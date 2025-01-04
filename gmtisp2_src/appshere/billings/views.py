# mpi_src/usermanager/views.py
import uuid
import logging
import requests
import paystack
import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, FormView, RedirectView, View, CreateView, UpdateView
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache

from utils.mikrotik_userman import init_mikrotik_manager
from appshere.accounts.views import OrganizationMixin
from appshere.accounts.models import User
from .models import Profile, UserProfile, Payment, Session

paystack.api_key = settings.PAYSTACK_SECRET_KEY
mikrotik_manager = init_mikrotik_manager()

logger = logging.getLogger(__name__)


class ProfileListView(LoginRequiredMixin, ListView):
    model = Profile
    template_name = 'billings/profile_list.html'
    context_object_name = 'profiles'

    def get_queryset(self):
        # Get the organization associated with the logged-in user
        organization = self.request.user.organization
        # Filter profiles by the organization
        return Profile.objects.filter(organization=organization)


class UserProfileListView(OrganizationMixin, ListView):
    model = UserProfile
    template_name = 'billings/user_profile_list.html'
    context_object_name = 'user_profiles'

    def get_queryset(self):
        queryset = UserProfile.objects.all()
        return self.get_queryset_filtered_by_organization(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'User Orders'
        return context


class PaymentListView(OrganizationMixin, ListView):
    model = Payment
    template_name = 'billings/payment_list.html'
    context_object_name = 'payments'

    def get_queryset(self):
        queryset = Payment.objects.all()
        return self.get_queryset_filtered_by_organization(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Payments'
        return context


class SessionListView(OrganizationMixin, ListView):
    template_name = 'billings/sessions.html'
    context_object_name = 'user_sessions'

    def get_queryset(self):
        queryset = Session.objects.all()
        return self.get_queryset_filtered_by_organization(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Sessions'
        return context


class InitiatePaymentView(View):
    def get(self, request, profile_id):
        try:
            profile = get_object_or_404(Profile, id=profile_id)
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'User not authenticated'}, status=401)

            if not request.user.email:
                return JsonResponse({'error': 'Email is required'}, status=400)

            payment_reference = str(uuid.uuid4())
            
            # Convert price to float and then multiply by 100, and to integer
            try:
                amount = int(float(profile.price) * 100)
            except ValueError:
                return JsonResponse({'error': 'Invalid price format'}, status=400)

            payment_data = {
                "email": request.user.email,
                "amount": amount,
                "reference": payment_reference,
                "callback_url": request.build_absolute_uri(reverse('verify_payment')) + f"?user_id={request.user.id}&profile_id={profile.id}"
            }

            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            logger.debug(f"Initiating payment with reference: {payment_reference}")

            response = requests.post('https://api.paystack.co/transaction/initialize', json=payment_data, headers=headers)
            response.raise_for_status()  # Raise error for bad responses

            payment_url = response.json()['data']['authorization_url']
            return redirect(payment_url)

        except requests.RequestException as e:
            logger.error(f"Error during payment initiation: {e}", exc_info=True)
            return JsonResponse({'error': 'Payment initiation failed'}, status=500)


class VerifyPaymentView(View):
    def get(self, request):
        reference = request.GET.get('reference')
        user_id = request.GET.get('user_id')
        profile_id = request.GET.get('profile_id')
        mikrotik_id = request.GET.get('mikrotik_id')

        if not all([reference, user_id, profile_id]):
            return JsonResponse({'error': 'Reference, user ID, and profile ID are required'}, status=400)

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        try:
            logger.debug(f"Verifying payment with reference: {reference}")

            response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get('data', {}).get('status') == 'success':
                user = get_object_or_404(User, id=user_id)
                profile = get_object_or_404(Profile, id=profile_id)

                user_organization = user.organization # Get the user's organization
                user_profile, _ = UserProfile.objects.get_or_create(mikrotik_id=mikrotik_id, user=user, profile=profile, organization=user_organization)

                # Create the Payment record
                Payment.objects.create(
                    user=user,
                    user_profile=user_profile,
                    profile=profile,
                    organization=user_organization,
                    method="ONLINE",
                    trans_end=datetime.datetime.now(),
                    trans_status="completed",
                    price=response_data['data']['amount'] / 100,
                    paystack_reference=reference
                )

                # # assign user profile upon payment completion
                # from usermanager.tasks import create_or_update_user_profile_event
                # # create_or_update_user_profile_event.delay(user_profile.id)
                # create_or_update_user_profile_event(user_profile.id)

                return redirect('payment_success')

            else:
                logger.warning(f"Payment verification failed for reference: {reference}. Status: {response_data.get('data', {}).get('status')}")
                return redirect('payment_failed')

        except requests.RequestException as e:
            logger.error(f"Error verifying payment with Paystack: {e}", exc_info=True)
            return JsonResponse({'error': 'Payment verification failed'}, status=500)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


def payment_success(request):
    return render(request, 'billings/payment_success.html')

def payment_failed(request):
    return render(request, 'billings/payment_failed.html')


# Querying directly from Mikrotik
# class UserDetailView(LoginRequiredMixin, DetailView):
#     model = User
#     template_name = 'billings/user_detail.html'
#     context_object_name = 'user_detail'

#     def get_object(self, queryset=None):
#         # Always return the current logged-in user
#         return self.request.user

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)

