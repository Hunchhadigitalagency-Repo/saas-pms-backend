from pms.jwt_auth import CookieJWTAuthentication
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from settings_app.models import SlackToken
from settings_app.adapters.serializers import SlackTokenSerializer, SlackTokenDetailSerializer
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
    authentication_classes = [CookieJWTAuthentication]
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
            verification_result = self._verify_slack_token_with_slack(slack_token)
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

    @action(detail=False, methods=['post'])
    def verify_token(self, request):
        """
        Verify Slack token and return team information
        Expects: {'slack_token': '...'}
        """
        slack_token = request.data.get('slack_token')

        if not slack_token:
            return Response(
                {'error': 'slack_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify token with Slack API
            verification_result = self._verify_slack_token_with_slack(slack_token)
            if not verification_result['valid']:
                return Response(
                    {'error': verification_result.get('error', 'Invalid Slack token')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                'ok': True,
                'team_id': verification_result.get('team_id'),
                'team': verification_result.get('team_name')
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error verifying Slack token: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _verify_slack_token_with_slack(token):
        """
        Verify Slack token with Slack API and get team info
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
            
            return {
                'valid': True,
                'team_id': data.get('team_id'),
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
                'chat:write': 'Send messages as your Slack app',
                'groups:read': 'View basic information about private channels that your app has been added to'
            },
            'note': 'Private channels will only appear if your Slack app has been invited to them. To access private channels, invite your app using /invite @your-app-name in the channel.'
        })

    @action(detail=False, methods=['get'])
    def get_channels(self, request):
        """
        Get all Slack channels (public and private) that the bot has access to
        """
        try:
            slack_token_obj = SlackToken.objects.first()
            if not slack_token_obj or not slack_token_obj.is_connected:
                return Response(
                    {'error': 'Slack is not connected'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            channels = self._fetch_slack_channels(slack_token_obj.slack_token)
            if channels is None:
                return Response(
                    {'error': 'Failed to fetch channels from Slack'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response({
                'channels': channels
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching Slack channels: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _fetch_slack_channels(token):
        """
        Fetch all channels (public and private) from Slack API
        Note: For private channels, the bot must be a member of the channel
        """
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            all_channels = []
            cursor = None
            
            # Fetch channels with pagination support
            while True:
                params = {
                    'types': 'public_channel,private_channel',
                    'exclude_archived': True,
                    'limit': 200
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                response = requests.get(
                    'https://slack.com/api/conversations.list',
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                if response.status_code != 200:
                    logger.error(f"Slack API error: {response.status_code}")
                    return None
                
                data = response.json()
                if not data.get('ok'):
                    logger.error(f"Slack API error: {data.get('error')}")
                    return None
                
                channels = data.get('channels', [])
                logger.info(f"Fetched {len(channels)} channels from Slack")
                
                for channel in channels:
                    channel_info = {
                        'id': channel.get('id'),
                        'name': channel.get('name'),
                        'is_private': channel.get('is_private', False),
                        'is_channel': channel.get('is_channel', True),
                        'num_members': channel.get('num_members', 0)
                    }
                    all_channels.append(channel_info)
                    
                    # Log private channels for debugging
                    if channel.get('is_private'):
                        logger.info(f"Found private channel: {channel.get('name')}")
                
                # Check for pagination
                cursor = data.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
            
            logger.info(f"Total channels fetched: {len(all_channels)} (Public: {sum(1 for c in all_channels if not c['is_private'])}, Private: {sum(1 for c in all_channels if c['is_private'])})")
            return all_channels
        except Exception as e:
            logger.error(f"Error fetching Slack channels: {str(e)}")
            return None
