# mpi_src/appshere/accounts/admin.py
import logging
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from django.utils.timezone import now

from datetime import datetime
import csv
from django.http import HttpResponse
from django.utils.encoding import smart_str

from utils.mikrotik_userman import init_mikrotik_manager
from utils.data_preparation import prepare_user_data

from appshere.billings.models import UserProfile, Profile, Payment, Session
from .models import User, UserUsage, Organization, Dashboard

# Initialize MikroTikUserManager
mikrotik_manager = init_mikrotik_manager()

logger = logging.getLogger(__name__)



from django.contrib import admin

admin.site.site_header = "GMTISP Admin Login"
admin.site.site_title = "GMTISP Admin"
admin.site.index_title = "Welcome to the GMTISP Admin Panel"


class CacheAdmin(admin.ModelAdmin):
    change_list_template = "admin/clear_cache.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('clear-cache/', self.admin_site.admin_view(self.clear_cache), name='clear_cache'),
        ]
        return custom_urls + urls

    def clear_cache(self, request):
        cache.clear()
        logger.info(f'Cache cleared by {request.user.username} at {now()}.')
        self.message_user(request, "Cache has been cleared successfully.", messages.SUCCESS)
        return HttpResponseRedirect(reverse('admin:index'))


# class MultitenantAdminMixin:
#     '''
#     Mixin that restricts the visibility of model instances based on the user's organization.
#     Superusers can access all objects without being associated with an organization.
#     Staff users see all objects in the organization they belong to.
#     Regular users see only objects of their organization that belong to them.
#     '''
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
        
#         # Superuser sees all objects
#         if request.user.is_superuser:
#             return qs
        
#         # Staff users see all objects in their organization
#         if request.user.is_staff:
#             return qs.filter(organization=request.user.organization)
        
#         # Regular users see only their own objects in their organization
#         if request.user.is_authenticated:
#             return qs.filter(organization=request.user.organization, owner=request.user)

#         return qs.none()  # No objects for unauthenticated users

#     def save_model(self, request, obj, form, change):
#         if not request.user.is_superuser:
#             obj.organization = request.user.organization  # Assign organization for non-superusers
#             if hasattr(obj, 'owner'):
#                 obj.owner = request.user  # Assign owner for non-superusers
#         super().save_model(request, obj, form, change)

#     def formfield_for_foreignkey(self, db_field, request, **kwargs):
#         if db_field.name == "organization":
#             if request.user.is_superuser:
#                 # Superuser sees all organizations
#                 kwargs["queryset"] = Organization.objects.all()
#             elif request.user.is_staff:
#                 # Staff users see only their associated organization
#                 kwargs["queryset"] = Organization.objects.filter(id=request.user.organization.id)
#             else:
#                 # Regular users see only their associated organization
#                 kwargs["queryset"] = Organization.objects.filter(id=request.user.organization.id)
#         return super().formfield_for_foreignkey(db_field, request, **kwargs)

#     def get_form(self, request, obj=None, **kwargs):
#         form = super().get_form(request, obj, **kwargs)
#         if not request.user.is_superuser:
#             form.base_fields['organization'].disabled = True  # Disable organization field
#         return form

#     def has_change_permission(self, request, obj=None):
#         return request.user.is_superuser or (obj and obj.organization == request.user.organization) or super().has_change_permission(request, obj)

#     def has_delete_permission(self, request, obj=None):
#         return request.user.is_superuser or (obj and obj.organization == request.user.organization) or super().has_delete_permission(request, obj)

#     def has_view_permission(self, request, obj=None):
#         return request.user.is_superuser or (obj and (obj.organization == request.user.organization and (request.user.is_staff or obj.owner == request.user))) or super().has_view_permission(request, obj)
    
class MultitenantAdminMixin:
    '''
    Mixin that restricts the visibility of model instances based on the user's organization.
    Superusers can access all objects without restriction.
    Staff users see all objects in their organization.
    Regular users see only objects that belong to them within their organization.
    '''
    
    def _get_organization_queryset(self, request):
        """Helper method to return the queryset filtered by the user's organization."""
        if request.user.is_superuser:
            return Organization.objects.all()  # Superusers can access all organizations
        return Organization.objects.filter(id=request.user.organization.id)  # Filtered to the user's organization

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # Superuser sees all objects
        if request.user.is_superuser:
            return qs

        # Staff users see all objects in their organization
        if request.user.is_staff:
            return qs.filter(organization=request.user.organization)

        # Regular users see only their own objects in their organization
        if request.user.is_authenticated:
            return qs.filter(organization=request.user.organization, owner=request.user)

        return qs.none()  # No objects for unauthenticated users

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            # Non-superusers must have their organization and owner set
            obj.organization = request.user.organization
            if hasattr(obj, 'owner'):
                obj.owner = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organization":
            # Limit queryset for organization based on user role
            kwargs["queryset"] = self._get_organization_queryset(request)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields['organization'].disabled = True  # Disable organization field for non-superusers
        return form

    def has_change_permission(self, request, obj=None):
        # Allow changes if user is superuser, or the object belongs to the user's organization
        return request.user.is_superuser or (obj and obj.organization == request.user.organization) or super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        # Allow delete if user is superuser, or the object belongs to the user's organization
        return request.user.is_superuser or (obj and obj.organization == request.user.organization) or super().has_delete_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        # Allow view if user is superuser, or the object belongs to user's organization and is either owned by the user or the user is staff
        return request.user.is_superuser or (
            obj and
            obj.organization == request.user.organization and
            (request.user.is_staff or obj.owner == request.user)
        ) or super().has_view_permission(request, obj)

    
