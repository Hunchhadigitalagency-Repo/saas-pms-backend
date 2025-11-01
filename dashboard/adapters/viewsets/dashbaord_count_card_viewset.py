from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from decimal import Decimal


class DashboardViewset(viewsets.ViewSet):

    @action(detail=False, methods=['get'])
    def dashboard_data(self, request):
        """
        Get comprehensive dashboard data with comparisons and trends
        """
        today = timezone.now().date()
        
        # Calculate date ranges
        current_month_start = today.replace(day=1)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = current_month_start - timedelta(days=1)
        
        current_week_start = today - timedelta(days=today.weekday())
        last_week_start = current_week_start - timedelta(days=7)
        last_week_end = current_week_start - timedelta(days=1)
        
        # 1. Total Projects
        total_projects = self._get_total_projects(
            today, current_month_start, last_month_start, last_month_end
        )
        
        # 2. Work Items Completed
        work_items_completed = self._get_completed_work_items(
            today, current_week_start, last_week_start, last_week_end
        )
        
        # 3. Overdue Work Items
        overdue_work_items = self._get_overdue_work_items(
            today, current_week_start, last_week_start, last_week_end
        )
        
        # 4. Work Item Velocity
        velocity = self._get_work_item_velocity(
            today, current_week_start, last_week_start, last_week_end
        )
        
        return Response({
            'total_projects': total_projects,
            'work_items_completed': work_items_completed,
            'overdue_work_items': overdue_work_items,
            'velocity': velocity,
        })

    def _get_total_projects(self, today, current_month_start, last_month_start, last_month_end):
        """
        Get total projects with comparison vs last month
        """
        from project.models import Project
        
        # Current month projects
        current_count = Project.objects.filter(
            created_at__date__gte=current_month_start,
            created_at__date__lte=today
        ).count()
        
        # Last month projects (full month)
        last_month_count = Project.objects.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        ).count()
        
        # Calculate trend
        trend_data = self._calculate_trend(current_count, last_month_count)
        
        return {
            'count': current_count,
            'comparison': {
                'previous_period': last_month_count,
                'difference': current_count - last_month_count,
                'percentage': trend_data['percentage'],
                'trend': trend_data['trend']
            }
        }

    def _get_completed_work_items(self, today, current_week_start, last_week_start, last_week_end):
        """
        Get completed work items with comparison vs last week
        """
        from work_items.models import WorkItems, Status
        
        # Current week completed
        current_count = WorkItems.objects.filter(
            status=Status.COMPLETED,
            updated_at__date__gte=current_week_start,
            updated_at__date__lte=today
        ).count()
        
        # Last week completed
        last_week_count = WorkItems.objects.filter(
            status=Status.COMPLETED,
            updated_at__date__gte=last_week_start,
            updated_at__date__lte=last_week_end
        ).count()
        
        # Calculate trend
        trend_data = self._calculate_trend(current_count, last_week_count)
        
        return {
            'count': current_count,
            'comparison': {
                'previous_period': last_week_count,
                'difference': current_count - last_week_count,
                'percentage': trend_data['percentage'],
                'trend': trend_data['trend']
            }
        }

    def _get_overdue_work_items(self, today, current_week_start, last_week_start, last_week_end):
        """
        Get overdue work items with comparison vs last week
        """
        from work_items.models import WorkItems, Status
        
        # Current overdue (not completed and due date passed)
        current_count = WorkItems.objects.filter(
            ~Q(status=Status.COMPLETED),
            due_date__lt=today
        ).count()
        
        # Overdue at the start of this week
        last_week_count = WorkItems.objects.filter(
            ~Q(status=Status.COMPLETED),
            due_date__lt=current_week_start
        ).count()
        
        # Calculate trend (for overdue, declining is good, so we invert the logic)
        trend_data = self._calculate_trend(current_count, last_week_count, inverse=True)
        
        return {
            'count': current_count,
            'comparison': {
                'previous_period': last_week_count,
                'difference': current_count - last_week_count,
                'percentage': trend_data['percentage'],
                'trend': trend_data['trend']
            }
        }

    def _get_work_item_velocity(self, today, current_week_start, last_week_start, last_week_end):
        """
        Get average work items completed per day (velocity) with comparison vs last week
        """
        from work_items.models import WorkItems, Status
        
        # Current week
        current_week_days = (today - current_week_start).days + 1
        current_completed = WorkItems.objects.filter(
            status=Status.COMPLETED,
            updated_at__date__gte=current_week_start,
            updated_at__date__lte=today
        ).count()
        current_velocity = round(current_completed / current_week_days, 2) if current_week_days > 0 else 0
        
        # Last week
        last_week_days = 7
        last_week_completed = WorkItems.objects.filter(
            status=Status.COMPLETED,
            updated_at__date__gte=last_week_start,
            updated_at__date__lte=last_week_end
        ).count()
        last_week_velocity = round(last_week_completed / last_week_days, 2)
        
        # Calculate trend
        trend_data = self._calculate_trend(
            float(current_velocity), 
            float(last_week_velocity)
        )
        
        return {
            'velocity': current_velocity,
            'comparison': {
                'previous_period': last_week_velocity,
                'difference': round(current_velocity - last_week_velocity, 2),
                'percentage': trend_data['percentage'],
                'trend': trend_data['trend']
            }
        }

    def _calculate_trend(self, current, previous, inverse=False):
        """
        Calculate percentage change and trend direction
        
        Args:
            current: Current period value
            previous: Previous period value
            inverse: If True, declining values are considered positive (for overdue items)
        
        Returns:
            dict with percentage and trend (growing/declining/steady)
        """
        if previous == 0:
            if current == 0:
                percentage = 0
                trend = 'steady'
            else:
                percentage = 100
                trend = 'declining' if inverse else 'growing'
        else:
            percentage = round(((current - previous) / previous) * 100, 2)
            
            if percentage > 5:
                trend = 'declining' if inverse else 'growing'
            elif percentage < -5:
                trend = 'growing' if inverse else 'declining'
            else:
                trend = 'steady'
        
        return {
            'percentage': abs(percentage),
            'trend': trend
        }