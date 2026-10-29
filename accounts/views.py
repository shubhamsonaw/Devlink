from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.http import url_has_allowed_host_and_scheme
from solutions.models import Solution
from problems.models import Problem
from opportunities.models import Connection

from .models import Profile

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not username or not email or not password:
            messages.error(request, "Username, email, and password are required")
            return redirect('accounts:signup')
        
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already exists")
            return redirect('accounts:signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("accounts:signup")

        try:
            validate_password(password)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return redirect('accounts:signup')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        login(request, user)
        return redirect("accounts:profile", username=user.username)

    return render(request, "signup.html")




def login_view(request):
    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # 🔥 CHECK IF EMAIL
        user_obj = None
        if "@" in identifier:
            try:
                user_obj = User.objects.get(email__iexact=identifier)
                username = user_obj.username
            except User.DoesNotExist:
                username = None
        else:
            username = identifier

        user = authenticate(request, username=username, password=password)

        if user is not None:
            Profile.objects.get_or_create(user=user)
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('accounts:profile', username=user.username)
        else:
            messages.error(request, "Invalid username/email or password")
            return redirect('accounts:login')

    return render(request, "login.html")



def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("accounts:login")



def profile_view(request, username):
    user = get_object_or_404(User, username=username)

    # ✅ SAFE PROFILE (IMPORTANT FIX)
    profile = Profile.objects.get_or_create(user=user)[0]

    solutions = Solution.objects.filter(user=user)
    skill_dict = {}

    for sol in solutions:
        problem = sol.problem
        tags = problem.tags.all()

        for tag in tags:
            if tag.name in skill_dict:
                skill_dict[tag.name] += 1
            else:
                skill_dict[tag.name] = 1

    # sort skills by count (highest first)
    sorted_skills = sorted(skill_dict.items(), key=lambda x: x[1], reverse=True)
        
    problems = Problem.objects.filter(user=user)

    total_solutions = solutions.count()
    accepted_solutions = solutions.filter(is_accepted=True).count()
    total_votes = sum([sol.votes.count() for sol in solutions])
    
    is_connected = False

    if request.user.is_authenticated and request.user != user:
        is_connected = Connection.objects.filter(
            user1=request.user,
            user2=user
        ).exists() or Connection.objects.filter(
            user1=user,
            user2=request.user
        ).exists()

    context = {
        'profile_user': user,
        'profile': profile,
        'solutions': solutions,
        'problems': problems,
        'total_solutions': total_solutions,
        'accepted_solutions': accepted_solutions,
        'total_votes': total_votes,
        'top_skills': sorted_skills,
        'is_connected': is_connected,
    }
    
    return render(request, 'profile.html', context)

@login_required
def my_profile(request):
    return redirect('accounts:profile', username=request.user.username)



@login_required
def edit_profile(request):
    user = request.user
    profile = Profile.objects.get_or_create(user=user)[0]

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        bio = request.POST.get("bio")
        github = request.POST.get("github")
        linkedin = request.POST.get("linkedin")
        profile_image = request.FILES.get("profile_image")
        
        if User.objects.exclude(id=user.id).filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect('accounts:edit_profile')

        
        user.username = username
        user.email = email
        user.save()

        
        profile.bio = bio
        profile.github = github
        profile.linkedin = linkedin
        if profile_image:
            profile.profile_image = profile_image
        profile.save()

        return redirect('accounts:profile', username=user.username)

    context = {
        "user": user,
        "profile": profile
    }

    return render(request, "edit_profile.html", context)
    
