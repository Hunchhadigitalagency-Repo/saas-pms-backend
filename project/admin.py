from django.contrib import admin

from project.models import Project, ProjectMembers

# Register your models here.

class ProjectMembersInline(admin.TabularInline):
    model = ProjectMembers
    extra = 1

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'status', 'due_date', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('priority', 'status')
    inlines = [ProjectMembersInline]
