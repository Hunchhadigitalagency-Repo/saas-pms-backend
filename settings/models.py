from django.db import models
from customer.models import Client


class SlackToken(models.Model):
    """
    Model to store Slack integration tokens and team information
    """
    slack_token = models.CharField(max_length=255)
    team_id = models.CharField(max_length=255)
    team_name = models.CharField(max_length=255, null=True, blank=True)
    is_connected = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Slack Token"
        verbose_name_plural = "Slack Tokens"

    def __str__(self):
        return f"Slack Token for {self.client.name} ({self.team_id})"
