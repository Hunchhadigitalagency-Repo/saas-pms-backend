from django.db import models

# Create your models here.
# create project model with project name, priority with (high medium and low), status with (active, on hold, completed), due date and description created at and updated at as well 

class Project(models.Model):
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
    ]

    name = models.CharField(max_length=555)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='low')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    due_date = models.DateField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    meeting_link = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['-created_at']
        


class ProjectMembers(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('member', 'Members'),
        ('viewer', 'Viewer'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='member')

    class Meta:
        unique_together = ('project', 'user')

class ProjectActivityLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    activity = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.activity} - {self.project.name}"