# mpi_src/appshere/billings/tasks.py
import logging
from django.db import transaction, IntegrityError
from celery import shared_task
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import timedelta

from utils.mikrotik_userman import init_mikrotik_manager
from appshere.accounts.models import User, UserUsage
from .models import Profile, UserProfile, Session, Limitation, ProfileLimitation

logger = logging.getLogger(__name__)

# Initialize the MikroTik manager
mikrotik_manager = init_mikrotik_manager()


# ------------------------------- from MikroTik to Django
@shared_task
def sync_data_from_mikrotik():
    """Synchronizes MikroTik data (users, profiles, user profiles, and sessions) with Django."""
    logger.debug("Starting sync_mikrotik_data task")

    try:
        sync_users(mikrotik_manager)
        sync_monitor_user_usage(mikrotik_manager)
        sync_profiles(mikrotik_manager)
        sync_user_profiles(mikrotik_manager)
        sync_sessions(mikrotik_manager)
    except Exception as e:
        logger.error(f"Error syncing data: {e}", exc_info=True)
    else:
        logger.info("MikroTik sync completed successfully")


def sync_users(mikrotik_manager):
    """Synchronizes users from MikroTik to the Django database."""
    try:
        with transaction.atomic():
            mikrotik_users = mikrotik_manager.get_users()
            for mt_user in mikrotik_users:
                # Use `mikrotik_id` as the lookup field to avoid duplicate entries
                user, created = User.objects.update_or_create(
                    mikrotik_id=mt_user['.id'],  # Lookup by mikrotik_id
                    defaults={
                        'name': mt_user['name'],  # Use 'name' here instead of 'username'
                        'group': mt_user.get('group', ''),
                        'disabled': mt_user.get('disabled') == 'true',
                        'otp_secret': mt_user.get('otp-secret', ''),
                        'shared_users': int(mt_user.get('shared-users', 1)),
                        'plain_password': mt_user.get('password', ''),
                    }
                )
                if created:
                    logger.info(f'Created new user with MikroTik ID: {user.mikrotik_id}')
                else:
                    logger.info(f'Updated user with MikroTik ID: {user.mikrotik_id}')
    except Exception as e:
        logger.error(f"Error syncing users: {e}", exc_info=True)
        raise


