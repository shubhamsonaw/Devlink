from django.shortcuts import render
from problems.models import Problem
from solutions.models import Solution
from django.contrib.auth.models import User
from django.db.models import Count
from django.core.cache import cache
import logging


logger = logging.getLogger(__name__)

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
    cache_key = 'home:dashboard:v1'
    try:
        dashboard_data = cache.get(cache_key)
    except Exception:
        # A temporary cache outage should not take down the public homepage.
        logger.warning('Redis cache unavailable; loading homepage data from PostgreSQL.', exc_info=True)
        dashboard_data = None

    if dashboard_data is None:
        dashboard_data = {
            'problems': list(Problem.objects.order_by('-created_at')[:5]),
            'solutions': list(
                Solution.objects.select_related('problem', 'user').order_by('-created_at')[:5]
            ),
            'top_users': list(
                User.objects.annotate(total_solutions=Count('solutions'))
                .order_by('-total_solutions')[:5]
            ),
        }
        try:
            # This is public, non-personalized feed data. Keep its stale window short.
            cache.set(cache_key, dashboard_data, timeout=60)
        except Exception:
            logger.warning('Could not save homepage data to Redis cache.', exc_info=True)

    return render(request, 'home.html', {
        **dashboard_data,
    })
