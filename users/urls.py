from django.urls import path, re_path, include
from users import views as users_views


urlpatterns = [
    path('', users_views.Login.as_view(), name='user_login'),
    path('register/', users_views.Register.as_view(), name='register'),
    path('profile/', users_views.Profile.as_view(), name='profile'),
    path('password_reset/', users_views.UserPasswordResetView.as_view(), name='user_password_reset'),
    path('password_change/', users_views.UserPasswordChangeView.as_view(), name='user_password_change'),
    path('reset/<uidb64>/<token>/', users_views.UserPasswordResetConfirmView.as_view(),
         name='user_password_reset_confirm'),
    path('activate/', users_views.activate, name='activate'),
    path('activate/<slug:username>/', users_views.activate, name='activate'),
    path('activate/<slug:username>/<slug:token>/', users_views.activate, name='activate'),
]

# user rest framework api urls
urlpatterns += [
    path('api-user/user/', users_views.UserAPI.as_view()),
]
