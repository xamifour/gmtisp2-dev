# mpi_src/appshere/accounts/views.py
import logging
import paystack

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, FormView, RedirectView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.urls import reverse_lazy

from appshere.billings.models import ( Payment, UserProfile, Session,
    get_user_all_time_traffic, get_user_all_time_uptime,
    get_user_traffic_and_time_for_a_period,
    format_traffic_size,
)

from utils.mikrotik_userman import init_mikrotik_manager
from .forms import SignUpForm, SignInForm
from .models import User, UserUsage

paystack.api_key = settings.PAYSTACK_SECRET_KEY
mikrotik_manager = init_mikrotik_manager()

logger = logging.getLogger(__name__)

class SignUpView(FormView):
    template_name = 'accounts/sign_up.html'
    form_class = SignUpForm
    success_url = reverse_lazy('sign_in')

    def form_valid(self, form):
        form.save()
        # # Automatically log the user in after signing up (optional)
        # login(self.request, user)
        return super().form_valid(form)

class SignInView(FormView):
    template_name = 'accounts/sign_in.html'
    form_class = SignInForm
    success_url = reverse_lazy('user_detail')

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        return super().form_valid(form)

class SignOutView(LoginRequiredMixin, RedirectView):
    url = reverse_lazy('sign_in')

    def get(self, request, *args, **kwargs):
        logout(request)
        return super().get(request, *args, **kwargs)


# class OrganizationMixin(LoginRequiredMixin):
#     '''
#     Superusers should have access to all objects.
#     Staff users should have access to objects belonging to their organization.
#     Normal users should have access only to objects that belong to them within their organization.
#     '''
#     def get_user_organization(self):
#         if self.request.user.is_superuser:
#             return None  # Superuser context; return all organizations
#         return self.request.user.organization  # Regular user context

#     def get_queryset_filtered_by_organization(self, queryset):
#         organization = self.get_user_organization()
#         if organization is None:
#             return queryset  # For superusers, return the full queryset
#         elif self.request.user.is_staff:
#             return queryset.filter(user__organization=organization)
#         else:
#             return queryset.filter(user__organization=organization, user=self.request.user)


from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin

class OrganizationMixin(LoginRequiredMixin):
    '''
    Mixin that restricts access to objects based on the user's organization.
    
    Superusers: Access to all objects without restriction.
    Staff users: Access to all objects in their assigned organization.
    Normal users: Access only to objects belonging to them within their organization.
    '''
    
    def get_user_organization(self):
        """
        Returns the organization for the current user. 
        Superusers return None to indicate no restriction on organization.
        """
        if self.request.user.is_superuser:
            return None  # Superusers can access all organizations.
        if hasattr(self.request.user, 'organization'):
            return self.request.user.organization  # Regular users have an associated organization.
        raise PermissionDenied("User is not associated with any organization.")  # Raise error if organization is missing

    def get_queryset_filtered_by_organization(self, queryset):
        """
        Filters the queryset based on the user's organization.
        - Superusers get the full queryset (no organization filter).
        - Staff users are filtered by their organization.
        - Regular users are filtered by both their organization and ownership.
        """
        organization = self.get_user_organization()

        # Superusers: No restriction on organization, return full queryset.
        if organization is None:
            return queryset

        # Staff users: Filter by their associated organization, but not restricted to ownership.
        if self.request.user.is_staff:
            return queryset.filter(user__organization=organization)

        # Regular users: Filter by both organization and ownership.
        if self.request.user.is_authenticated:
            return queryset.filter(user__organization=organization, user=self.request.user)

        return queryset.none()  # Unauthenticated users get no results.

    def get_object(self, queryset=None):
        """
        Override `get_object` to apply organization-based restrictions for retrieving objects.
        """
        obj = super().get_object(queryset)
        
        # Ensure the object belongs to the user's organization (for non-superusers).
        organization = self.get_user_organization()
        if organization and (obj.user.organization != organization or (obj.user != self.request.user and not self.request.user.is_staff)):
            raise PermissionDenied("You do not have permission to access this object.")
        
        return obj