def parse_uptime(uptime_str: str) -> int:
    """
    Parse uptime string (format: '3h50m45s') and return total seconds.
    If the format is not as expected, handle it gracefully.
    """
    total_seconds = 0
    import re
    match = re.match(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', uptime_str)

    if match:
        hours, minutes, seconds = match.groups(default='0')
        total_seconds += int(hours) * 3600
        total_seconds += int(minutes) * 60
        total_seconds += int(seconds)

    return total_seconds

def sync_monitor_user_usage(mikrotik_manager):
    """Synchronizes user usage from MikroTik to the Django database."""
    logger.debug("Starting sync_monitor_user_usage task")

    try:
        # Retrieve all users from Django to map MikroTik IDs to User objects
        django_users = {user.mikrotik_id: user for user in User.objects.all()}

        for mikrotik_id, user in django_users.items():
            # Fetch the user usage from MikroTik
            usage_data = mikrotik_manager.monitor_user_usage(mikrotik_id)

            if usage_data:
                # Since usage_data is a list, we take the first (and only) item
                usage_info = usage_data[0]

                # Create or update the UserUsage instance
                UserUsage.objects.update_or_create(
                    mikrotik_id=mikrotik_id,
                    defaults={
                        'user': user,
                        'active_sessions': int(usage_info.get('active-sessions', 0)),
                        'active_sub_sessions': int(usage_info.get('active-sub-sessions', 0)),
                        'total_download': int(usage_info.get('total-download', 0)),
                        'total_upload': int(usage_info.get('total-upload', 0)),
                        'total_uptime': usage_info.get('total-uptime', '0s'),  # default to '0s' if not provided
                        'attributes_details': usage_info.get('attributes-details', '')
                    }
                )
                logger.info(f"Updated usage for user: {user.username}")
            else:
                logger.warning(f"No usage data returned for user ID: {mikrotik_id}")

    except Exception as e:
        logger.error(f"Error syncing user usage: {e}", exc_info=True)
        raise


def sync_profiles(mikrotik_manager):
    """Synchronizes profiles from MikroTik to the Django database."""
    try:
        with transaction.atomic():
            mikrotik_profiles = mikrotik_manager.get_profiles()
            for mt_profile in mikrotik_profiles:
                profile, created = Profile.objects.update_or_create(
                    name=mt_profile['name'],
                    defaults={
                        'name_for_users': mt_profile.get('name-for-users', ''),
                        'price': mt_profile.get('price', '0.00'),
                        'starts_when': mt_profile.get('starts-when', 'assigned'),
                        'validity': mt_profile.get('validity', '30d 00:00:00'),
                        'override_shared_users': mt_profile.get('override-shared-users', 'off'),
                        'mikrotik_id': mt_profile['.id'],  # Store MikroTik ID
                    }
                )
                if created:
                    logger.info(f'Created new profile: {profile.name}')
                else:
                    logger.info(f'Updated profile: {profile.name}')
    except Exception as e:
        logger.error(f"Error syncing profiles: {e}", exc_info=True)
        raise


def sync_user_profiles(mikrotik_manager):
    """Synchronizes user profiles from MikroTik to the Django database."""
    try:
        with transaction.atomic():
            mikrotik_user_profiles = mikrotik_manager.get_user_profiles()
            for mt_user_profile in mikrotik_user_profiles:
                user = User.objects.filter(username=mt_user_profile['user']).first()
                profile = Profile.objects.filter(name=mt_user_profile['profile']).first()

                if not user or not profile:
                    logger.warning(f"User '{mt_user_profile['user']}' or Profile '{mt_user_profile['profile']}' not found.")
                    continue

                end_time = mt_user_profile.get('end-time', None)
                state = mt_user_profile.get('state')
                mikrotik_id = mt_user_profile['.id']

                # Attempt to get the existing UserProfile by MikroTik ID
                user_profile, created = UserProfile.objects.get_or_create(
                    mikrotik_id=mikrotik_id,
                    defaults={
                        'user': user,
                        'profile': profile,
                        'state': state,
                        'end_time': end_time
                    }
                )

                # If the record already exists, check if we need to update it
                if not created:
                    # Only update state and end_time if they have changed
                    update_needed = False
                    if user_profile.state != state:
                        user_profile.state = state
                        update_needed = True
                    if user_profile.end_time != end_time:
                        user_profile.end_time = end_time
                        update_needed = True

                    if update_needed:
                        user_profile.save()

    except Exception as e:
        logger.error(f"Error syncing user profiles: {e}", exc_info=True)
        raise


def sync_sessions(mikrotik_manager):
    """Synchronizes sessions from MikroTik to the Django database."""
    try:
        with transaction.atomic():
            mikrotik_sessions = mikrotik_manager.get_sessions()
            for mt_session in mikrotik_sessions:
                user = User.objects.filter(username=mt_session.get('user')).first()
                if not user:
                    logger.warning(f"User '{mt_session.get('user')}' not found. '{mt_session.get('acct-session-id')}'")
                    continue

                # Convert naive datetime to aware datetime if time zone support is active
                from django.utils import timezone
                ended_str = mt_session.get('ended')
                ended = None
                if ended_str:
                    ended = datetime.strptime(ended_str, '%Y-%m-%d %H:%M:%S')
                    if timezone.is_naive(ended):
                        ended = timezone.make_aware(ended)

                session_defaults = {
                    'user': user,  # Ensure user is assigned here
                    'nas_ip_address': mt_session.get('nas-ip-address'),
                    'nas_port_id': mt_session.get('nas-port-id'),
                    'nas_port_type': mt_session.get('nas-port-type'),
                    'calling_station_id': mt_session.get('calling-station-id'),
                    'download': int(mt_session.get('download', 0)),
                    'upload': int(mt_session.get('upload', 0)),
                    'uptime': mt_session.get('uptime'),
                    'status': mt_session.get('status'),
                    'started': mt_session.get('started'),
                    'ended': mt_session.get('ended', None),
                    'terminate_cause': mt_session.get('terminate-cause', None),
                    'user_address': mt_session.get('user-address'),
                    'last_accounting_packet': mt_session.get('last-accounting-packet'),
                    'mikrotik_id': mt_session.get('.id')  # Store MikroTik ID here
                }

                session, created = Session.objects.update_or_create(
                    session_id=mt_session.get('acct-session-id'),
                    defaults=session_defaults
                )

                if created:
                    logger.info(f'Created new session: {session.session_id}')
                else:
                    logger.info(f'Updated session: {session.session_id}')

                # Notify WebSocket clients of new session data
                send_traffic_update_to_group(session.session_id, {
                    "download": session.download,
                    "upload": session.upload,
                    "uptime": session.uptime,
                })
    except Exception as e:
        logger.error(f"Error syncing sessions: {e}", exc_info=True)
        raise


# WebSocket notification
def send_traffic_update_to_group(session_id, traffic_data):
    """Sends session traffic updates to WebSocket clients."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'session_{session_id}',  # Group name
        {
            'type': 'send_traffic_update',  # Method to call in the consumer
            'traffic_data': traffic_data  # Traffic data to send
        }
    )


# ------------------------------- from Django to MikroTik
# event-based tasks triggered by CRUD operations

from utils.data_preparation import (
    prepare_user_data, 
    prepare_profile_data, 
    prepare_user_profile_data, 
    prepare_limitation_data, 
    prepare_profile_limitation_data
)

# @shared_task
# def create_or_update_user_event(user_id):
#     try:
#         user = User.objects.get(id=user_id)
#         user_data = prepare_user_data(user)
#         if user.mikrotik_id:
#             if mikrotik_manager.get_user(user.mikrotik_id):
#                 mikrotik_manager.update_user(user_id=user.mikrotik_id, user_data=user_data)
#             else:
#                 response = mikrotik_manager.create_user(user_data)
#                 user.mikrotik_id = response.get('.id')
#                 user.save()
#     except User.DoesNotExist:
#         logger.error(f'User with ID {user_id} not found')
@shared_task
def create_or_update_user_event(user_id):
    try:
        user = User.objects.get(id=user_id)
        if user.mikrotik_id:
            # Update existing user in MikroTik
            user_data = prepare_user_data(user, is_update=True)
            mikrotik_manager.update_user(user_id=user.mikrotik_id, user_data=user_data)
        else:
            # Create new user in MikroTik
            user_data = prepare_user_data(user, is_update=False)
            response = mikrotik_manager.create_user(user_data)
            
            # Save the generated MikroTik ID to the user in Django
            if response and '.id' in response:
                user.mikrotik_id = response['.id']
                user.save()
                logger.info(f"User created in MikroTik with ID {user.mikrotik_id}")
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")

@shared_task
def create_or_update_profile_event(profile_id):
    try:
        profile = Profile.objects.get(id=profile_id)
        profile_data = prepare_profile_data(profile)
        if profile.mikrotik_id:
            mikrotik_manager.update_profile(profile_id=profile.mikrotik_id, profile_data=profile_data)
        else:
            response = mikrotik_manager.create_profile(profile_data)
            profile.mikrotik_id = response.get('.id')
            profile.save()
    except Profile.DoesNotExist:
        logger.error(f'Profile with ID {profile_id} not found')


@shared_task
def create_or_update_user_profile_event(user_profile_id):
    """Create or update a user profile in MikroTik."""
    try:
        user_profile = UserProfile.objects.get(id=user_profile_id)

        if user_profile.mikrotik_id:
            # Update existing user profile in MikroTik
            # user_profile_data = prepare_user_profile_data(user_profile)
            # mikrotik_manager.update_user_profile(user_profile_id=user_profile.mikrotik_id, **user_profile_data)
            # logger.info(f"Updated user profile for user {user_profile.user.username} in MikroTik.")
            pass
        else:
            # Create new user profile in MikroTik
            user_profile_data = prepare_user_profile_data(user_profile)
            response = mikrotik_manager.create_user_profile(user_profile_data)

            # Save the generated MikroTik ID to the user profile in Django
            if response and '.id' in response:
                user_profile.mikrotik_id = response['.id']
                user_profile.save()
                logger.info(f"Created user profile for user {user_profile.user.username} in MikroTik with ID {user_profile.mikrotik_id}")
            else:
                logger.error(f"User profile creation failed for {user_profile.user.username}. No valid response received from MikroTik.")

    except UserProfile.DoesNotExist:
        logger.error(f"UserProfile with ID {user_profile_id} does not exist")
    except Exception as e:
        logger.error(f"Error processing UserProfile {user_profile_id} in MikroTik: {e}", exc_info=True)
        raise


@shared_task
def create_or_update_limitation_event(limitation_id):
    try:
        limitation = Limitation.objects.get(id=limitation_id)
        limitation_data = prepare_limitation_data(limitation)
        if limitation.mikrotik_id:
            mikrotik_manager.update_limitation(limitation_id=limitation.mikrotik_id, limitation_data=limitation_data)
        else:
            response = mikrotik_manager.create_limitation(limitation_data)
            limitation.mikrotik_id = response.get('.id')
            limitation.save()
    except Limitation.DoesNotExist:
        logger.error(f'Limitation with ID {limitation_id} not found')


@shared_task
def create_or_update_profile_limitation_event(profile_limitation_id):
    """Create or update a profile limitation in MikroTik."""
    try:
        profile_limitation = ProfileLimitation.objects.get(id=profile_limitation_id)
        if profile_limitation.mikrotik_id:
            # # Update existing profile limitation in MikroTik
            # profile_limitation_data = prepare_profile_limitation_data(profile_limitation)
            # mikrotik_manager.update_profile_limitation(
            #     limitation_id=profile_limitation.mikrotik_id, 
            #     limitation_data=profile_limitation_data
            # )
            # logger.info(f"Updated profile limitation for profile {profile_limitation.profile} in MikroTik.")
            pass
        else:
            # Create new profile limitation in MikroTik
            profile_limitation_data = prepare_profile_limitation_data(profile_limitation)
            response = mikrotik_manager.create_profile_limitation(profile_limitation_data)

            # Save the generated MikroTik ID to the profile limitation in Django
            if response and '.id' in response:
                profile_limitation.mikrotik_id = response['.id']
                profile_limitation.save()
                logger.info(f"Created profile limitation for profile {profile_limitation.profile} in MikroTik with ID {profile_limitation.mikrotik_id}")
            else:
                logger.error(f"Profile limitation creation failed for profile {profile_limitation.profile}. No valid response received from MikroTik.")

    except ProfileLimitation.DoesNotExist:
        logger.error(f'ProfileLimitation with ID {profile_limitation_id} does not exist')
    except Exception as e:
        logger.error(f"Error processing ProfileLimitation {profile_limitation_id} in MikroTik: {e}", exc_info=True)
        raise

def trigger_mikrotik_tasks(instance, created, **kwargs):
    """Trigger MikroTik tasks based on model instance changes."""
    from .tasks import (
        create_or_update_user_event,
        create_or_update_profile_event,
        create_or_update_user_profile_event,
        create_or_update_limitation_event,
        create_or_update_profile_limitation_event
    )

    task_map = {
        User: create_or_update_user_event,
        Profile: create_or_update_profile_event,
        UserProfile: create_or_update_user_profile_event,
        Limitation: create_or_update_limitation_event,
        ProfileLimitation: create_or_update_profile_limitation_event,
    }

    task = task_map.get(type(instance))  # Get the task for the instance's type
    if task:
        # task.delay(instance.id)  # Trigger the task asynchronously
        task(instance.id) # without using asynchronous tasks like Celery
    else:
        logger.error(f"No task mapped for model {type(instance)}")


# # Deletion tasks
# @shared_task
# def delete_user_from_mikrotik(user_id):
#     try:
#         user = User.objects.get(id=user_id)
#         if user.mikrotik_id:
#             existing_user = next((u for u in mikrotik_manager.get_users() if u['name'] == user.username), None)
#             if existing_user:
#                 mikrotik_manager.delete_user(user_id=existing_user['.id'])
#                 logger.info(f'Deleted user {user.username} from MikroTik.')
#             else:
#                 logger.warning(f'User {user.username} does not exist in MikroTik.')
#     except User.DoesNotExist:
#         logger.error(f"User with ID {user_id} not found.")
#     except Exception as e:
#         logger.error(f"Error deleting user {user_id} from MikroTik: {e}", exc_info=True)


# @shared_task
# def delete_profile_from_mikrotik(profile_id):
#     try:
#         profile = Profile.objects.get(id=profile_id)
#         if profile.mikrotik_id:
#             existing_profile = next((p for p in mikrotik_manager.get_profiles() if p['name'] == profile.name), None)
#             if existing_profile:
#                 mikrotik_manager.delete_profile(profile_id=existing_profile['.id'])
#                 logger.info(f'Deleted profile {profile.name} from MikroTik.')
#             else:
#                 logger.warning(f'Profile {profile.name} does not exist in MikroTik.')
#     except Profile.DoesNotExist:
#         logger.error(f"Profile with ID {profile_id} not found.")
#     except Exception as e:
#         logger.error(f"Error deleting profile {profile_id} from MikroTik: {e}", exc_info=True)


# @shared_task
# def delete_user_profile_from_mikrotik(user_profile_id):
#     try:
#         user_profile = UserProfile.objects.get(id=user_profile_id)
#         if user_profile.mikrotik_id:
#             existing_user_profile = next((up for up in mikrotik_manager.get_user_profiles() if up['user'] == user_profile.user.username), None)
#             if existing_user_profile:
#                 mikrotik_manager.delete_user_profile(user_profile_id=existing_user_profile['.id'])
#                 logger.info(f'Deleted user profile for {user_profile.user.username} from MikroTik.')
#             else:
#                 logger.warning(f'User profile for {user_profile.user.username} does not exist in MikroTik.')
#     except UserProfile.DoesNotExist:
#         logger.error(f"UserProfile with ID {user_profile_id} not found.")
#     except Exception as e:
#         logger.error(f"Error deleting user profile for {user_profile_id} from MikroTik: {e}", exc_info=True)


# @shared_task
# def delete_limitation_from_mikrotik(limitation_id):
#     try:
#         limitation = Limitation.objects.get(id=limitation_id)
#         if limitation.mikrotik_id:
#             existing_limitation = next((l for l in mikrotik_manager.get_limitations() if l['name'] == limitation.name), None)
#             if existing_limitation:
#                 mikrotik_manager.delete_limitation(limitation_id=existing_limitation['.id'])
#                 logger.info(f'Deleted limitation {limitation.name} from MikroTik.')
#             else:
#                 logger.warning(f'Limitation {limitation.name} does not exist in MikroTik.')
#     except Limitation.DoesNotExist:
#         logger.error(f"Limitation with ID {limitation_id} not found.")
#     except Exception as e:
#         logger.error(f"Error deleting limitation {limitation_id} from MikroTik: {e}", exc_info=True)


# @shared_task
# def delete_profile_limitation_from_mikrotik(profile_limitation_id):
#     try:
#         profile_limitation = ProfileLimitation.objects.get(id=profile_limitation_id)
#         if profile_limitation.mikrotik_id:
#             existing_profile_limitation = next((pl for pl in mikrotik_manager.get_profile_limitations() if pl['profile'] == profile_limitation.profile.name), None)
#             if existing_profile_limitation:
#                 mikrotik_manager.delete_profile_limitation(limitation_id=existing_profile_limitation['.id'])
#                 logger.info(f'Deleted profile limitation for {profile_limitation.profile.name} from MikroTik.')
#             else:
#                 logger.warning(f'Profile limitation for {profile_limitation.profile.name} does not exist in MikroTik.')
#     except ProfileLimitation.DoesNotExist:
#         logger.error(f"ProfileLimitation with ID {profile_limitation_id} not found.")
#     except Exception as e:
#         logger.error(f"Error deleting profile limitation for {profile_limitation_id} from MikroTik: {e}", exc_info=True)


# def trigger_delete_mikrotik_tasks(instance, **kwargs):
#     """Trigger MikroTik delete tasks based on model instance type."""
#     task_map = {
#         User: delete_user_from_mikrotik,
#         Profile: delete_profile_from_mikrotik,
#         UserProfile: delete_user_profile_from_mikrotik,
#         Limitation: delete_limitation_from_mikrotik,
#         ProfileLimitation: delete_profile_limitation_from_mikrotik,
#     }

#     task = task_map.get(type(instance))  # Get the task for the instance's type
#     if task:
#         task.delay(instance.id)  # Trigger the task asynchronously
#     else:
#         logger.error(f"No delete task mapped for model {type(instance)}")
