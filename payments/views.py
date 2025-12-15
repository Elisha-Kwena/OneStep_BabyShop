# payments/views.py
from rest_framework import status, generics, permissions, filters
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q,Sum
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import Payment, PaymentMethod, PaymentWebhook
from .serializers import (
    PaymentMethodSerializer,
    PaymentMethodListSerializer,
    PaymentCreateSerializer,
    PaymentDetailSerializer,
    PaymentListSerializer,
    PaymentStatusUpdateSerializer,
    PaymentRefundSerializer,
    PaymentWebhookSerializer,
    PaymentInitiationResponseSerializer,
    PaymentVerificationResponseSerializer
)

logger = logging.getLogger(__name__)


class StandardResultsPagination(PageNumberPagination):
    """Standard pagination for payments."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ==================== PAYMENT METHOD VIEWS ====================

class PaymentMethodListView(generics.ListAPIView):
    """
    GET /api/payments/methods/
    List available payment methods
    """
    serializer_class = PaymentMethodListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Return active payment methods."""
        return PaymentMethod.objects.filter(is_active=True).order_by('sort_order')
    
    def list(self, request, *args, **kwargs):
        """List payment methods."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Payment method list error: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve payment methods.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== PAYMENT VIEWS ====================

class PaymentListView(generics.ListAPIView):
    """
    GET /api/payments/
    List user's payments with filtering
    """
    serializer_class = PaymentListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']
    search_fields = ['payment_reference', 'order__order_number']
    
    def get_queryset(self):
        """Return payments for current user."""
        user = self.request.user
        queryset = Payment.objects.filter(user=user)
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        gateway_filter = self.request.query_params.get('gateway')
        if gateway_filter:
            queryset = queryset.filter(payment_gateway=gateway_filter)
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
            except ValueError:
                pass
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
            except ValueError:
                pass
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """List payments with summary."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            # Get summary
            total_payments = queryset.count()
            total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0
            successful_payments = queryset.filter(status='successful').count()
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'success': True,
                    'summary': {
                        'total_payments': total_payments,
                        'total_amount': float(total_amount),
                        'successful_payments': successful_payments
                    },
                    'data': serializer.data
                })
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'summary': {
                    'total_payments': total_payments,
                    'total_amount': float(total_amount),
                    'successful_payments': successful_payments
                },
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Payment list error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve payments.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# payments/views.py
class PaymentCreateView(generics.CreateAPIView):
    """
    POST /api/payments/create/
    Initiate a new payment
    """
    serializer_class = PaymentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """Create a new payment."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                payment = serializer.save()
                
                # Log successful creation
                logger.info(f"Payment initiated: {payment.payment_reference} for {request.user.email}")
                
                # TODO: Integrate with actual payment gateway here
                # For now, simulate payment initiation
                checkout_url = None
                payment_instructions = None
                
                # Set checkout URL for card payments
                if payment.payment_gateway in ['stripe', 'paypal']:
                    checkout_url = f"/api/payments/{payment.payment_reference}/checkout/"
                
                # Set instructions for mobile money
                elif payment.payment_gateway in ['mpesa', 'airtel_money', 'tkash', 'equitel']:
                    payment_instructions = f"Please send KES {payment.amount} to {payment.payment_gateway.upper()}"
                
                # Prepare response - use a simpler approach to avoid serialization errors
                try:
                    # First try with full serializer
                    payment_serializer = PaymentDetailSerializer(payment, context={'request': request})
                    payment_data = payment_serializer.data
                except Exception as e:
                    # If that fails, use minimal data
                    logger.warning(f"Full payment serialization failed, using minimal data: {str(e)}")
                    payment_data = self.get_minimal_payment_data(payment)
                
                response_data = {
                    'payment': payment_data,
                    'checkout_url': checkout_url,
                    'payment_instructions': payment_instructions,
                    'success': True,
                    'message': _('Payment initiated successfully.')
                }
                
                response_serializer = PaymentInitiationResponseSerializer(response_data)
                
                return Response({
                    'success': True,
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Payment creation error for {request.user.email}: {str(e)}", exc_info=True)
                return Response({
                    'success': False,
                    'message': _('Failed to initiate payment.'),
                    'error': str(e)  # Include error for debugging
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_minimal_payment_data(self, payment):
        """Get minimal payment data when full serialization fails"""
        return {
            'id': payment.id,
            'payment_reference': payment.payment_reference,
            'amount': float(payment.amount),
            'currency': payment.currency,
            'payment_gateway': payment.payment_gateway,
            'payment_gateway_display': payment.get_payment_gateway_display(),
            'status': payment.status,
            'status_display': payment.get_status_display(),
            'created_at': payment.created_at.isoformat(),
            'order': {
                'id': payment.order.id,
                'order_number': payment.order.order_number,
                'total_amount': float(payment.order.total_amount)
            } if payment.order else None
        }
class PaymentDetailView(generics.RetrieveAPIView):
    """
    GET /api/payments/{payment_reference}/
    Get payment details
    """
    serializer_class = PaymentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'payment_reference'
    lookup_url_kwarg = 'payment_reference'
    
    def get_queryset(self):
        """Return payments for current user."""
        return Payment.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Get payment details."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, context={'request': request})
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Payment detail error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve payment details.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentVerifyView(generics.GenericAPIView):
    """
    POST /api/payments/{payment_reference}/verify/
    Verify payment status with payment gateway
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'payment_reference'
    lookup_url_kwarg = 'payment_reference'
    
    def get_queryset(self):
        """Return payments for current user."""
        return Payment.objects.filter(user=self.request.user)
    
    def post(self, request, *args, **kwargs):
        """Verify payment status."""
        try:
            payment = self.get_object()
            
            # TODO: Integrate with actual payment gateway verification
            # This is a placeholder implementation
            
            is_verified = False
            verification_message = ""
            
            if payment.status == 'successful':
                is_verified = True
                verification_message = "Payment already verified and successful."
            elif payment.status == 'pending':
                # Simulate checking with payment gateway
                # In real implementation, call gateway API here
                
                # Placeholder: Mark as successful for demo
                # payment.mark_as_successful(gateway_ref="DEMO-123")
                # is_verified = True
                # verification_message = "Payment verified successfully."
                
                is_verified = False
                verification_message = "Payment verification not implemented yet."
            else:
                verification_message = f"Payment status is {payment.get_status_display()}"
            
            # Prepare response
            response_data = {
                'payment': PaymentDetailSerializer(payment, context={'request': request}).data,
                'is_verified': is_verified,
                'verification_message': verification_message,
                'success': True,
                'message': _('Payment verification completed.')
            }
            
            response_serializer = PaymentVerificationResponseSerializer(response_data)
            
            return Response({
                'success': True,
                'data': response_serializer.data
            })
            
        except Exception as e:
            logger.error(f"Payment verification error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to verify payment.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentRefundView(generics.GenericAPIView):
    """
    POST /api/payments/{payment_reference}/refund/
    Refund a payment (admin only)
    """
    serializer_class = PaymentRefundSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'payment_reference'
    lookup_url_kwarg = 'payment_reference'
    
    def get_queryset(self):
        """Return refundable payments."""
        return Payment.objects.filter(status='successful')
    
    def post(self, request, *args, **kwargs):
        """Process refund."""
        payment = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'payment': payment})
        
        if serializer.is_valid():
            try:
                refund_amount = serializer.validated_data['refund_amount']
                refund_reason = serializer.validated_data.get('refund_reason', '')
                
                # TODO: Integrate with actual payment gateway refund
                # This is a placeholder implementation
                
                # Simulate refund
                # payment.mark_as_refunded(
                #     amount=refund_amount,
                #     reason=refund_reason,
                #     reference=f"REF-{payment.payment_reference}"
                # )
                
                logger.info(f"Refund requested for payment: {payment.payment_reference}")
                
                return Response({
                    'success': True,
                    'message': _('Refund request submitted. Payment gateway integration required.'),
                    'refund_details': {
                        'payment_reference': payment.payment_reference,
                        'refund_amount': float(refund_amount),
                        'refund_reason': refund_reason
                    }
                })
                
            except Exception as e:
                logger.error(f"Refund error: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to process refund.')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== WEBHOOK VIEWS ====================

class PaymentWebhookView(generics.GenericAPIView):
    """
    POST /api/payments/webhook/{gateway}/
    Receive payment webhooks from payment gateways
    """
    permission_classes = [permissions.AllowAny]  # Webhooks don't require authentication
    
    def post(self, request, *args, **kwargs):
        """Process payment webhook."""
        gateway = kwargs.get('gateway')
        
        try:
            # Log webhook
            webhook = PaymentWebhook.objects.create(
                gateway=gateway,
                event_type=request.headers.get('X-Event-Type', 'unknown'),
                payload=request.data,
                headers=dict(request.headers),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # TODO: Process webhook based on gateway
            # This needs to be implemented for each payment gateway
            
            # Example structure for processing:
            # if gateway == 'mpesa':
            #     self._process_mpesa_webhook(webhook, request.data)
            # elif gateway == 'stripe':
            #     self._process_stripe_webhook(webhook, request.data)
            
            # For now, just acknowledge receipt
            webhook.is_processed = True
            webhook.processing_error = "Webhook processing not implemented"
            webhook.save()
            
            logger.info(f"Webhook received from {gateway}")
            
            return Response({
                'success': True,
                'message': 'Webhook received'
            })
            
        except Exception as e:
            logger.error(f"Webhook processing error from {gateway}: {str(e)}")
            return Response({
                'success': False,
                'message': 'Webhook processing failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== ADMIN VIEWS ====================

class AdminPaymentListView(generics.ListAPIView):
    """
    GET /api/admin/payments/
    List all payments for admin
    """
    serializer_class = PaymentListSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['created_at', 'amount', 'status', 'payment_gateway']
    ordering = ['-created_at']
    search_fields = [
        'payment_reference', 'gateway_reference',
        'user__email', 'user__username',
        'order__order_number', 'mobile_number'
    ]
    
    def get_queryset(self):
        """Return all payments with admin filters."""
        queryset = Payment.objects.all()
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        gateway_filter = self.request.query_params.get('gateway')
        if gateway_filter:
            queryset = queryset.filter(payment_gateway=gateway_filter)
        
        user_filter = self.request.query_params.get('user')
        if user_filter:
            queryset = queryset.filter(
                Q(user__email__icontains=user_filter) |
                Q(user__username__icontains=user_filter)
            )
        
        date_from = self.request.query_params.get('date_from')
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
            except ValueError:
                pass
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
            except ValueError:
                pass
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """List all payments with admin summary."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            # Get admin summary
            total_payments = queryset.count()
            total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0
            successful_payments = queryset.filter(status='successful').count()
            pending_payments = queryset.filter(status='pending').count()
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'success': True,
                    'summary': {
                        'total_payments': total_payments,
                        'total_amount': float(total_amount),
                        'successful_payments': successful_payments,
                        'pending_payments': pending_payments
                    },
                    'data': serializer.data
                })
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'summary': {
                    'total_payments': total_payments,
                    'total_amount': float(total_amount),
                    'successful_payments': successful_payments,
                    'pending_payments': pending_payments
                },
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Admin payment list error: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve payments.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentStatusUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/admin/payments/{payment_reference}/status/
    Update payment status (admin only)
    """
    serializer_class = PaymentStatusUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'payment_reference'
    lookup_url_kwarg = 'payment_reference'
    
    def get_queryset(self):
        """Return all payments for admin."""
        return Payment.objects.all()
    
    def update(self, request, *args, **kwargs):
        """Update payment status."""
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            try:
                self.perform_update(serializer)
                
                logger.info(f"Payment status updated: {instance.payment_reference} to {instance.status}")
                
                # Return updated payment
                detail_serializer = PaymentDetailSerializer(instance, context={'request': request})
                return Response({
                    'success': True,
                    'message': _('Payment status updated successfully.'),
                    'data': detail_serializer.data
                })
                
            except Exception as e:
                logger.error(f"Payment status update error: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to update payment status.')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)