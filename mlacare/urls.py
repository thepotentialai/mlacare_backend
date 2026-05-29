from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('django-admin/', admin.site.urls),
    # Auth & accounts
    path('api/auth/', include('accounts.urls')),
    # Patient routes
    path('api/patients/', include('patients.urls')),
    # Agent routes
    path('api/agents/', include('agents.urls')),
    # Visits & health reports
    path('api/visits/', include('visits.urls')),
    # Notifications & SOS
    path('api/notifications/', include('notifications.urls')),
    # Payments
    path('api/payments/', include('payments.urls')),
    # Admin API
    path('api/admin/', include('admin_api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
elif getattr(settings, 'SERVE_MEDIA_VIA_DJANGO', False):
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
