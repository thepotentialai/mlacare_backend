from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

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
    # Patient-agent matching
    path('api/matching/', include('matching.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