class UserDetailView(OrganizationMixin, DetailView):
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_detail'

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Dashboard'
        cache_key = f"user_detail_{self.request.user.id}"
        cache_timeout = 300  # Cache timeout in seconds (5 minutes)

        # Check cache for existing data
        user_related_data = cache.get(cache_key)

        if not user_related_data:
            user_related_data = self.get_user_related_data()
            # Store the data in cache
            cache.set(cache_key, user_related_data, cache_timeout)
        else:
            logger.debug(f"Fetched user detail from cache for user ID: {self.request.user.id}")

        context.update(user_related_data)
        return context

    def get_user_related_data(self):
        user_profiles = UserProfile.objects.filter(user=self.request.user)
        recent_user_profiles = user_profiles.order_by('-created')[:5]
        current_user_profile = user_profiles.order_by('-created')[:1]
        running_active_profiles = user_profiles.filter(state='running-active')

        user_payments = Payment.objects.filter(user=self.request.user).order_by('-trans_end')[:5]
        user_sessions = Session.objects.filter(user=self.request.user).select_related('user').order_by('-session_id')
        active_sessions = user_sessions.filter(ended__isnull=True)

        user_all_time_traffic = get_user_all_time_traffic(self.request.user)
        user_all_time_uptime = get_user_all_time_uptime(self.request.user)

        user_all_time_traffic = {
            'total_download': format_traffic_size(user_all_time_traffic.get('total_download', 0)),
            'total_upload': format_traffic_size(user_all_time_traffic.get('total_upload', 0)),
            'total_traffic': format_traffic_size(user_all_time_traffic.get('total_traffic', 0)),
        }

        usage_for_a_period = {'error': 'No UserProfile found for this user.'}
        if user_profiles.exists():
            usage_for_a_period = get_user_traffic_and_time_for_a_period(user_profiles.first().id)

        usage_for_a_period.update({
            'total_download': format_traffic_size(usage_for_a_period.get('total_download', 0)),
            'total_upload': format_traffic_size(usage_for_a_period.get('total_upload', 0)),
            'total_traffic': format_traffic_size(usage_for_a_period.get('total_traffic', 0)),
            'total_time': f"{int(usage_for_a_period.get('total_time', 0))} seconds"
        })

        return {
            'recent_user_profiles': recent_user_profiles,
            'current_user_profile': current_user_profile,
            'running_active_profiles': running_active_profiles,
            'recent_user_payments': user_payments,
            'user_sessions': user_sessions,
            'active_sessions': active_sessions,
            'user_all_time_traffic': user_all_time_traffic,
            'user_all_time_uptime': user_all_time_uptime,
            'usage_for_a_period': usage_for_a_period,
        }


class UserUsageListView(OrganizationMixin, ListView):
    template_name = 'accounts/user_usage_list.html'
    context_object_name = 'user_usages'

    def get_queryset(self):
        queryset = UserUsage.objects.all()
        return self.get_queryset_filtered_by_organization(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'User Usage Data'
        return context
    

# views.py
from .models import Organization
from .forms import OrganizationForm

class OrganizationListView(ListView):
    model = Organization
    template_name = 'accounts/organization_list.html'  # Template to render
    context_object_name = 'organizations'  # Name to use in the template context

class OrganizationCreateUpdateView(CreateView, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'accounts/organization_form.html'
    context_object_name = 'form'
    success_url = reverse_lazy('organization_list')

    # This method handles whether you're updating or creating
    def get_object(self, queryset=None):
        """
        Override to fetch the object if it exists. This method will be
        called for both create and update operations.
        """
        if self.kwargs.get('pk'):
            # If there's a primary key in the URL, it means we are editing
            return get_object_or_404(Organization, pk=self.kwargs.get('pk'))
        return None  # For create, return None to create a new object

    def form_valid(self, form):
        # You can add custom form handling here if needed
        return super().form_valid(form)

