"""rendershot_django URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views

rest_framework_router = DefaultRouter()

urlpatterns = [
    path(os.getenv('SECRET_ADMIN_URL') + '/admin/', admin.site.urls),
    path('', include('job.urls')),
    path('', include('users.urls')),
    path('', include('dashboard.urls')),
    path('', include('payment.urls')),
    path('', include('ticketing.urls')),
    path('', include('system.urls')),
    re_path(r'^jet/', include('jet.urls', 'jet')),  # Django JET URLS
    path("admin/", include('loginas.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^advanced_filters/', include('advanced_filters.urls')),
    re_path(r'^_nested_admin/', include('nested_admin.urls')),
]

# rest framework api urls
urlpatterns += [
    path('api-auth/token/', views.obtain_auth_token),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
