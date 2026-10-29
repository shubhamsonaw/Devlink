from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.opportunity_list, name='opportunity_list'),
    path('create/', views.create_opportunity, name='create_opportunity'),
    path('<int:opportunity_id>/close/', views.close_opportunity, name='close_opportunity'),
    
    path('<int:id>/', views.opportunity_detail, name='opportunity_detail'),
    path("invite/", views.send_invitation, name='send_invitation'),
    path('invitations/', views.invitation_list, name='invitation_list'),
    path('application/<int:app_id>/accept/', views.accept_application, name='accept_application'),
    path('application/<int:app_id>/reject/', views.reject_application, name='reject_application'),
    path('solution/<int:solution_id>/invite/', views.invite_solution_collaborator, name='invite_solution_collaborator'),
    path('<int:pk>/apply/', views.apply_opportunity, name='apply_opportunity'),
    path('<int:pk>/applications/', views.view_applications, name='view_applications'),
    path('applications/received/', views.application_list, name='application_list'),
    path('applications/sent/', views.applications, name='applications'),
    path('invitation/<int:pk>/accept/', views.accept_invitation, name='accept_invitation'),
    path('invitation/<int:pk>/reject/', views.reject_invitation, name='reject_invitation'),
    path('sent-invitations/', views.sent_invitations, name='sent_invitations'),
    path('chat/<str:username>/', views.chat, name='chat'),
    path('messages/', views.messages_list, name='messages_list'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/tasks/create/', views.create_project_task, name='create_project_task'),
    path('project-tasks/<int:task_id>/status/', views.update_project_task_status, name='update_project_task_status'),
    path('projects/<int:project_id>/status/', views.set_project_status, name='set_project_status'),

]
