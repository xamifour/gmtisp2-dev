# mpi_src/appshere/accounts/urls.py

from django.urls import path

from . import views

# app_name = 'accounts'  

urlpatterns = [
    path('sign-up/', views.SignUpView.as_view(), name='sign_up'),
    path('sign-in/', views.SignInView.as_view(), name='sign_in'),
    path('sign-out/', views.SignOutView.as_view(), name='sign_out'),
    path('', views.UserDetailView.as_view(), name='user_detail'),
    path('user-usage/', views.UserUsageListView.as_view(), name='user_usage_list'),

    path('organization/create/', views.OrganizationCreateUpdateView.as_view(), name='organization_create'),
    path('organization/<uuid:pk>/edit/', views.OrganizationCreateUpdateView.as_view(), name='organization_edit'),
    path('organizations/', views.OrganizationListView.as_view(), name='organization_list'),
]

