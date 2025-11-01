from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from work_items.models import WorkItems
from django.db.models import Count, Q, Case, When, Value, CharField
from datetime import date


class WorkItemStatusDistribution(APIView):
    def get(self, request):
        today = date.today()

        # Include only work items whose project is NOT completed
        work_items = WorkItems.objects.filter(~Q(project__status='completed')).annotate(
            display_status=Case(
                When(Q(due_date__lt=today) & ~Q(status='completed'), then=Value('overdue')),
                default='status',
                output_field=CharField()
            )
        )

        # Group by computed display_status and count
        status_distribution = (
            work_items.values('display_status')
            .annotate(count=Count('display_status'))
            .order_by('display_status')
        )

        response_data = {
            "status_distribution": list(status_distribution)
        }

        return Response(response_data)


class WorkItemPriorityDistribution(APIView):
    def get(self, request):
        # Only include work items whose project is NOT completed
        work_items = WorkItems.objects.filter(~Q(project__status='completed'))

        # Group by priority
        priority_distribution = (
            work_items.values('priority')
            .annotate(count=Count('priority'))
            .order_by('priority')
        )

        response_data = {
            "priority_distribution": list(priority_distribution)
        }

        return Response(response_data)
