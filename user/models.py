from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', default='default.jpg')
    google_id = models.CharField(max_length=555, blank=True, null=True)

    def __str__(self):
        return self.user.username