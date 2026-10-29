from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Create solution
    path('create/<int:problem_id>/', views.create_solution, name='solution_create'),

    # View all solutions for a problem
    path('problem/<int:problem_id>/', views.solution_list, name='solution_list'),
    
    path('vote/<int:solution_id>/', views.toggle_vote, name='toggle_vote'),
    
    path('accept/<int:solution_id>/', views.accept_solution, name='accept_solution'),
    
    path('comment/<int:solution_id>/', views.add_comment, name='add_comment'),
    
]