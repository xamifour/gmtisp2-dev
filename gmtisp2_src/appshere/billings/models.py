# mpi_src/appshere/billings/models.py
import uuid
import re
import logging
from django.db import models
from datetime import timedelta
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

logger = logging.getLogger(__name__)

from utils.metrics import format_traffic_size, parse_uptime
from appshere.accounts.models import User, Organization, BaseMixin

MAX_LEN = 67

class Profile(BaseMixin):
    WHEN_START_CHOICES = [
        ('assigned', 'Assigned'),
        ('first-auth', 'First authentication'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mikrotik_id = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True, related_name='profile_org')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(_('name'), max_length=MAX_LEN, unique=True)
    name_for_users = models.CharField(_('name for users'), max_length=MAX_LEN, blank=True, null=True, help_text='Friendly name for user, e.g., Plan-100MB')
    price = models.CharField(_('price'), max_length=10, default='0.00')
    validity = models.CharField(_('validity'), max_length=MAX_LEN, default='30d', help_text="30m (30 minutes), 45d (45 days), 15d 00:45:00 (15 days, 0 hours, 45 minutes, and 0 seconds, 0 (no expiration)")
    starts_when = models.CharField(_('starts when'), max_length=MAX_LEN, choices=WHEN_START_CHOICES, default='first-auth')
    override_shared_users = models.CharField(_('override shared users'), max_length=MAX_LEN, default='off')
    
    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.name_for_users} - {self.price} - {self.validity}"
    
    def is_bonus(self):
        # Profile is considered a bonus if either:
        # 1. price is '0' and starts_when is 'assigned', OR
        # 2. price is '0' (ignoring starts_when)
        return self.price == '0' and (self.starts_when == 'assigned' or True)


# class Bonus(models.Model):
#     BONUS_TYPES = [
#         ('time', 'Time-based Bonus'),
#         ('data', 'Data-based Bonus'),
#         ('value', 'Value-based Bonus'),
#     ]
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     mikrotik_id = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True)
#     organization = models.ForeignKey('Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='bonus_org')
#     user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='bonuses')
#     profile = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='profile_bonuses')
#     bonus_type = models.CharField(max_length=MAX_LEN, choices=BONUS_TYPES)
#     value = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Bonus value
#     applied = models.BooleanField(default=False)  # Track if the bonus has been applied
#     start_time = models.DateTimeField(null=True, blank=True)
#     end_time = models.DateTimeField(null=True, blank=True)
#     valid_until = models.DateTimeField(null=True, blank=True)  # Bonus expiry date
#     reason = models.TextField(blank=True, null=True)  # Reason for the bonus (e.g., promotion)

#     class Meta:
#         ordering = ['-start_time']

#     def __str__(self):
#         return f"Bonus {self.id} for {self.user.username} ({self.bonus_type})"
    
#     def apply_bonus(self):
#         """
#         Apply the bonus if it's not expired and if it hasn't been applied yet.
#         Handles different types of bonuses (time, data, value) and ensures the correct updates.
#         """
#         try:
#             if self.applied:
#                 return False  # Bonus has already been applied

#             # Check if the bonus has expired
#             if self.valid_until and timezone.now() > self.valid_until:
#                 logger.warning(f"Bonus {self.id} has expired and will not be applied.")
#                 return False  # Bonus expired

#             # Apply the bonus to the UserProfile
#             user_profile = UserProfile.objects.filter(user=self.user, profile=self.profile).first()

#             if not user_profile:
#                 raise ValueError("UserProfile not found for this user and profile")

#             # Handle different bonus types
#             if self.bonus_type == 'time':
#                 self._apply_time_bonus(user_profile)
#             elif self.bonus_type == 'data':
#                 self._apply_data_bonus(user_profile)
#             elif self.bonus_type == 'value':
#                 self._apply_value_bonus(user_profile)
#             else:
#                 raise ValueError(f"Unsupported bonus type: {self.bonus_type}")

#             # Mark the bonus as applied
#             self.applied = True
#             self.save()

