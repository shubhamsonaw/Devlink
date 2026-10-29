from django.db import models
from django.contrib.auth.models import User


# Create your models here.
# class Problem(models.Model):

#     DIFFICULTY_CHOICES = [
#         ('easy', 'Easy'),
#         ('medium', 'Medium'),
#         ('hard', 'Hard'),
#     ]

#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problems')

#     title = models.CharField(max_length=255)
#     description = models.TextField()

#     difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.title


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Problem(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField(max_length=255)
    description = models.TextField()

    difficulty = models.CharField(
        max_length=10,
        choices=[
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard')
        ],
        default='easy'
    )

    tags = models.ManyToManyField(Tag, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
