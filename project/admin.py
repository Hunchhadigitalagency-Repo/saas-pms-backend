from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from project.models import Project, ProjectMembers, ProjectActivityLog

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
