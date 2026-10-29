from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # List all problems
    path('', views.problem_list, name='problem_list'),

    # Create new problem
    path('create/', views.create_problem, name='create_problem'),
    path('<int:problem_id>/status/', views.set_problem_status, name='set_problem_status'),

    # View single problem (detail page)
    path('<int:problem_id>/', views.problem_detail, name='problem_detail'),
   
]
