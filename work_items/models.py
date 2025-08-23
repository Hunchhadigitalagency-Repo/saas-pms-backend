from django.db import models
from django.contrib.auth.models import User

class Status(models.TextChoices):
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'

class Priority(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'

# Create your models here.
class WorkItems(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    due_date = models.DateField()
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(max_length=50, choices=Priority.choices, default=Priority.LOW)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE, null=True, blank=True)
    assigned_to = models.ManyToManyField(User, related_name='assigned_work_items', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Work Items"
        ordering = ['-created_at']