from .models import Profile


def nav_profile_image(request):
    if not request.user.is_authenticated:
        return {"nav_profile_image_url": ""}

    profile, _ = Profile.objects.get_or_create(user=request.user)
    image_url = ""
    try:
        image_url = profile.profile_image.url if profile.profile_image else ""
    except Exception:
        image_url = ""

    return {"nav_profile_image_url": image_url}
