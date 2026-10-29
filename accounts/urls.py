from django.contrib import admin
from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

app_name = 'accounts'
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),

    # path('profile/', views.profile_view, name='profile'),
    
    # path('profile/<str:username>/', views.user_profile_view, name='user_profile'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/', views.my_profile, name='my_profile'),
    path('edit/',views.edit_profile, name='edit_profile'),
  
]
