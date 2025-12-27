from django.contrib import admin
from .models import SlackToken


@admin.register(SlackToken)
class SlackTokenAdmin(admin.ModelAdmin):
    list_display = ['team_name', 'team_id', 'is_connected', 'created_at', 'updated_at']
    list_filter = ['is_connected', 'created_at']
    search_fields = ['team_name', 'team_id']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Slack Information', {
            'fields': ('team_name', 'team_id', 'slack_token')
        }),
        ('Status', {
            'fields': ('is_connected',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
