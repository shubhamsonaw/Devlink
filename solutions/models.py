from django.db import models
from django.contrib.auth.models import User
from problems.models import Problem
# Create your models here.


class Solution(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solutions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='solutions')

    explanation = models.TextField()
    code = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    is_accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.problem.title}"
    
class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE, related_name='votes')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'solution')

    def __str__(self):
        return f"{self.user.username} voted {self.solution.id}"
    
    
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE, related_name='comments')

    text = models.TextField()

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.text[:20]}"
    