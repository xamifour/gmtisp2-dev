# mpi_src/appshere/billings/admin.py
import logging
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from utils.mikrotik_userman import init_mikrotik_manager
from utils.data_preparation import prepare_profile_data, prepare_limitation_data
from appshere.accounts.admin import MultitenantAdminMixin
from .models import UserProfile, Profile, Payment, Session, Limitation, ProfileLimitation

# Initialize MikroTikUserManager
mikrotik_manager = init_mikrotik_manager()

logger = logging.getLogger(__name__)


class ProfileAdmin(MultitenantAdminMixin, admin.ModelAdmin):
    list_display = ('mikrotik_id', 'name', 'name_for_users', 'price', 'validity', 'created', 'organization__slug')
    actions = ['sync_profiles_to_mikrotik']
    readonly_fields = ['mikrotik_id', 'created', 'modified']
    
    fieldsets = (
        (None, {'fields': (
            'mikrotik_id', 'organization', 'name', 'name_for_users', 'price', 
            'validity', 'starts_when', 'override_shared_users'
        )}),
        (_('Dates'), {'fields': ('created', 'modified')}),
    )

    def sync_profiles_to_mikrotik(self, request, queryset):
        """Sync selected profiles with MikroTik."""
        for obj in queryset:
            try:
                profile_data = prepare_profile_data(obj)
                existing_profile = next(
                    (p for p in mikrotik_manager.get_profiles() if p['name'] == obj.name), None
                )
                if existing_profile:
                    mikrotik_manager.update_profile(
                        profile_id=existing_profile['.id'],  # Pass the existing profile ID
                        profile_data=profile_data  # Pass all profile data
                    )
                    self.message_user(request, f"Profile '{obj.name}' updated in MikroTik UserManager.")
                else:
                    mikrotik_manager.create_profile(
                        profile_data=profile_data  # Pass all profile data
                    )
                    self.message_user(request, f"Profile '{obj.name}' created in MikroTik UserManager.")
            except Exception as e:
                self.message_user(request, f"Error syncing profile '{obj.name}' with MikroTik UserManager: {e}", level='error')

    sync_profiles_to_mikrotik.short_description = "Sync selected profiles to MikroTik"


class UserProfileAdmin(MultitenantAdminMixin, admin.ModelAdmin):
    list_display = ('mikrotik_id', 'user', 'profile__name', 'state', 'end_time', 'created', 'organization__slug')
    readonly_fields = ['mikrotik_id', 'end_time', 'state', 'created', 'modified']


class PaymentAdmin(MultitenantAdminMixin, admin.ModelAdmin):
    list_display = ('user_profile', 'method', 'price', 'trans_end', 'trans_status', 'organization__slug')
    search_fields = ('user__username', 'method', 'price')
    list_filter = ('method', 'trans_status')
    readonly_fields = ['mikrotik_id', 'user_profile', 'user', 'profile', 'organization', 'price', 
                       'trans_status', 'method', 'trans_start', 'trans_end', 'copy_from', 
                       'user_message', 'currency', 'paystack_reference']


class SessionAdmin(MultitenantAdminMixin, admin.ModelAdmin):
    list_display = (
        'organization__slug', 'mikrotik_id', 'session_id', 'user', 'nas_ip_address', 
        'started', 'ended', 'terminate_cause'
    )
    search_fields = ('session_id', 'user__username', 'nas_ip_address')
    list_filter = ('nas_ip_address', 'nas_port_type', 'status', 'terminate_cause')
    readonly_fields = [
        'mikrotik_id', 'session_id', 'user', 'nas_ip_address', 
        'nas_port_id', 'nas_port_type', 'calling_station_id', 
        'download', 'upload', 'uptime', 'status', 'started', 
        'ended', 'terminate_cause', 'user_address', 'last_accounting_packet'
    ]


class LimitationAdmin(MultitenantAdminMixin, admin.ModelAdmin):
    list_display = ('mikrotik_id', 'name', 'transfer_limit', 'uptime_limit', 'organization__slug')
    search_fields = ('name',)
    list_filter = ('rate_limit_priority',)
    readonly_fields = ('mikrotik_id', 'created', 'modified')
    actions = ['sync_limitations_to_mikrotik']

    def sync_limitations_to_mikrotik(self, request, queryset):
        """Sync selected limitations with MikroTik."""
        for obj in queryset:
            try:
                limitation_data = prepare_limitation_data(obj)
                existing_limitation = next(
                    (l for l in mikrotik_manager.get_limitations() if l['name'] == obj.name), None
                )
                if existing_limitation:
                    mikrotik_manager.update_limitation(
                        limitation_id=existing_limitation['.id'],
                        limitation_data=limitation_data
                    )
                    self.message_user(request, f"Limitation '{obj.name}' updated in MikroTik UserManager.")
                else:
                    mikrotik_manager.create_limitation(
                        limitation_data=limitation_data
                    )
                    self.message_user(request, f"Limitation '{obj.name}' created in MikroTik UserManager.")
            except Exception as e:
                self.message_user(request, f"Error syncing limitation '{obj.name}' with MikroTik UserManager: {e}", level='error')

    sync_limitations_to_mikrotik.short_description = "Sync selected limitations to MikroTik"


class ProfileLimitationAdmin(MultitenantAdminMixin, admin.ModelAdmin):
    list_display = ('mikrotik_id', 'profile', 'limitation', 'organization__slug')
    search_fields = ('profile', 'limitation')
    list_filter = ('weekdays',)
    readonly_fields = ('mikrotik_id', 'created', 'modified')


# Register models
admin.site.register(Profile, ProfileAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Limitation, LimitationAdmin)
admin.site.register(ProfileLimitation, ProfileLimitationAdmin)





