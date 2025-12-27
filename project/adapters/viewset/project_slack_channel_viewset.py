from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from pms.jwt_auth import CookieJWTAuthentication
from project.models import ProjectSlackChannel, Project
from project.adapters.serializers.project_slack_channel_serializer import (
    ProjectSlackChannelSerializer,
    ProjectSlackChannelDetailSerializer
)
import logging

logger = logging.getLogger(__name__)


class ProjectSlackChannelViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSlackChannelSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]
    queryset = ProjectSlackChannel.objects.all()

    def get_queryset(self):
        """
        Filter channels by project if project_id is provided
        """
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return ProjectSlackChannel.objects.filter(project_id=project_id)
        return ProjectSlackChannel.objects.all()

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return ProjectSlackChannelDetailSerializer
        return ProjectSlackChannelSerializer

    @action(detail=False, methods=['post'])
    def connect_channel(self, request):
        """
        Connect a Slack channel to a project
        Expects: {'project_id': 1, 'channel_id': 'C123...', 'channel_name': 'general', 'is_private': false}
        """
        project_id = request.data.get('project_id')
        channel_id = request.data.get('channel_id')
        channel_name = request.data.get('channel_name')
        is_private = request.data.get('is_private', False)

        if not project_id or not channel_id or not channel_name:
            return Response(
                {'error': 'project_id, channel_id, and channel_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify project exists
            project = Project.objects.get(id=project_id)

            # Create or update the channel connection
            channel_obj, created = ProjectSlackChannel.objects.update_or_create(
                project=project,
                channel_id=channel_id,
                defaults={
                    'channel_name': channel_name,
                    'is_private': is_private
                }
            )

            serializer = ProjectSlackChannelDetailSerializer(channel_obj)
            message = 'Channel connected successfully' if created else 'Channel updated successfully'
            
            return Response(
                {'message': message, **serializer.data},
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error connecting Slack channel: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def disconnect_channel(self, request):
        """
        Disconnect a Slack channel from a project
        Expects: {'project_id': 1, 'channel_id': 'C123...'}
        """
        project_id = request.data.get('project_id')
        channel_id = request.data.get('channel_id')

        if not project_id or not channel_id:
            return Response(
                {'error': 'project_id and channel_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            channel_obj = ProjectSlackChannel.objects.get(
                project_id=project_id,
                channel_id=channel_id
            )
            channel_obj.delete()
            
            return Response(
                {'message': 'Channel disconnected successfully'},
                status=status.HTTP_200_OK
            )
        except ProjectSlackChannel.DoesNotExist:
            return Response(
                {'error': 'Channel connection not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error disconnecting Slack channel: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def get_project_channels(self, request):
        """
        Get all Slack channels connected to a project
        Query param: project_id
        """
        project_id = request.query_params.get('project_id')
        
        if not project_id:
            return Response(
                {'error': 'project_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            channels = ProjectSlackChannel.objects.filter(project_id=project_id)
            serializer = ProjectSlackChannelDetailSerializer(channels, many=True)
            
            return Response({
                'channels': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching project channels: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
