from django.urls import path
from dashboard import views as dashboard_views

urlpatterns = [
    path('dashboard/', dashboard_views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/get_account_chart/', dashboard_views.get_account_chart, name='get_account_chart'),
    path('dashboard/get_job_chart/', dashboard_views.get_job_chart, name='get_job_chart'),

]