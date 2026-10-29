from django.contrib import admin
from .models import Solution,Vote,Comment


# Register your models here.

admin.site.register(Solution)
admin.site.register(Vote)
admin.site.register(Comment)