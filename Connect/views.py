from django.shortcuts import render
from problems.models import Problem
from solutions.models import Solution
from django.contrib.auth.models import User
from django.db.models import Count

# def home(request):
    
#     problems = Problem.objects.order_by('-created_at')[:5]

#     solutions = Solution.objects.order_by('-created_at')[:5]

#     top_users = User.objects.annotate(
#         total_solutions=Count('solutions')
#     ).order_by('-total_solutions')[:5]

#     context = {
#         'problems': problems,
#         'solutions': solutions,
#         'top_users': top_users,
#     }

#     return render(request, 'home.html', context)


def home(request):
    problems = Problem.objects.order_by('-created_at')[:5]
    solutions = Solution.objects.order_by('-created_at')[:5]
    top_users = User.objects.annotate(
        total_solutions=Count('solutions')
    ).order_by('-total_solutions')[:5]

    return render(request, 'home.html', {
        'problems': problems,
        'solutions': solutions,
        'top_users': top_users,
    })