#         # Fetch all user profiles from MikroTik
#         all_profiles = mikrotik_manager.get_user_profiles()

#         # Filter profiles by the current user and 'running-active' state
#         running_active_profiles = [
#             profile for profile in all_profiles 
#             if profile.get('state') == 'running-active' and profile.get('user') == self.request.user.username
#         ]

#         # Retrieve related profiles from the Profile model based on the user's running-active profiles
#         related_profiles = Profile.objects.filter(name__in=[p.get('profile') for p in running_active_profiles])

#         # Filter profiles by the current user
#         user_profiles = [
#             profile for profile in all_profiles
#             if profile.get('user') == self.request.user.username
#         ]

#         # Sort profiles by the 'end_time' field (assuming it's formatted properly as date or datetime)
#         # Sort in descending order to get the most recent ones first
#         user_profiles_sorted = sorted(user_profiles, key=lambda p: p.get('end_time', ''), reverse=True)

#         # Get the 5 most recent profiles based on 'end_time'
#         recent_profiles = user_profiles_sorted[:5]

#         # Fetch the current user's sessions from MikroTik
#         user_sessions = mikrotik_manager.get_user_sessions(self.request.user.username)
   
#         # Filter sessions with the status 'start' (active sessions)
#         # active_sessions = [session for session in user_sessions if session.get('status') == 'start' or 'start,interim']
#         active_sessions = [session for session in user_sessions if session.get('ended') == None]

#         # Sort in descending order to get the most recent ones first
#         # user_profiles_sorted = sorted(user_sessions, key=lambda p: p.get('end_time', ''), reverse=True)

#         context['running_active_profiles'] = running_active_profiles
#         context['related_profiles'] = related_profiles
#         context['recent_profiles'] = recent_profiles
#         context['user_sessions'] = user_sessions
#         context['active_sessions'] = active_sessions

#         return context


# class UserProfileListView(LoginRequiredMixin, ListView):
#     model = User
#     template_name = 'billings/user_profile_list.html'
#     context_object_name = 'user_profiles'

#     def get_queryset(self):
#         queryset = super().get_queryset()

#         # Superusers see all profiles, regular users only see their own
#         if self.request.user.is_superuser:
#             return queryset
#         return queryset.filter(pk=self.request.user.pk)

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # Add user profiles to the context
#         if self.request.user.is_superuser:
#             context['user_profiles'] = mikrotik_manager.get_user_profiles()  # Superusers get all profiles
#         else:
#             all_profiles = mikrotik_manager.get_user_profiles()  # Fetch all profiles
#             user_profiles = [profile for profile in all_profiles if profile.get('user') == self.request.user.username]
#             context['user_profiles'] = user_profiles

#         return context


# class SessionListView(LoginRequiredMixin, ListView):
#     template_name = 'billings/sessions.html'
#     context_object_name = 'mikrotik_sessions'

#     def get_queryset(self):
#         # Superusers see all sessions; regular users see only their own
#         if self.request.user.is_superuser:
#             return mikrotik_manager.get_sessions()
#         else:
#             if hasattr(mikrotik_manager, 'get_user_sessions'):
#                 return mikrotik_manager.get_user_sessions(self.request.user.username)
#             else:
#                 raise ImproperlyConfigured("'MikroTikUserManager' must implement 'get_user_sessions' for regular users.")

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # Add profiles to the context
#         if self.request.user.is_superuser:
#             context['user_profiles'] = mikrotik_manager.get_user_profiles()  # Get all profiles for superusers
#         else:
#             all_profiles = mikrotik_manager.get_user_profiles()  # Fetch all profiles
#             user_profile = next((profile for profile in all_profiles if profile.get('user') == self.request.user.username), None)
#             context['user_profile'] = user_profile

#         return context