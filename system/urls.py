from system import views as system_views
from django.urls import path, include

urlpatterns = [
    path('api-system/system/', system_views.System.as_view()),
    path('api-system/system/calculate_cost', system_views.CalculateCost.as_view()),
    path('api-system/dropbox/', system_views.Dropbox.as_view()),
    path('api-system/rendershare/', system_views.RenderShare.as_view(), name='rendershare_api'),
    path('api-system/rendershare/log/', system_views.LogAPI.as_view()),
    path('api-system/urls/', system_views.URLsAPI.as_view()),
    path('api-system/submitters/keyshot/<int:version>', system_views.KeyShotSubmitterAPI.as_view()),
]
