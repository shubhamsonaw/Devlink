from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponseNotAllowed

from .models import Problem,Tag

# Create your views here.



def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    accepted_solution = problem.solutions.filter(is_accepted=True).select_related('user').first()
    accepted_project = None
    if accepted_solution:
        from opportunities.models import Project
        accepted_project = Project.objects.filter(source_solution=accepted_solution).first()

    return render(request, 'problem_detail.html', {
        'problem': problem,
        'accepted_solution': accepted_solution,
        'accepted_project': accepted_project,
    })


@login_required
def set_problem_status(request, problem_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    problem = get_object_or_404(Problem, id=problem_id)
    if problem.user_id != request.user.id:
        messages.error(request, "Only the problem owner can change its status.")
        return redirect('problem_detail', problem_id=problem.id)

    new_status = request.POST.get('status', '')
    valid_statuses = {value for value, _ in Problem.STATUS_CHOICES}
    if new_status not in valid_statuses:
        messages.error(request, "Choose a valid problem status.")
        return redirect('problem_detail', problem_id=problem.id)
    if new_status == 'resolved':
        accepted_solution = problem.solutions.filter(is_accepted=True).first()
        if not accepted_solution:
            messages.error(request, "Accept a solution before resolving this problem.")
            return redirect('problem_detail', problem_id=problem.id)
        from opportunities.models import Project
        if Project.objects.filter(source_solution=accepted_solution, status='active').exists():
            messages.error(request, "Complete the active collaboration project before resolving this problem.")
            return redirect('problem_detail', problem_id=problem.id)

    problem.status = new_status
    problem.save(update_fields=['status'])
    message = "Problem marked resolved." if new_status == 'resolved' else "Problem reopened."
    messages.success(request, message)
    return redirect('problem_detail', problem_id=problem.id)
    
    


def problem_list(request):
    query = request.GET.get('q')
    tag = request.GET.get('tag')

    problems = Problem.objects.all().order_by('-created_at')

    if query:
        problems = problems.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )

    if tag:
        problems = problems.filter(tags__name__iexact=tag)

    return render(request, 'problem_list.html', {
        'problems': problems,
        'query': query,
        'selected_tag': tag
    })

# @login_required
# def create_problem(request):
#     if request.method == 'POST':
#         title = request.POST.get('title')
#         description = request.POST.get('description')
#         difficulty = request.POST.get('difficulty')

#         Problem.objects.create(
#             user=request.user,
#             title=title,
#             description=description,
#             difficulty=difficulty
#         )

        
        
#         messages.success(request, "Problem created successfully")
#         return redirect('problem_list')

#     return render(request, 'problem_create.html')



@login_required
def create_problem(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        difficulty = request.POST.get('difficulty', '').strip()
        tags_input = request.POST.get('tags', '')
        tag_names = list(dict.fromkeys(
            name.strip().lower() for name in tags_input.split(',') if name.strip()
        ))

        if not title or not description:
            messages.error(request, "Please provide a title and description.")
            return redirect('create_problem')

        if difficulty not in {choice[0] for choice in Problem._meta.get_field('difficulty').choices}:
            messages.error(request, "Please select a valid difficulty.")
            return redirect('create_problem')

        if len(tag_names) > 5:
            messages.error(request, "You can only add up to 5 tags.")
            return redirect('create_problem')
        if any(len(name) > 50 for name in tag_names):
            messages.error(request, "Each tag must be 50 characters or fewer.")
            return redirect('create_problem')

        with transaction.atomic():
            problem = Problem.objects.create(
                user=request.user,
                title=title,
                description=description,
                difficulty=difficulty
            )
            for name in tag_names:
                tag, _ = Tag.objects.get_or_create(name=name)
                problem.tags.add(tag)
                
        messages.success(request, "Problem created successfully")
        return redirect('problem_list')

    return render(request, 'problem_create.html')
