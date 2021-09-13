from django.urls import path
from job import views as job_views
from job import api_views as job_api_views

urlpatterns = [
    path('jobs/job_list/', job_views.JobListView.as_view(), name='job_list'),
    path('jobs/submit_job/', job_views.SubmitJobView.as_view(), name='submit_job'),
    path('jobs/job_output_url/', job_views.job_output_url, name='job_output_url'),
    path('jobs/submit_file_select/get_file_select/', job_views.get_file_select, name='get_file_select'),
    path('jobs/submit_file_select/', job_views.SubmitFileSelectView.as_view(), name='submit_file_select'),
    path('jobs/advanced_keyshot_submitter/', job_views.AdvancedSubmitterView.as_view(), name='advanced_keyshot_submitter'),
    path('jobs/advanced_keyshot_submitter/<uuid:session_id>/', job_views.AdvancedSubmitterView.as_view(), name='advanced_keyshot_submitter'),
    path('jobs/advanced_keyshot_submitter/<str:file_name>/', job_views.AdvancedSubmitterView.as_view(), name='advanced_keyshot_submitter'),
]

# api routes
urlpatterns += [
    path('api-job/job/', job_api_views.JobAPI.as_view()),
    path('api-job/submit_session/', job_api_views.SubmitSessionAPI.as_view()),
]