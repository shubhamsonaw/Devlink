from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db import transaction
from django.http import HttpResponseNotAllowed
from django.utils import timezone

from .models import (
    Opportunity, Invitation, Application, Connection, Message, Project, ProjectTask, ProjectUpdate,
)


def ensure_connection(first_user, second_user):
    connection_exists = Connection.objects.filter(
        Q(user1=first_user, user2=second_user) |
        Q(user1=second_user, user2=first_user)
    ).exists()
    if not connection_exists:
        Connection.objects.create(user1=first_user, user2=second_user)

# Create your views here.

def opportunity_list(request):
    opportunities = Opportunity.objects.filter(is_active=True).order_by('-created_at')

    return render(request, 'opportunity_list.html', {
        'opportunities': opportunities
    })
    
    
def opportunity_detail(request, id):
    opportunity = get_object_or_404(Opportunity, id=id)

    user_application = None

    # ✅ Only check if user is logged in
    if request.user.is_authenticated:
        user_application = Application.objects.filter(
            user=request.user,
            opportunity=opportunity
        ).order_by('-created_at').first()  # ⭐ only latest

    context = {
        'opportunity': opportunity,
        'user_application': user_application
    }

    return render(request, 'opportunity_detail.html', context)
    
@login_required
def create_opportunity(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        skills = request.POST.get('required_skills', '').strip()

        if not title or not description or not skills:
            messages.error(request, "Title, description, and required skills are all required.")
            return render(request, 'opportunity_create.html', status=400)

        Opportunity.objects.create(
            user=request.user,
            title=title,
            description=description,
            required_skills=skills
        )
        

        messages.success(request, "Opportunity created successfully")
        return redirect('opportunity_list')

    return render(request, 'opportunity_create.html')


@login_required
def close_opportunity(request, opportunity_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    opportunity = get_object_or_404(Opportunity, id=opportunity_id, user=request.user)
    if opportunity.is_active:
        opportunity.is_active = False
        opportunity.save(update_fields=['is_active'])
        messages.success(request, "Opportunity closed. New applications are now disabled.")
    return redirect('opportunity_detail', id=opportunity.id)

# @login_required
# def send_invitation(request, opportunity_id):
#     opportunity = get_object_or_404(Opportunity, id=opportunity_id)

#     if request.method == "POST":
#         username = request.POST.get("username")

#         try:
#             receiver = User.objects.get(username=username)
#         except User.DoesNotExist:
#             messages.error(request, "User not found")
#             return redirect('opportunity_detail', pk=opportunity_id)

#         if receiver == request.user:
#             messages.error(request, "You cannot invite yourself")
#             return redirect('opportunity_detail', pk=opportunity_id)

#         if Invitation.objects.filter(
#             sender=request.user,
#             receiver=receiver,
#             opportunity=opportunity
#         ).exists():
#             messages.warning(request, "Already invited")
#             return redirect('opportunity_detail', pk=opportunity_id)

#         Invitation.objects.create(
#             sender=request.user,
#             receiver=receiver,
#             opportunity=opportunity
#         )

#         messages.success(request, "Invitation sent")
#         return redirect('opportunity_detail', pk=opportunity_id)

#     return redirect('opportunity_detail', pk=opportunity_id)

@login_required
def send_invitation(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        message = request.POST.get("message", "").strip()

        receiver = User.objects.filter(username__iexact=username).first()

        if not receiver:
            messages.error(request, "User not found")
            return redirect("invitation_list")

        if receiver == request.user:
            messages.error(request, "You cannot invite yourself")
            return redirect("invitation_list")

        if Connection.objects.filter(
            Q(user1=request.user, user2=receiver) |
            Q(user1=receiver, user2=request.user)
        ).exists():
            messages.info(request, "You are already connected to this developer")
            return redirect("invitation_list")

        # if Invitation.objects.filter(sender=request.user, receiver=receiver).exists():
        #     messages.warning(request, "Already invited")
        #     return redirect("invitation_list")

        if Invitation.objects.filter(sender=request.user, receiver=receiver, status="pending").exists():
            messages.warning(request, "You already have a pending invitation to this developer")
            return redirect("invitation_list")

        Invitation.objects.create(sender=request.user, receiver=receiver, message=message)

        messages.success(request, "Invitation sent")

    return redirect("invitation_list")


@login_required
def invite_solution_collaborator(request, solution_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    from solutions.models import Solution

    solution = get_object_or_404(Solution, id=solution_id, is_accepted=True)
    problem = solution.problem
    if problem.user_id != request.user.id:
        messages.error(request, "Only the problem owner can invite this solver.")
        return redirect("solution_list", problem_id=problem.id)
    if solution.user_id == request.user.id:
        messages.error(request, "You cannot invite yourself.")
        return redirect("solution_list", problem_id=problem.id)
    if Connection.objects.filter(
        Q(user1=request.user, user2=solution.user) |
        Q(user1=solution.user, user2=request.user)
    ).exists():
        messages.info(request, "You are already connected to this developer.")
        return redirect("solution_list", problem_id=problem.id)
    if Invitation.objects.filter(
        sender=request.user, receiver=solution.user, solution=solution, status="pending"
    ).exists():
        messages.warning(request, "A collaboration invite for this solution is already pending.")
        return redirect("solution_list", problem_id=problem.id)

    Invitation.objects.create(
        sender=request.user,
        receiver=solution.user,
        solution=solution,
        message=request.POST.get("message", "").strip() or f"Let's collaborate on: {problem.title}",
    )
    messages.success(request, f"Collaboration invite sent to {solution.user.username}.")
    return redirect("solution_list", problem_id=problem.id)

@login_required
def invitation_list(request):
    invitations = Invitation.objects.filter(receiver=request.user).order_by('-created_at')

    # For invite panel
    users = User.objects.exclude(id=request.user.id)
    opportunities = Opportunity.objects.filter(user=request.user)

    context = {
        "invitations": invitations,
        "users": users,
        "opportunities": opportunities,
    }

    return render(request, "invitation_list.html", context)
    
    
@login_required
def accept_application(request, app_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(['POST'])
    application = get_object_or_404(Application, id=app_id)

    # Only owner can accept
    if application.opportunity.user != request.user:
        messages.error(request, "Not allowed")
        return redirect('application_list')

    with transaction.atomic():
        application.status = 'accepted'
        application.save(update_fields=['status'])
        ensure_connection(application.opportunity.user, application.user)
        project, _ = Project.objects.get_or_create(
            source_application=application,
            defaults={
                'title': application.opportunity.title,
                'description': application.opportunity.description,
                'owner': application.opportunity.user,
            },
        )
        project.members.add(application.opportunity.user, application.user)

    messages.success(request, "Application accepted")
    return redirect('application_list')


@login_required
def reject_application(request, app_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(['POST'])
    application = get_object_or_404(Application, id=app_id)

    if application.opportunity.user != request.user:
        messages.error(request, "Not allowed")
        return redirect('application_list')

    application.status = 'rejected'
    application.save()

    messages.warning(request, "Application rejected")
    return redirect('application_list')



@login_required
def apply_opportunity(request, pk):
    opportunity = get_object_or_404(Opportunity, id=pk)

    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        github = request.POST.get("github", "").strip()
        resume = request.POST.get("resume", "").strip()

        if opportunity.user_id == request.user.id or not opportunity.is_active:
            messages.error(request, "This opportunity is not accepting applications")
            return redirect("opportunity_detail", id=pk)

        # ❌ validation fix
        if not message:
            messages.error(request, "Message required")
            return redirect("opportunity_detail", id=pk)  # ✅ FIXED

        # ❌ optional: prevent duplicate applications (recommended)
        if Application.objects.filter(user=request.user, opportunity=opportunity).exists():
            messages.warning(request, "You already applied")
            return redirect("opportunity_detail", id=pk)

        Application.objects.create(
            user=request.user,
            opportunity=opportunity,
            message=message,
            github=github,
            resume=resume
        )

        messages.success(request, "Applied successfully!")
        return redirect("opportunity_detail", id=pk)

    return redirect("opportunity_detail", id=pk)


@login_required
def view_applications(request, pk):
    opportunity = get_object_or_404(Opportunity, id=pk, user=request.user)
    applications = Application.objects.filter(opportunity=opportunity)

    return render(request, "application_list.html", {
        "applications": applications,
        "opportunity": opportunity
    })



@login_required
def application_list(request):
    applications = Application.objects.filter(
        opportunity__user=request.user
    ).select_related('user', 'opportunity').order_by('-created_at')

    return render(request, 'application_list.html', {
        'applications': applications
    })
    
    
    
@login_required
def applications(request):
    applications = Application.objects.filter(
        user=request.user
    ).select_related('opportunity').order_by('-created_at')

    return render(request, 'applications.html', {
        'applications': applications
    })
    
    
    
@login_required
def accept_invitation(request, pk):
    invitation = get_object_or_404(
        Invitation,
        id=pk,
        receiver=request.user
    )

    if request.method == "POST" and invitation.status == "pending":
        with transaction.atomic():
            invitation.status = "accepted"
            invitation.save(update_fields=['status'])
            ensure_connection(invitation.sender, invitation.receiver)
            if invitation.solution_id:
                solution = invitation.solution
                problem = solution.problem
                project, _ = Project.objects.get_or_create(
                    source_solution=solution,
                    defaults={
                        'title': problem.title,
                        'description': problem.description,
                        'owner': problem.user,
                    },
                )
                project.members.add(problem.user, solution.user)
                if problem.status == 'resolved':
                    problem.status = 'open'
                    problem.save(update_fields=['status'])
        messages.success(request, "Invitation accepted. You're now connected and the project is ready.")

    return redirect("invitation_list")


@login_required
def reject_invitation(request, pk):
    invitation = get_object_or_404(
        Invitation,
        id=pk,
        receiver=request.user
    )

    if request.method == "POST" and invitation.status == "pending":
        invitation.status = "rejected"
        invitation.save()
        messages.warning(request, "Invitation rejected")

    return redirect("invitation_list")
    
    
@login_required
def sent_invitations(request):
    invites = Invitation.objects.filter(sender=request.user).order_by('-created_at')

    return render(request, "sent_invitations.html", {
        "invites": invites
    })
    


# @login_required
# def chat(request,username):
#     other_user = get_object_or_404(User, username=username)

#     # ✅ only allow if connected
#     is_connected = Connection.objects.filter(
#         user1=request.user, user2=other_user
#     ).exists() or Connection.objects.filter(
#         user1=other_user, user2=request.user
#     ).exists()

#     if not is_connected:
#         messages.error(request, "You are not connected")
#         return redirect("opportunity_list")

#     messages_qs = Message.objects.filter(
#         sender__in=[request.user, other_user],
#         receiver__in=[request.user, other_user]
#     ).order_by("timestamp")
    
#     messages_qs.filter(
#         sender=other_user,
#         receiver=request.user,
#         is_read=False
#     ).update(is_read=True)

#     if request.method == "POST":
#         content = request.POST.get("content")
#         if content:
#             Message.objects.create(
#                 sender=request.user,
#                 receiver=other_user,
#                 content=content
#             )
#         return redirect("chat", username=other_user.username)

#     return render(request, "chat.html", {
#         "messages": messages_qs,
#         "other_user": other_user
#     })


@login_required
def chat(request, username):

    other_user = get_object_or_404(User, username=username)

    is_connected = Connection.objects.filter(
        user1=request.user,
        user2=other_user
    ).exists() or Connection.objects.filter(
        user1=other_user,
        user2=request.user
    ).exists()

    if not is_connected:
        messages.error(request, "You are not connected")
        return redirect("opportunity_list")

    chat_messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    ).order_by("timestamp")

    # unread → read
    chat_messages.filter(
        sender=other_user,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    if request.method == "POST":

        content = request.POST.get("content")

        if content:

            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=content,
            )

            return redirect("chat", username=other_user.username)

    return render(request, "chat.html", {
        "chat_messages": chat_messages,
        "other_user": other_user
    })
    

# @login_required
# def chat_view(request, username):
#     receiver = get_object_or_404(User, username=username)

#     messages = Message.objects.filter(
#         sender__in=[request.user, receiver],
#         receiver__in=[request.user, receiver]
#     ).order_by("timestamp")

#     return render(request, "chat.html", {
#         "receiver": receiver,
#         "messages": messages
#     })
    
    


@login_required
def messages_list(request):

    messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).order_by('-timestamp')

    conversations = []
    users_seen = set()

    for msg in messages:

        other_user = msg.receiver if msg.sender == request.user else msg.sender

        if other_user.id not in users_seen:

            unread_count = Message.objects.filter(
                sender=other_user,
                receiver=request.user,
                is_read=False
            ).count()

            conversations.append({
                "user": other_user,
                "last_message": msg,
                "unread_count": unread_count,
            })

            users_seen.add(other_user.id)

    context = {
        "conversations": conversations
    }

    return render(request, "messages_list.html", context)


def project_list(request):
    projects = Project.objects.all().select_related('owner').annotate(
        update_count=Count('updates')
    ).order_by('-created_at')
    return render(request, 'project_list.html', {'projects': projects})


def project_detail(request, project_id):
    project = get_object_or_404(Project.objects.select_related('owner'), id=project_id)
    is_member = request.user.is_authenticated and (
        project.owner_id == request.user.id or project.members.filter(id=request.user.id).exists()
    )
    if request.method == 'POST':
        if not is_member:
            return HttpResponseNotAllowed(['GET'])
        if project.status == 'completed':
            messages.error(request, "Reopen this project before posting updates.")
            return redirect('project_detail', project_id=project.id)
        content = request.POST.get('content', '').strip()
        if not content:
            messages.error(request, "Write an update before posting.")
        elif len(content) > 5000:
            messages.error(request, "Updates must be 5,000 characters or fewer.")
        else:
            ProjectUpdate.objects.create(project=project, author=request.user, content=content)
            messages.success(request, "Project update posted.")
            return redirect('project_detail', project_id=project.id)

    tasks = list(project.tasks.select_related('created_by', 'assigned_to'))
    task_columns = [
        {
            'value': status,
            'label': label,
            'tasks': [task for task in tasks if task.status == status],
        }
        for status, label in ProjectTask.STATUS_CHOICES
    ]
    can_complete_project = not any(task.status != 'done' for task in tasks)

    return render(request, 'project_detail.html', {
        'project': project,
        'updates': project.updates.select_related('author'),
        'members': project.members.all(),
        'is_member': is_member,
        'task_columns': task_columns,
        'task_status_choices': ProjectTask.STATUS_CHOICES,
        'can_complete_project': can_complete_project,
    })


@login_required
def create_project_task(request, project_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    project = get_object_or_404(Project, id=project_id)
    if not project.members.filter(id=request.user.id).exists() and project.owner_id != request.user.id:
        messages.error(request, "Only project members can create tasks.")
        return redirect('project_detail', project_id=project.id)
    if project.status == 'completed':
        messages.error(request, "Reopen this project before adding tasks.")
        return redirect('project_detail', project_id=project.id)

    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    assignee_id = request.POST.get('assigned_to', '').strip()
    if not title:
        messages.error(request, "A task title is required.")
        return redirect('project_detail', project_id=project.id)
    if len(title) > 255:
        messages.error(request, "Task titles must be 255 characters or fewer.")
        return redirect('project_detail', project_id=project.id)

    assignee = None
    if assignee_id:
        assignee = get_object_or_404(project.members, id=assignee_id)

    ProjectTask.objects.create(
        project=project,
        title=title,
        description=description,
        created_by=request.user,
        assigned_to=assignee,
    )
    messages.success(request, "Task added to the project.")
    return redirect('project_detail', project_id=project.id)


@login_required
def update_project_task_status(request, task_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    task = get_object_or_404(ProjectTask.objects.select_related('project'), id=task_id)
    project = task.project
    if not project.members.filter(id=request.user.id).exists() and project.owner_id != request.user.id:
        messages.error(request, "Only project members can update tasks.")
        return redirect('project_detail', project_id=project.id)
    if project.status == 'completed':
        messages.error(request, "Reopen this project before changing task status.")
        return redirect('project_detail', project_id=project.id)

    new_status = request.POST.get('status', '')
    valid_statuses = {value for value, _ in ProjectTask.STATUS_CHOICES}
    if new_status not in valid_statuses:
        messages.error(request, "Choose a valid task status.")
        return redirect('project_detail', project_id=project.id)

    task.status = new_status
    task.save(update_fields=['status', 'updated_at'])
    messages.success(request, "Task status updated.")
    return redirect('project_detail', project_id=project.id)


@login_required
def set_project_status(request, project_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    new_status = request.POST.get('status', '')
    valid_statuses = {value for value, _ in Project.STATUS_CHOICES}
    if new_status not in valid_statuses:
        messages.error(request, "Choose a valid project status.")
        return redirect('project_detail', project_id=project.id)

    if new_status == 'completed' and project.tasks.exclude(status='done').exists():
        messages.error(request, "Mark every task done before completing the project.")
        return redirect('project_detail', project_id=project.id)

    with transaction.atomic():
        project.status = new_status
        project.completed_at = timezone.now() if new_status == 'completed' else None
        project.save(update_fields=['status', 'completed_at'])
        if new_status == 'active' and project.source_solution_id:
            problem = project.source_solution.problem
            if problem.status == 'resolved':
                problem.status = 'open'
                problem.save(update_fields=['status'])
    if new_status == 'completed':
        messages.success(request, "Project completed. Great work!")
    else:
        messages.success(request, "Project reopened.")
    return redirect('project_detail', project_id=project.id)
