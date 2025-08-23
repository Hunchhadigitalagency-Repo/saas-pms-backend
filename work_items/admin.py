from django.contrib import admin

from .models import WorkItems

# Register your models here.

@admin.register(WorkItems)
class WorkItemsAdmin(admin.ModelAdmin):
    list_display = ('title', 'due_date', 'status', 'priority', 'project')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('title', 'description')