#             return True
#         except ValueError as e:
#             logger.error(f"Error applying bonus {self.id}: {str(e)}")
#             return False
#         except Exception as e:
#             logger.error(f"Unexpected error applying bonus {self.id}: {str(e)}")
#             return False

#     def _apply_time_bonus(self, user_profile):
#         """
#         Handle the application of time-based bonuses.
#         This could include extending or overriding the end_time for the bonus.
#         """
#         if user_profile.end_time:
#             # If there's already an end_time, decide whether to stack or override
#             current_end_time = datetime.strptime(user_profile.end_time, '%Y-%m-%d %H:%M:%S')
#             if self.value > 0:
#                 # Stack: extend the end_time
#                 extended_end_time = current_end_time + timedelta(days=int(self.value))
#                 user_profile.end_time = extended_end_time.strftime('%Y-%m-%d %H:%M:%S')
#             else:
#                 # Override: set a new end_time
#                 user_profile.end_time = (timezone.now() + timedelta(days=int(self.value))).strftime('%Y-%m-%d %H:%M:%S')
#         else:
#             # If no end_time is set, apply the bonus normally
#             user_profile.end_time = (timezone.now() + timedelta(days=int(self.value))).strftime('%Y-%m-%d %H:%M:%S')

#         # Ensure the user's profile state is active after applying a time-based bonus
#         user_profile.state = 'active'
#         user_profile.save()

#     def _apply_data_bonus(self, user_profile):
#         """
#         Handle the application of data-based bonuses.
#         This could include stacking the data usage limit.
#         """
#         limitation = ProfileLimitation.objects.filter(profile=self.profile).first()
#         if limitation:
#             # Assuming the limitation has a 'download_limit' field (in MB/GB, etc.)
#             limitation.download_limit += self.value  # Stack the data limit
#             limitation.save()
#         else:
#             logger.warning(f"ProfileLimitation not found for profile {self.profile.id}.")

#     def _apply_value_bonus(self, user_profile):
#         """
#         Handle the application of value-based bonuses.
#         This could include changing the user's state or applying any specific logic.
#         """
#         # For a value-based bonus, you might want to simply mark the profile as active, or adjust the state
#         user_profile.state = 'active'  # Mark the profile as active after receiving a value-based bonus
#         user_profile.save()


class UserProfile(BaseMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mikrotik_id = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True, related_name='userprofile_org')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    state = models.CharField(_('state'), max_length=MAX_LEN, blank=True, null=True)
    end_time = models.CharField(_('end time'), max_length=MAX_LEN, null=True, blank=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.user.username} - {self.profile.name} - {self.state}"

    def get_state(self):
        if self.state == 'used':
            return 'Time Elapsed'
        elif self.state == 'running':
            return 'Data Exhausted'
        elif self.state == 'waiting':
            return 'Waiting'
        return 'Active'


class Limitation(BaseMixin):
    RESET_COUNTERS_INTERVAL = [
        ('disabled', 'Disabled'),
        ('monthly', 'Monthly'),
        ('weekly', 'Weekly'),
        ('daily', 'Daily'),
        ('hourly', 'Hourly'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mikrotik_id = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True, related_name='limit_org')
    name = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True, help_text="limit-1gb")
    download_limit = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    upload_limit = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    transfer_limit = models.CharField(max_length=MAX_LEN, default='0', help_text="100M (100 MB), 10G (10 GB)")
    uptime_limit = models.CharField(max_length=MAX_LEN, default='30d',  help_text="30m (30 minutes), 45d (45 days), 0 (no expiration)")
    rate_limit_rx = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    rate_limit_tx = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    rate_limit_min_rx = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    rate_limit_min_tx = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    rate_limit_priority = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    rate_limit_burst_rx = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    rate_limit_burst_tx = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    rate_limit_burst_threshold_rx = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    rate_limit_burst_threshold_tx = models.CharField(max_length=MAX_LEN, default='0', help_text="")
    rate_limit_burst_time_rx = models.CharField(max_length=MAX_LEN, default='00:00:00', help_text="")
    rate_limit_burst_time_tx = models.CharField(max_length=MAX_LEN, default='00:00:00', help_text="")
    reset_counters_start_time = models.CharField(max_length=MAX_LEN, blank=True, null=True, help_text="")
    reset_counters_interval = models.CharField(max_length=MAX_LEN, choices=RESET_COUNTERS_INTERVAL, default='disabled', help_text="")

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.name