# not working
class DashboardAdmin(MultitenantAdminMixin, admin.ModelAdmin):
    change_list_template = "admin/dashboard.html"  # Custom template for the dashboard

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='admin-dashboard'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        organizations_count = Organization.objects.count()
        users_count = User.objects.count()
        user_usages_count = UserUsage.objects.count()
        profiles_count = Profile.objects.count()
        payments_count = Payment.objects.count()
        sessions_count = Session.objects.count()

        context = {
            'organizations_count': organizations_count,
            'users_count': users_count,
            'user_usages_count': user_usages_count,
            'profiles_count': profiles_count,
            'payments_count': payments_count,
            'sessions_count': sessions_count,
        }

        print(f"Rendering dashboard with context: {context}")
        return render(request, 'admin/dashboard.html', context)


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'email', 'phone', 'address')
    search_fields = ('name', 'slug', 'email', 'phone')
    ordering = ('name',)
    list_filter = ('address',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        (_('Contact Info'), {
            'fields': ('email', 'phone', 'address', 'url')
        }),
        (_('Branding'), {
            'fields': ('logo', 'theme')
        }),
    )

    def has_delete_permission(self, request, obj=None):
        # Optionally restrict delete permission for organizations
        return super().has_delete_permission(request, obj)


class UserProfileInline(MultitenantAdminMixin, admin.TabularInline):
    model = UserProfile
    extra = 1
    can_delete = False
    verbose_name_plural = 'User Profile'
    fk_name = 'user'
    readonly_fields = ['mikrotik_id', 'end_time', 'state']

class UserAdmin(MultitenantAdminMixin, BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        'mikrotik_id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'organization__slug'
    )
    search_fields = ('username', 'email')
    # ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'password1', 'password2', 'plain_password', 'organization'
                # 'email', 'group', 'shared_users', 'disabled', 'attributes',  
            ),
        }),
    )
    
    fieldsets = (
        (None, {'fields': ('username', 'password', 'plain_password', 'organization')}),
        (_('Personal info'), {'fields': (
            'first_name', 'last_name', 'email', 'phone', 'address', 'notes'
        )}),
        (_('Mikrotik info'), {'fields': (
            'mikrotik_id', 'group', 'otp_secret', 'shared_users', 'attributes',
        )}),
        (_('Permissions'), {'fields': (
            'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'
        )}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'modified')}),
    )

    actions = ['sync_user_to_mikrotik', 'export_users_to_csv']
    readonly_fields = ['mikrotik_id', 'last_login', 'date_joined', 'modified']
    
    def sync_user_to_mikrotik(self, request, queryset):
        """Sync selected users with MikroTik."""
        for obj in queryset:
            try:
                # Prepare user data using the prepare_user_data function
                user_data = prepare_user_data(obj)
                # Check if user exists in MikroTik
                existing_user = next(
                    (u for u in mikrotik_manager.get_users() if u['name'] == obj.username), None
                )
                # If user exists, update the user
                if existing_user:
                    mikrotik_manager.update_user(
                        user_id=existing_user['.id'],  # Pass the existing user ID
                        user_data=user_data  # Pass all user data in a dictionary
                    )
                    self.message_user(request, f"User '{obj.username}' updated in MikroTik UserManager.")
                # If user doesn't exist, create a new user
                else:
                    mikrotik_manager.create_user(
                        user_data=user_data  # Pass all user data in a dictionary
                    )
                    self.message_user(request, f"User '{obj.username}' created in MikroTik UserManager.")
            except Exception as e:
                self.message_user(request, f"Error syncing user '{obj.username}' with MikroTik UserManager: {e}", level='error')

    sync_user_to_mikrotik.short_description = "Sync selected users to MikroTik"

    # Export users to a csv file
    def export_users_to_csv(modeladmin, request, queryset):
        # Check if the queryset has any users with an organization
        first_user = queryset.first()
        organization_slug = 'unknown_organization'  # Default in case no organization is found
        
        # If the first user has an organization, use its slug
        if first_user and first_user.organization:
            organization_slug = first_user.organization.slug

        # Generate filename with organization slug and datetime
        filename = f'users_{organization_slug}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
        
        # Create the response object to return a CSV file
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        
        writer = csv.writer(response)
        
        # Write the header
        writer.writerow([
            'Username', 'Email', 'First Name', 'Last Name', 'Address', 'Organization ID', 'Organization Name', 'Plain Password'
        ])
        
        # Write the user data, including organization data
        for user in queryset:
            organization_id = user.organization.id if user.organization else ''
            organization_name = user.organization.name if user.organization else ''
            writer.writerow([
                smart_str(user.username),
                smart_str(user.email),
                smart_str(user.first_name),
                smart_str(user.last_name),
                smart_str(user.address),
                smart_str(organization_id),
                smart_str(organization_name),
                smart_str(user.plain_password),  # Be cautious about exporting plain passwords
            ])
        
        return response

    export_users_to_csv.short_description = "Export selected users to CSV"


class UserUsageAdmin(MultitenantAdminMixin, admin.ModelAdmin):
    list_display = ('mikrotik_id', 'user', 'formatted_user_download', 'formatted_user_upload', 'formatted_user_traffic', 'total_uptime', 'created', 'organization__slug')
    list_filter = ('created',)
    search_fields = ('user',)
    ordering = ('-created',)
    date_hierarchy = 'created'
    readonly_fields = ('mikrotik_id', 'user', 'created', 'modified', 'formatted_user_download', 'formatted_user_upload', 'formatted_user_traffic', 'total_uptime', 'organization', 'active_sessions', 'active_sub_sessions', 'attributes_details')


# Register models
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Dashboard, DashboardAdmin) 
admin.site.register(User, UserAdmin)
admin.site.register(UserUsage, UserUsageAdmin)
admin.site.register(admin.models.LogEntry, CacheAdmin)





