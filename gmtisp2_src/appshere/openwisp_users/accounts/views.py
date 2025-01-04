from allauth.account.forms import ChangePasswordForm as BaseChangePasswordForm
from allauth.account.views import PasswordChangeView as BasePasswordChangeView
from django import forms
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView


class ChangePasswordForm(BaseChangePasswordForm):
    next = forms.CharField(widget=forms.HiddenInput, required=False)


class PasswordChangeView(BasePasswordChangeView):
    form_class = ChangePasswordForm
    template_name = 'account/password_change.html'
    success_url = reverse_lazy('account_change_password_success')

    def get_success_url(self):
        if self.request.POST.get(REDIRECT_FIELD_NAME):
            return self.request.POST.get(REDIRECT_FIELD_NAME)
        return super().get_success_url()

    def get_initial(self):
        data = super().get_initial()
        data['next'] = self.request.GET.get(REDIRECT_FIELD_NAME)
        return data


password_change = login_required(PasswordChangeView.as_view())
password_change_success = login_required(
    TemplateView.as_view(template_name='account/password_change_success.html')
)


class ProfileView(TemplateView):
    template_name = 'accounts/profile.html'


from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from openwisp_users.models import User
# from gmtisp_billing.models import Order, PlanQuota

class UserDashboardView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/user_dashboard.html'
    context_object_name = 'user'

    def get_object(self, queryset=None):
        # Always return the current logged-in user
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        
        # Get user plan details
        user_plan = getattr(user, 'userplan', None)
        current_plan = user_plan.plan if user_plan else None

        # Get the current plan's quota
        current_plan_quota = None
        if current_plan:
            # Assuming AbstractPlanQuota is the model connecting Plan to quota
            current_plan_quota = PlanQuota.objects.filter(plan=current_plan).first()

        # Get the most recent 5 completed orders for the user
        recent_orders = Order.objects.filter(
            user=user,
            status=Order.STATUS.COMPLETED
        ).order_by('-completed')[:5]

        context.update({
            'page_title': 'Dashboard',
            'user_plan': user_plan,
            'current_plan': current_plan,
            'current_plan_quota': current_plan_quota,
            'recent_orders': recent_orders,
            'current_order': recent_orders.first() if recent_orders else None
        })
        
        return context

