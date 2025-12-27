from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from settings.models import SlackToken
from settings.adapters.serializers import SlackTokenSerializer, SlackTokenDetailSerializer
import requests
import logging

logger = logging.getLogger(__name__)

SLACK_OAUTH_SCOPES = [
    'channels:read',
    'chat:write',
    'groups:read',
]


class SlackTokenViewSet(viewsets.ModelViewSet):
    serializer_class = SlackTokenSerializer
    permission_classes = [IsAuthenticated]
    queryset = SlackToken.objects.all()

    def get_queryset(self):
        """
        Return all slack tokens
        """
        return SlackToken.objects.all()

    @action(detail=False, methods=['get'])
    def check_connection(self, request):
        """
        Check if Slack is connected
        """
        try:
            slack_token = SlackToken.objects.first()
            if slack_token and slack_token.is_connected and slack_token.slack_token:
                serializer = SlackTokenDetailSerializer(slack_token)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(
                {'is_connected': False},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error checking Slack connection: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def add_token(self, request):
        """
        Add Slack token and team ID to the database
        Expects: {'slack_token': '...', 'team_id': '...', 'team_name': '...'}
        """
        slack_token = request.data.get('slack_token')
        team_id = request.data.get('team_id')
        team_name = request.data.get('team_name')

        if not slack_token or not team_id:
            return Response(
                {'error': 'slack_token and team_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify token with Slack API
            verification_result = self._verify_slack_token(slack_token, team_id)
            if not verification_result['valid']:
                return Response(
                    {'error': verification_result.get('error', 'Invalid Slack token')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create or update SlackToken (only one instance should exist)
            slack_token_obj, created = SlackToken.objects.update_or_create(
                team_id=team_id,
                defaults={
                    'slack_token': slack_token,
                    'team_name': team_name or verification_result.get('team_name'),
                    'is_connected': True
                }
            )

            serializer = SlackTokenDetailSerializer(slack_token_obj)
            return Response(
                {'message': 'Slack token added successfully', **serializer.data},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error adding Slack token: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def disconnect(self, request):
        """
        Disconnect/remove Slack integration
        """
        try:
            slack_token = SlackToken.objects.first()
            if slack_token:
                slack_token.delete()
                return Response(
                    {'message': 'Slack integration removed successfully'},
                    status=status.HTTP_200_OK
                )

            return Response(
                {'error': 'No Slack integration found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error disconnecting Slack: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _verify_slack_token(token, team_id):
        """
        Verify Slack token with Slack API
        """
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Check token validity and get team info
            response = requests.post(
                'https://slack.com/api/auth.test',
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return {'valid': False, 'error': 'Failed to verify token with Slack'}
            
            data = response.json()
            if not data.get('ok'):
                return {'valid': False, 'error': data.get('error', 'Token verification failed')}
            
            if data.get('team_id') != team_id:
                return {'valid': False, 'error': 'Team ID does not match'}
            
            return {
                'valid': True,
                'team_name': data.get('team')
            }
        except Exception as e:
            logger.error(f"Error verifying Slack token: {str(e)}")
            return {'valid': False, 'error': str(e)}

    @action(detail=False, methods=['get'])
    def oauth_scopes(self, request):
        """
        Get required OAuth scopes for Slack integration
        """
        return Response({
            'scopes': SLACK_OAUTH_SCOPES,
            'scope_descriptions': {
                'channels:read': 'View basic information about public channels in a workspace',
                'chat:write': 'Send messages as @collabrix-integration',
                'groups:read': 'View basic information about private channels that "collabrix-integration" has been added to'
            }
        })
