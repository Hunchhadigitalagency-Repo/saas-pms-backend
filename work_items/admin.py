from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from .models import WorkItems

# Register your models here.

@admin.register(WorkItems)
class WorkItemsAdmin(SummernoteModelAdmin):
    list_display = ('title', 'due_date', 'status', 'priority', 'project')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('title', 'description')
    summernote_fields = ('description',)