class ProfileLimitation(BaseMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mikrotik_id = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True, related_name='prof_limit_org')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, blank=True, null=True)
    limitation = models.ForeignKey(Limitation, on_delete=models.CASCADE, blank=True, null=True)
    from_time = models.CharField(max_length=10, default='00:00:00')
    till_time = models.CharField(max_length=10, default='23:59:59')
    weekdays = models.CharField(max_length=MAX_LEN, blank=True, null=True)  # Comma-separated weekdays

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.profile.name} - {self.limitation.name}"
    

class Payment(BaseMixin):
    COPY_FROM_CHOICES = [
        ('manual', 'Manual'),
        ('auto', 'Auto'),
    ]

    TRANS_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    METHOD_CHOICES = [
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mikrotik_id = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True, related_name='payment_org')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, blank=True, null=True)
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    copy_from = models.CharField(max_length=MAX_LEN, choices=COPY_FROM_CHOICES, default='manual')
    method = models.CharField(max_length=MAX_LEN, choices=METHOD_CHOICES, default='OFFLINE')
    trans_start = models.CharField(max_length=MAX_LEN, null=True, blank=True)
    trans_end = models.CharField(_('Date'), max_length=MAX_LEN, null=True, blank=True)
    trans_status = models.CharField(max_length=MAX_LEN, choices=TRANS_STATUS_CHOICES)
    user_message = models.TextField(null=True, blank=True)
    currency = models.CharField(max_length=MAX_LEN, default="GHS")
    price = models.CharField(max_length=10)
    paystack_reference = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        ordering = ['-trans_end']

    def __str__(self):
        return _('Payment #: %(id)d') % {'id': self.id}

    def get_reference(self):
        return _('%(ref)s') % {'ref': self.paystack_reference}


class Session(models.Model):
    mikrotik_id = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True)
    session_id = models.CharField(_('Session ID'), max_length=MAX_LEN, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True, related_name='session_org')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nas_ip_address = models.CharField(_('NAS IP Address'), max_length=45, blank=True, null=True)
    nas_port_id = models.CharField(_('NAS Port ID'), max_length=MAX_LEN)
    nas_port_type = models.CharField(_('NAS Port Type'), max_length=MAX_LEN)
    calling_station_id = models.CharField(_('Calling Station ID'), max_length=MAX_LEN)
    user_address = models.CharField(_('User Address'), max_length=45)
    download = models.CharField(_('Download'), max_length=MAX_LEN)
    upload = models.CharField(_('Upload'), max_length=MAX_LEN)
    uptime = models.CharField(_('Uptime'), max_length=MAX_LEN)
    status = models.CharField(_('Status'), max_length=MAX_LEN)
    started = models.CharField(_('Started'), max_length=MAX_LEN, null=True, blank=True)
    ended = models.CharField(_('Ended'), max_length=MAX_LEN, null=True, blank=True)
    last_accounting_packet = models.CharField(_('Last Accounting Packet'), max_length=MAX_LEN, null=True, blank=True)
    terminate_cause = models.CharField(_('Terminate Cause'), max_length=MAX_LEN, blank=True, null=True)

    class Meta:
        ordering = ['-started']

    def __str__(self):
        return f"Session {self.session_id} for {self.user.username}"

    def get_session_status(self):
        closed_statuses = {'stop', 'close-acked', 'expired'}
        statuses = set(self.status.split(','))
        return 'Closed' if closed_statuses & statuses else 'Running'
        
    def get_terminate_cause(self):
        if self.terminate_cause == 'admin-reset':
            return 'Data finished'
        elif self.terminate_cause == 'um-limits-reached':
            return 'Time Expired'
        else:
            return None
        
    def session_traffic(self):
        try:
            download_size = int(self.download)
            upload_size = int(self.upload)
            return download_size + upload_size
        except (ValueError, TypeError):
            return 0

    def formatted_download(self):
        try:
            bytes_size = int(self.download)
            return format_traffic_size(bytes_size)
        except (ValueError, TypeError):
            return "Invalid download size"

    def formatted_upload(self):
        try:
            bytes_size = int(self.upload)
            return format_traffic_size(bytes_size)
        except (ValueError, TypeError):
            return "Invalid upload size"

    def formatted_total_traffic(self):
        return format_traffic_size(self.session_traffic())


