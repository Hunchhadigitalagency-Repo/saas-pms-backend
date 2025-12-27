from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from project.models import Project, ProjectMembers, ProjectActivityLog, ProjectSlackChannel

# Register your models here.

class ProjectMembersInline(admin.TabularInline):
    model = ProjectMembers
    extra = 1

@admin.register(Project)
class ProjectAdmin(SummernoteModelAdmin):
    list_display = ('name', 'priority', 'status', 'due_date', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('priority', 'status')
    inlines = [ProjectMembersInline]
    summernote_fields = ('description',)

@admin.register(ProjectActivityLog)
class ProjectActivityLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'created_at')
    search_fields = ('project__name',)
    list_filter = ('created_at',)

@admin.register(ProjectSlackChannel)
class ProjectSlackChannelAdmin(admin.ModelAdmin):
    list_display = ('project', 'channel_name', 'channel_id', 'is_private', 'created_at', 'updated_at')
    search_fields = ('project__name', 'channel_name', 'channel_id')
    list_filter = ('is_private', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
