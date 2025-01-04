# mpi_src/appshere/billings/urls.py

from django.urls import path

from . import views

# apps_name = 'billings'

urlpatterns = [
    
    path('plans/', views.ProfileListView.as_view(), name='profile_list'),
    path('user-profiles/', views.UserProfileListView.as_view(), name='user_profile_list'),
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('sessions/', views.SessionListView.as_view(), name='session_list'),

    # Payment paths
    path('initiate-payment/<uuid:profile_id>/', views.InitiatePaymentView.as_view(), name='initiate_payment'),
    path('payment/verify/', views.VerifyPaymentView.as_view(), name='verify_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),

]


