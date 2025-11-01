from work_items.adapters.serializers.work_items_serializer import WorkItemsSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from datetime import date
from work_items.models import WorkItems, Status

class DueTasksView(APIView):
    """
    API view to return all work items that are due until today (not completed)
    """
    def get(self, request):
        today = date.today()
        
        due_tasks = WorkItems.objects.filter(
            ~Q(status=Status.COMPLETED),
            due_date__lte=today
        ).order_by('due_date')

        serializer = WorkItemsSerializer(due_tasks, many=True)
        
        return Response({"due_tasks": serializer.data})