def get_user_all_time_uptime(user):
    total_uptime_seconds = 0
    
    # Fetch all sessions for the user
    sessions = Session.objects.filter(user=user)

    for session in sessions:
        if session.uptime:
            match = re.match(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', session.uptime)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                total_uptime_seconds += hours * 3600 + minutes * 60 + seconds

    return timedelta(seconds=total_uptime_seconds)

# def get_user_all_time_traffic(user):
#     """Calculate total download and upload for a user."""
#     total_traffic = Session.objects.filter(user=user).aggregate(
#         total_download=Sum('download'),
#         total_upload=Sum('upload')
#     )
#     return {
#         'total_download': total_traffic['total_download'] or 0,
#         'total_upload': total_traffic['total_upload'] or 0,
#         'total_traffic': (total_traffic['total_download'] or 0) + (total_traffic['total_upload'] or 0),
#     }
def get_user_all_time_traffic(user):
    """Calculate total download and upload for a user."""
    sessions = Session.objects.filter(user=user)
    
    total_download = 0
    total_upload = 0
    
    for session in sessions:
        try:
            # Convert 'download' and 'upload' to integers (handle invalid data gracefully)
            total_download += int(session.download or 0)
            total_upload += int(session.upload or 0)
        except ValueError:
            # In case of conversion error (invalid data), skip that session or log it
            pass

    return {
        'total_download': total_download,
        'total_upload': total_upload,
        'total_traffic': total_download + total_upload,
    }

def get_user_traffic_and_time_for_a_period(user_profile_id):
    """Get user traffic and time within a specific validity period."""
    try:
        user_profile = UserProfile.objects.get(id=user_profile_id)
        
        profile = user_profile.profile
        validity_duration = parse_validity(profile.validity)
        start_time = user_profile.created
        end_time = start_time + validity_duration

        if user_profile.end_time:
            end_time_from_string = timezone.datetime.fromisoformat(user_profile.end_time)
            if end_time_from_string.tzinfo is None:
                end_time_from_string = timezone.make_aware(end_time_from_string)
            end_time = min(end_time, end_time_from_string)

        sessions = Session.objects.filter(
            user=user_profile.user,
            started__gte=start_time,
            started__lt=end_time
        )

        total_download = sum(int(session.download) for session in sessions if session.download.isdigit())
        total_upload = sum(int(session.upload) for session in sessions if session.upload.isdigit())
        total_traffic = total_download + total_upload
        total_time = sum(parse_uptime(session.uptime) for session in sessions)

        return {
            'total_download': total_download,
            'total_upload': total_upload,
            'total_traffic': total_traffic,
            'total_time': total_time,
            'sessions_count': sessions.count()
        }

    except ObjectDoesNotExist:
        return {'error': 'UserProfile not found.'}
    except ValueError:
        return {'error': 'Invalid data encountered in session download/upload.'}


def parse_validity(validity_str):
    """Parse validity string (like '30d 00:00:00') into a timedelta object."""
    days, hours, minutes, seconds = 0, 0, 0, 0
    matches = re.findall(r'(\d+)([d|h|m|s])', validity_str)

    for match in matches:
        value, unit = match
        value = int(value)
        if unit == 'd':
            days += value
        elif unit == 'h':
            hours += value
        elif unit == 'm':
            minutes += value
        elif unit == 's':
            seconds += value

    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
