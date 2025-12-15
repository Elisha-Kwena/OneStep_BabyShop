from rest_framework import status,generics,permissions,viewsets,filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
import logging

from ..models import (
    CustomUser, 
    UserAddress, 
    NotificationPreferences, 
    LoyaltyPointsHistory, 
    UserActivityLog
)

from users.seriallizers.profile import(
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    UserProfileMinimalSerializer,
    UserAddressSerializer,
    UserAddressCreateSerializer,
    NotificationPreferencesSerializer,
    NotificationPreferencesUpdateSerializer,
    LoyaltyPointsHistorySerializer,
    UserActivityLogSerializer,
    UserDashboardSerializer
)

logger =logging.getLogger()

class StandardResultsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

# ==================== USER PROFILE VIEWS ====================

class UserProfileRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    GET /api/users/profile/
    Retrieve current user's profile
    
    PUT/PATCH /api/users/profile/
    Update user profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'put', 'head', 'options']
    
    def get_object(self):
        """Return the current authenticated user."""
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        """Get user profile."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, context={'request': request})
            instance.update_last_activity()
            
            logger.info(f"Profile retrieved for user: {request.user.email}")
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Profile retrieval error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve profile.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Update user profile."""
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        update_serializer = UserProfileUpdateSerializer(
            instance, 
            data=request.data, 
            partial=partial,
            context={'request': request}
        )
        
        if update_serializer.is_valid():
            try:
                self.perform_update(update_serializer)
                
                UserActivityLog.objects.create(
                    user=request.user,
                    activity_type='profile_updated',
                    description='Updated profile information',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                logger.info(f"Profile updated for user: {request.user.email}")
                
                serializer = self.get_serializer(instance, context={'request': request})
                return Response({
                    'success': True,
                    'message': _('Profile updated successfully.'),
                    'data': serializer.data
                })
                
            except Exception as e:
                logger.error(f"Profile update error for {request.user.email}: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to update profile.'),
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': update_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileMinimalView(generics.RetrieveAPIView):
    """
    GET /api/users/profile/minimal/
    Get minimal user info (used in orders, reviews, etc.)
    """
    serializer_class = UserProfileMinimalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Return the current authenticated user."""
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        """Get minimal user profile."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, context={'request': request})
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Minimal profile retrieval error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve profile.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== USER ADDRESS VIEWS ====================

class UserAddressListView(generics.ListAPIView):
    """
    GET /api/users/addresses/
    List all user addresses
    """
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination
    
    def get_queryset(self):
        """Return only addresses for the current user."""
        return self.request.user.addresses.all().order_by(
            '-is_default_shipping', 
            '-is_default_billing', 
            '-created_at'
        )
    
    def list(self, request, *args, **kwargs):
        """List user addresses."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={'request': request})
                return self.get_paginated_response({
                    'success': True,
                    'data': serializer.data
                })
            
            serializer = self.get_serializer(queryset, many=True, context={'request': request})
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Address list error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve addresses.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserAddressCreateView(generics.CreateAPIView):
    """
    POST /api/users/addresses/create/
    Create a new address
    """
    serializer_class = UserAddressCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """Create new address."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                address = serializer.save(user=self.request.user)
                
                UserActivityLog.objects.create(
                    user=self.request.user,
                    activity_type='address_created',
                    description=f'Added new {address.address_type} address',
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', '')
                )
                
                logger.info(f"Address created for user: {self.request.user.email}")
                
                # Return full address data
                full_serializer = UserAddressSerializer(address, context={'request': request})
                return Response({
                    'success': True,
                    'message': _('Address created successfully.'),
                    'data': full_serializer.data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Address creation error for {self.request.user.email}: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to create address.'),
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserAddressRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/users/addresses/{id}/ - Get specific address
    PUT/PATCH /api/users/addresses/{id}/ - Update address
    DELETE /api/users/addresses/{id}/ - Delete address
    """
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Return only addresses for the current user."""
        return self.request.user.addresses.all()
    
    def retrieve(self, request, *args, **kwargs):
        """Get specific address."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, context={'request': request})
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Address retrieve error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve address.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Update address."""
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        
        if serializer.is_valid():
            try:
                self.perform_update(serializer)
                
                UserActivityLog.objects.create(
                    user=self.request.user,
                    activity_type='address_updated',
                    description=f'Updated {instance.address_type} address',
                    ip_address=self.request.META.get('REMOTE_ADDR'),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', '')
                )
                
                logger.info(f"Address updated for user: {self.request.user.email}")
                
                return Response({
                    'success': True,
                    'message': _('Address updated successfully.'),
                    'data': serializer.data
                })
                
            except Exception as e:
                logger.error(f"Address update error for {self.request.user.email}: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to update address.'),
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_destroy(self, instance):
        """Delete address."""
        instance.delete()
        
        UserActivityLog.objects.create(
            user=self.request.user,
            activity_type='address_deleted',
            description=f'Deleted {instance.address_type} address',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        logger.info(f"Address deleted for user: {self.request.user.email}")


# ==================== NOTIFICATION PREFERENCES VIEWS ====================

class NotificationPreferencesRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    GET /api/users/notifications/
    Retrieve user's notification preferences
    
    PUT/PATCH /api/users/notifications/
    Update notification preferences
    """
    serializer_class = NotificationPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'put', 'head', 'options']
    
    def get_object(self):
        """Get or create notification preferences for user."""
        user = self.request.user
        preferences, created = NotificationPreferences.objects.get_or_create(user=user)
        if created:
            logger.info(f"Created default notification preferences for user: {user.email}")
        return preferences
    
    def retrieve(self, request, *args, **kwargs):
        """Get notification preferences."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Notification preferences retrieve error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve notification preferences.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Update notification preferences."""
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            try:
                self.perform_update(serializer)
                
                UserActivityLog.objects.create(
                    user=request.user,
                    activity_type='notification_preferences_updated',
                    description='Updated notification preferences',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                logger.info(f"Notification preferences updated for user: {request.user.email}")
                
                return Response({
                    'success': True,
                    'message': _('Notification preferences updated successfully.'),
                    'data': serializer.data
                })
                
            except Exception as e:
                logger.error(f"Notification preferences update error for {request.user.email}: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to update notification preferences.'),
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class NotificationChannelsUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/users/notifications/channels/
    Update only notification channels (email, sms, push)
    """
    serializer_class = NotificationPreferencesUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch', 'put', 'head', 'options']
    
    def get_object(self):
        """Get notification preferences for user."""
        user = self.request.user
        preferences, _ = NotificationPreferences.objects.get_or_create(user=user)
        return preferences
    
    def update(self, request, *args, **kwargs):
        """Update notification channels."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        
        if serializer.is_valid():
            try:
                self.perform_update(serializer)
                
                UserActivityLog.objects.create(
                    user=request.user,
                    activity_type='notification_channels_updated',
                    description='Updated notification channels',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                logger.info(f"Notification channels updated for user: {request.user.email}")
                
                return Response({
                    'success': True,
                    'message': _('Notification channels updated successfully.'),
                    'channels': serializer.data
                })
                
            except Exception as e:
                logger.error(f"Notification channels update error for {request.user.email}: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to update notification channels.'),
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== LOYALTY POINTS VIEWS ====================

class LoyaltyPointsHistoryListView(generics.ListAPIView):
    """
    GET /api/users/loyalty/history/
    List user's loyalty points history with pagination
    """
    serializer_class = LoyaltyPointsHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['created_at', 'points']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return loyalty history for current user."""
        return self.request.user.loyalty_points_history.all()
    
    def list(self, request, *args, **kwargs):
        """List loyalty points history with summary."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            total_earned = sum(item.points for item in queryset if item.points > 0)
            total_spent = abs(sum(item.points for item in queryset if item.points < 0))
            current_balance = self.request.user.loyalty_points
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'success': True,
                    'summary': {
                        'current_balance': current_balance,
                        'total_earned': total_earned,
                        'total_spent': total_spent
                    },
                    'data': serializer.data
                })
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'summary': {
                    'current_balance': current_balance,
                    'total_earned': total_earned,
                    'total_spent': total_spent
                },
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Loyalty history error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve loyalty history.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== USER ACTIVITY LOG VIEWS ====================

class UserActivityLogListView(generics.ListAPIView):
    """
    GET /api/users/activity/
    List user's activity logs with pagination
    """
    serializer_class = UserActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['created_at', 'activity_type']
    ordering = ['-created_at']
    search_fields = ['activity_type', 'description']
    
    def get_queryset(self):
        """Return activity logs for current user."""
        return self.request.user.activity_logs.all()
    
    def list(self, request, *args, **kwargs):
        """List activity logs with summary."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            total_activities = queryset.count()
            activity_types = queryset.values_list('activity_type', flat=True).distinct()
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'success': True,
                    'summary': {
                        'total_activities': total_activities,
                        'activity_types': list(activity_types)[:10]
                    },
                    'data': serializer.data
                })
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'summary': {
                    'total_activities': total_activities,
                    'activity_types': list(activity_types)[:10]
                },
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Activity log error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve activity logs.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

#
class UserDashboardView(generics.GenericAPIView):
    """
    GET /api/users/dashboard/
    Get comprehensive dashboard data for authenticated user
    """
    serializer_class = UserDashboardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """Get all dashboard data in one endpoint."""
        try:
            user = request.user
            
            # Prepare data for serializer
            dashboard_data = {
                'profile': user,
                'addresses': user.addresses.all(),
                'loyalty_history': user.loyalty_points_history.all()[:10]
            }
            
            serializer = self.get_serializer(dashboard_data, context={'request': request})
            
            # Update last activity
            user.update_last_activity()
            
            logger.info(f"Dashboard retrieved for user: {user.email}")
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Dashboard error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to load dashboard data.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)