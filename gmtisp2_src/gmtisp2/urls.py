import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views.generic import TemplateView
from django.views import defaults as default_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('openwisp_users.accounts.urls')),
    # path('api/v1/', include((get_api_urls(api_views), 'users'), namespace='users')),
    path('api/v1/', include('openwisp_users.api.urls')),
    path('api/v1/', include('openwisp_utils.api.urls')),
    path('users/', include('openwisp_users.urls')),

    path('about/', TemplateView.as_view(template_name="gmtisp2/pages/about.html"), name='about'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path('400/', default_views.bad_request, kwargs={"exception": Exception("Bad Request!")},),
        path('403/', default_views.permission_denied, kwargs={"exception": Exception("Permission Denied")},),
        path('404/', default_views.page_not_found, kwargs={"exception": Exception("Page not Found")},),
        path('500/', default_views.server_error),
    ]
     
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
        urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)