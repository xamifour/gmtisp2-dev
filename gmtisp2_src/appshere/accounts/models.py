# mpi_src/appshere/accounts/models.py
import uuid
import re
from datetime import timedelta, datetime
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from utils.metrics import format_traffic_size

import logging
logger = logging.getLogger(__name__)


MAX_LEN = 67
#    
class BaseMixin(models.Model):  
    created  = models.DateTimeField(_('created'), auto_now_add=True, db_index=True)
    modified = models.DateTimeField(_('modified'), auto_now=True)
    
    class Meta:
        abstract = True


class Organization(BaseMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=MAX_LEN, unique=True)
    slug = models.CharField(_('slug'), max_length=MAX_LEN, unique=True)
    description = models.TextField(_('description'), blank=True)
    email = models.EmailField(_('email'), unique=True, blank=True)
    address = models.CharField(_('address'), max_length=512, blank=True, null=True)
    phone = models.CharField(_('phone number'), max_length=10, unique=True, blank=True, null=True)
    url = models.URLField(_('URL'), blank=True, null=True)
    logo = models.ImageField(_('logo'), max_length=MAX_LEN, blank=True, null=True, help_text=_('Logo URL'))
    theme = models.CharField(_('theme'), max_length=7, blank=True, null=True, help_text=_('Primary theme color in hex format (e.g. #ffffff)'))
    session_quota = models.PositiveIntegerField(_('session quota'), default=0)
    notes = models.TextField(_('notes'), blank=True, null=True, help_text=_('Notes'))

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f'{self.slug} - {self.id}'


class Dashboard(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='dash_org')
    description = models.TextField(_('description'), blank=True)
      

class Nas(BaseMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey('Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='nas_org')
    name = models.CharField(verbose_name=_('name'), max_length=MAX_LEN, help_text=_('NAS Name (or IP address)'), db_index=True, db_column='nasname')
    short_name = models.CharField( verbose_name=_('short name'), max_length=MAX_LEN, db_column='shortname')
    type = models.CharField(verbose_name=_('type'), max_length=MAX_LEN)
    ports = models.PositiveIntegerField(verbose_name=_('ports'), blank=True, null=True)
    secret = models.CharField(verbose_name=_('secret'), max_length=MAX_LEN, help_text=_('Shared Secret'))
    server = models.CharField(verbose_name=_('server'), max_length=MAX_LEN, blank=True, null=True)
    community = models.CharField( verbose_name=_('community'), max_length=MAX_LEN, blank=True, null=True)
    description = models.CharField(verbose_name=_('description'), max_length=MAX_LEN, null=True, blank=True)
    gps_location = models.CharField( verbose_name=_('GPS Location'), max_length=MAX_LEN, blank=True, null=True)
    notes = models.TextField(verbose_name=_('notes'), blank=True, null=True, help_text=_('Notes'))

    class Meta:
        ordering = ['-created']
        db_table = 'nas'
        verbose_name = _('NAS')
        verbose_name_plural = _('NAS')

    def __str__(self):
        return self.name
    

class User(AbstractUser, BaseMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mikrotik_id = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_org')
    name = models.CharField(_('name'), max_length=MAX_LEN, unique=True, blank=True, null=True)
    group = models.CharField(_('group'), max_length=MAX_LEN, default='default')
    disabled = models.BooleanField(_('disabled'), default=False)
    otp_secret = models.CharField(_('otp-secret'), max_length=256, blank=True, null=True)
    shared_users = models.CharField(_('shared-users'), max_length=10, default='1')
    attributes = models.CharField(_('attributes'), max_length=MAX_LEN, blank=True, null=True)
    plain_password = models.CharField(_('plain password'), max_length=256, blank=True, null=True)  # must be auto generated
    country = models.CharField(_('country'), max_length=MAX_LEN, blank=True, null=True)
    city = models.CharField(_('city'), max_length=MAX_LEN, blank=True, null=True)
    postal_code = models.CharField(_('postal_code'), max_length=MAX_LEN, blank=True, null=True, help_text='+233')
    phone = models.CharField(_('phone'), max_length=10, blank=True, null=True, help_text='0201234567')
    address = models.CharField(_('address'), max_length=512, blank=True, null=True)
    notes = models.CharField(_('notes'), max_length=1024, blank=True, null=True)
    theme = models.CharField(_('theme'), max_length=7, blank=True, null=True, help_text=_('User theme/color in hex format (e.g. #ffffff)'))

    class Meta:
        ordering = ['-created']

    def save(self, *args, **kwargs):
        if self.password and not self.plain_password:
            self.plain_password = self.password
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class UserUsage(BaseMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mikrotik_id = models.CharField(max_length=MAX_LEN, unique=True, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True, related_name='userusage_org')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    active_sessions = models.CharField(max_length=10, default='0')
    active_sub_sessions = models.CharField(max_length=10, default='0')
    total_download = models.CharField(max_length=MAX_LEN, default='0')
    total_upload = models.CharField(max_length=MAX_LEN, default='0')
    total_uptime = models.CharField(max_length=MAX_LEN, blank=True, null=True)
    attributes_details = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"User ID: {self.user_id} - Download: {self.total_download} bytes, Upload: {self.total_upload} bytes"

    @property
    def total_traffic(self):
        return str(int(self.total_download) + int(self.total_upload))  # Calculate total traffic dynamically
    
    def formatted_user_upload(self):
        try:
            # bytes_size = int(self.total_upload)
            return format_traffic_size(int(self.total_upload))
        except (ValueError, TypeError):
            return "Invalid upload size"
        
    def formatted_user_download(self):
        try:
            bytes_size = int(self.total_download)
            return format_traffic_size(bytes_size)
        except (ValueError, TypeError):
            return "Invalid upload size"
        
    def formatted_user_traffic(self):
        try:
            bytes_size = int(self.total_traffic)
            return format_traffic_size(bytes_size)
        except (ValueError, TypeError):
            return "Invalid traffic size"