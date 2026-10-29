from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseNotAllowed
from django.db.models import Count
from django.db import transaction

from .models import Solution
from problems.models import Problem
from .models import Vote
from .models import Comment
from opportunities.models import Connection, Invitation
from django.db.models import Q

# Create your views here.

@login_required
def create_solution(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    if problem.status == 'resolved':
        messages.info(request, "This problem is resolved and is no longer accepting solutions.")
        return redirect('problem_detail', problem_id=problem.id)

    if request.method == 'POST':
        explanation = request.POST.get('explanation', '').strip()
        code = request.POST.get('code', '').strip()

        # ✅ VALIDATION
        if not explanation and not code:
            return render(request, "solution_create.html", {
                "problem": problem,
                "error": "⚠️ Please add explanation or code before submitting."
            })

        # ✅ SAVE
        Solution.objects.create(
            user=request.user,
            problem=problem,
            explanation=explanation,
            code=code
        )

        messages.success(request, "Solution submitted successfully")
        return redirect('problem_detail', problem_id=problem.id)

    return render(request, "solution_create.html", {
        "problem": problem
    })




# def solution_list(request, problem_id):
#     problem = get_object_or_404(Problem, id=problem_id)

#     sort = request.GET.get('sort', 'latest')

#     if sort == 'popular':
#         solutions = problem.solutions.annotate(
#             vote_count=Count('votes')
#         ).order_by('-is_accepted', '-vote_count', '-created_at')
#     else:
#         solutions = problem.solutions.all().order_by('-is_accepted', '-created_at')

#     return render(request, 'solution_list.html', {
#         'problem': problem,
#         'solutions': solutions,
#         'current_sort': sort
#     })
    


def solution_list(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)

    sort = request.GET.get('sort', 'latest')

    if sort == 'popular':
        solutions = problem.solutions.annotate(
            vote_count=Count('votes')
        ).order_by('-is_accepted', '-vote_count', '-created_at')
    else:
        solutions = problem.solutions.all().order_by('-is_accepted', '-created_at')

    # 🔥 IMPORTANT: track user votes
    user_votes = []
    pending_solution_invites = []
    connected_solver_ids = []
    if request.user.is_authenticated:
        user_votes = list(
            Vote.objects.filter(user=request.user, solution__in=solutions)
            .values_list('solution_id', flat=True)
        )
        if request.user == problem.user:
            pending_solution_invites = list(
                Invitation.objects.filter(
                    sender=request.user, status='pending', solution__in=solutions
                ).values_list('solution_id', flat=True)
            )
            connected_solver_ids = list(
                Connection.objects.filter(Q(user1=request.user) | Q(user2=request.user)).values_list(
                    'user1_id', 'user2_id'
                )
            )
            connected_solver_ids = {
                user_id for pair in connected_solver_ids for user_id in pair if user_id != request.user.id
            }

    return render(request, 'solution_list.html', {
        'problem': problem,
        'solutions': solutions,
        'current_sort': sort,
        'user_votes': user_votes,
        'pending_solution_invites': pending_solution_invites,
        'connected_solver_ids': connected_solver_ids,
    })
    


@login_required
def toggle_vote(request, solution_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    solution = get_object_or_404(Solution, id=solution_id)

    vote = Vote.objects.filter(user=request.user, solution=solution)

    if vote.exists():
        vote.delete()
        voted = False
    else:
        Vote.objects.create(user=request.user, solution=solution)
        voted = True

    return JsonResponse({
        'voted': voted,
        'total_votes': solution.votes.count()
    })
    
@login_required
def accept_solution(request, solution_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    solution = get_object_or_404(Solution, id=solution_id)
    problem = solution.problem

    # 🔒 Only problem owner can accept
    if request.user != problem.user:
        messages.error(request, "You are not allowed to accept this solution")
        return redirect('problem_detail', problem_id=problem.id)

    if not solution.is_accepted:
        with transaction.atomic():
            Solution.objects.filter(problem=problem, is_accepted=True).update(is_accepted=False)
            solution.is_accepted = True
            solution.save(update_fields=['is_accepted'])
            if problem.status == 'resolved':
                problem.status = 'open'
                problem.save(update_fields=['status'])

    messages.success(request, "Solution accepted successfully")

    return redirect('problem_detail', problem_id=problem.id)


@login_required
def add_comment(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)

    if request.method == "POST":
        text = request.POST.get('text', '').strip()
        parent_id = request.POST.get('parent_id', '').strip()

        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, id=parent_id, solution=solution)

        if text:
            Comment.objects.create(
                user=request.user,
                solution=solution,
                text=text,
                parent=parent
            )
    
    return redirect(solution_list, problem_id=solution.problem_id)
