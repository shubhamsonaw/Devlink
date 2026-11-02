from django.urls import path

from .api_views import ProblemCreateAPIView


urlpatterns = [
    path('', ProblemCreateAPIView.as_view(), name='api_problem_create'),
]
