from django.contrib import admin
from .models import Opportunity, Invitation, Application, Project, ProjectTask, ProjectUpdate

# Register your models here.

# admin.site.register(Opportunity)




@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("sender__username", "receiver__username")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("user", "opportunity", "status", "created_at")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "created_at")
    search_fields = ("title", "owner__username")


@admin.register(ProjectUpdate)
class ProjectUpdateAdmin(admin.ModelAdmin):
    list_display = ("project", "author", "created_at")
    search_fields = ("project__title", "author__username", "content")


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "assigned_to", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "project__title", "assigned_to__username")
