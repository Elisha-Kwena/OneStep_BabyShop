# orders/views.py
from rest_framework import status, generics, permissions, filters
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from cart.models import Cart

from .models import Order, OrderItem
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
    OrderUpdateSerializer,
    OrderStatusUpdateSerializer,
    OrderPaymentUpdateSerializer,
    OrderItemSerializer,
    OrderItemCreateSerializer,
    OrderSummarySerializer,
    MonthlyOrderStatsSerializer,
    OrderTrackingSerializer,
    CheckoutSerializer,
    CheckoutResponseSerializer
)
from users.models import UserAddress

logger = logging.getLogger(__name__)


class StandardResultsPagination(PageNumberPagination):
    """Standard pagination for orders."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ==================== ORDER VIEWS ====================

class OrderListView(generics.ListAPIView):
    """
    GET /api/orders/
    List all orders for authenticated user with filtering and pagination
    """
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']
    search_fields = ['order_number', 'shipping_contact_name']
    
    def get_queryset(self):
        """Return orders for current user with filters."""
        user = self.request.user
        queryset = Order.objects.filter(user=user)
        
        # Apply filters from query parameters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        payment_status_filter = self.request.query_params.get('payment_status')
        if payment_status_filter:
            queryset = queryset.filter(payment_status=payment_status_filter)
        
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
        """List orders with summary."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            # Get summary statistics
            total_orders = queryset.count()
            total_spent = queryset.aggregate(total=Sum('total_amount'))['total'] or 0
            pending_orders = queryset.filter(status='pending').count()
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'success': True,
                    'summary': {
                        'total_orders': total_orders,
                        'total_spent': float(total_spent),
                        'pending_orders': pending_orders
                    },
                    'data': serializer.data
                })
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'summary': {
                    'total_orders': total_orders,
                    'total_spent': float(total_spent),
                    'pending_orders': pending_orders
                },
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Order list error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve orders.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderCreateView(generics.CreateAPIView):
    """
    POST /api/orders/create/
    Create a new order from cart or items
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """Create a new order."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                order = serializer.save()
                
                # Clear user's cart after successful order creation
                try:
                    request.user.cart.clear()
                except:
                    pass
                
                logger.info(f"Order created: {order.order_number} for {request.user.email}")
                
                # Return detailed order information
                detail_serializer = OrderDetailSerializer(order, context={'request': request})
                return Response({
                    'success': True,
                    'message': _('Order created successfully.'),
                    'order': detail_serializer.data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Order creation error for {request.user.email}: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to create order.')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailView(generics.RetrieveAPIView):
    """
    GET /api/orders/{order_number}/
    Retrieve detailed order information
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'
    lookup_url_kwarg = 'order_number'
    
    def get_queryset(self):
        """Return orders for current user."""
        return Order.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Get order details."""
        try:
            order_number = kwargs.get('order_number')
            
            # Try to get the order
            try:
                instance = Order.objects.get(
                    order_number=order_number,
                    user=request.user
                )
            except Order.DoesNotExist:
                return Response({
                    'success': False,
                    'message': _('Order not found or you do not have permission to view it.')
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(instance, context={'request': request})
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Order detail error for {request.user.email}: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': _('Failed to retrieve order details.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderUpdateView(generics.UpdateAPIView):
    """
    PUT/PATCH /api/orders/{order_number}/update/
    Update order information (admin/customer service)
    """
    serializer_class = OrderUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'
    lookup_url_kwarg = 'order_number'
    
    def get_permissions(self):
        """Only allow staff/admin to update orders."""
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()
    
    def get_queryset(self):
        """Return all orders for staff, user's orders for regular users."""
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        """Update order."""
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            try:
                self.perform_update(serializer)
                
                logger.info(f"Order updated: {instance.order_number} by {request.user.email}")
                
                # Return updated order
                detail_serializer = OrderDetailSerializer(instance, context={'request': request})
                return Response({
                    'success': True,
                    'message': _('Order updated successfully.'),
                    'data': detail_serializer.data
                })
                
            except Exception as e:
                logger.error(f"Order update error: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to update order.')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class OrderCancelView(generics.GenericAPIView):
    """
    POST /api/orders/{order_number}/cancel/
    Cancel an order
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'
    lookup_url_kwarg = 'order_number'
    
    def get_queryset(self):
        """Return cancellable orders for current user."""
        return Order.objects.filter(
            user=self.request.user,
            status__in=['pending', 'confirmed', 'processing']
        )
    
    def post(self, request, *args, **kwargs):
        """Cancel order."""
        try:
            order = self.get_object()
            
            if not order.can_be_cancelled():
                return Response({
                    'success': False,
                    'message': _('This order cannot be cancelled.')
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update order status
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.save()
            
            logger.info(f"Order cancelled: {order.order_number} by {request.user.email}")
            
            # Return updated order
            serializer = OrderDetailSerializer(order, context={'request': request})
            return Response({
                'success': True,
                'message': _('Order cancelled successfully.'),
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Order cancellation error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to cancel order.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderStatusUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/orders/{order_number}/status/
    Update order status only (admin)
    """
    serializer_class = OrderStatusUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'order_number'
    lookup_url_kwarg = 'order_number'
    
    def get_queryset(self):
        """Return all orders for admin."""
        return Order.objects.all()
    
    def update(self, request, *args, **kwargs):
        """Update order status."""
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            try:
                self.perform_update(serializer)
                
                logger.info(f"Order status updated: {instance.order_number} to {instance.status}")
                
                # Return updated order
                detail_serializer = OrderDetailSerializer(instance, context={'request': request})
                return Response({
                    'success': True,
                    'message': _('Order status updated successfully.'),
                    'data': detail_serializer.data
                })
                
            except Exception as e:
                logger.error(f"Order status update error: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to update order status.')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class OrderPaymentUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/orders/{order_number}/payment/
    Update payment information (admin)
    """
    serializer_class = OrderPaymentUpdateSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'order_number'
    lookup_url_kwarg = 'order_number'
    
    def get_queryset(self):
        """Return all orders for admin."""
        return Order.objects.all()
    
    def update(self, request, *args, **kwargs):
        """Update payment information."""
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            try:
                self.perform_update(serializer)
                
                logger.info(f"Order payment updated: {instance.order_number}")
                
                # Return updated order
                detail_serializer = OrderDetailSerializer(instance, context={'request': request})
                return Response({
                    'success': True,
                    'message': _('Payment information updated successfully.'),
                    'data': detail_serializer.data
                })
                
            except Exception as e:
                logger.error(f"Order payment update error: {str(e)}")
                return Response({
                    'success': False,
                    'message': _('Failed to update payment information.')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# ==================== ORDER ITEM VIEWS ====================

class OrderItemListView(generics.ListAPIView):
    """
    GET /api/orders/{order_number}/items/
    List all items in an order
    """
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsPagination
    
    def get_queryset(self):
        """Return items for the specified order."""
        order_number = self.kwargs.get('order_number')
        return OrderItem.objects.filter(
            order__order_number=order_number,
            order__user=self.request.user
        )
    
    def list(self, request, *args, **kwargs):
        """List order items."""
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
            logger.error(f"Order items list error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve order items.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== DASHBOARD & ANALYTICS VIEWS ====================

class OrderSummaryView(generics.GenericAPIView):
    """
    GET /api/orders/summary/
    Get order summary statistics for authenticated user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """Get order summary."""
        try:
            user = request.user
            
            # Initialize with default values
            summary_data = {
                'total_orders': 0,
                'total_spent': 0.0,
                'pending_orders': 0,
                'delivered_orders': 0,
                'cancelled_orders': 0,
                'average_order_value': 0.0,
                'most_ordered_product': None,
                'favorite_category': None
            }
            
            # Check if user has any orders first
            orders = Order.objects.filter(user=user)
            
            if orders.exists():
                # Calculate statistics
                total_orders = orders.count()
                total_spent = orders.aggregate(total=Sum('total_amount'))['total'] or 0
                pending_orders = orders.filter(status='pending').count()
                delivered_orders = orders.filter(status='delivered').count()
                cancelled_orders = orders.filter(status='cancelled').count()
                average_order_value = orders.aggregate(avg=Avg('total_amount'))['avg'] or 0
                
                # Get most ordered product
                most_ordered_product = None
                product_counts = OrderItem.objects.filter(
                    order__user=user
                ).values('product__name').annotate(
                    count=Count('id')
                ).order_by('-count').first()
                
                if product_counts and product_counts.get('product__name'):
                    most_ordered_product = product_counts['product__name']
                
                # Get favorite category
                favorite_category = None
                category_counts = OrderItem.objects.filter(
                    order__user=user
                ).values('product__category__name').annotate(
                    count=Count('id')
                ).order_by('-count').first()
                
                if category_counts and category_counts.get('product__category__name'):
                    favorite_category = category_counts['product__category__name']
                
                summary_data = {
                    'total_orders': total_orders,
                    'total_spent': float(total_spent),
                    'pending_orders': pending_orders,
                    'delivered_orders': delivered_orders,
                    'cancelled_orders': cancelled_orders,
                    'average_order_value': float(average_order_value),
                    'most_ordered_product': most_ordered_product,
                    'favorite_category': favorite_category
                }
            
            serializer = OrderSummarySerializer(summary_data)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Order summary error for {request.user.email}: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': _('Failed to retrieve order summary.'),
                'error': str(e)  # Include for debugging
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"Order summary error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve order summary.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from collections import defaultdict
from datetime import datetime

class MonthlyOrderStatsView(generics.GenericAPIView):
    """
    GET /api/orders/stats/monthly/
    Get monthly order statistics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """Get monthly order statistics."""
        try:
            user = request.user
            months = int(request.query_params.get('months', 6))
            
            # Calculate date range
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30 * months)
            
            # Get all orders in the date range
            orders = Order.objects.filter(
                user=user,
                created_at__range=[start_date, end_date]
            )
            
            # Group by month and year
            monthly_data = defaultdict(lambda: {'count': 0, 'total': 0})
            
            for order in orders:
                month_year = (order.created_at.year, order.created_at.month)
                monthly_data[month_year]['count'] += 1
                monthly_data[month_year]['total'] += float(order.total_amount)
            
            # Prepare response
            stats_data = []
            month_names = {
                1: 'January', 2: 'February', 3: 'March', 4: 'April',
                5: 'May', 6: 'June', 7: 'July', 8: 'August',
                9: 'September', 10: 'October', 11: 'November', 12: 'December'
            }
            
            for (year, month), data in sorted(monthly_data.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True):
                count = data['count']
                total = data['total']
                avg_value = total / count if count > 0 else 0
                
                stats_data.append({
                    'month': month_names.get(month, 'Unknown'),
                    'year': year,
                    'order_count': count,
                    'total_amount': total,
                    'average_order_value': avg_value
                })
            
            serializer = MonthlyOrderStatsSerializer(stats_data, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Monthly stats error for {request.user.email}: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': _('Failed to retrieve monthly statistics.'),
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# ==================== TRACKING VIEWS ====================

class OrderTrackView(generics.RetrieveAPIView):
    """
    GET /api/orders/{order_number}/track/
    Get order tracking information
    """
    serializer_class = OrderTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'
    lookup_url_kwarg = 'order_number'
    
    def get_queryset(self):
        """Return orders for current user."""
        return Order.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Get tracking information."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Order tracking error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve tracking information.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== CHECKOUT VIEWS ====================

class CheckoutView(generics.CreateAPIView):
    """
    POST /api/v1/orders/checkout/
    Process checkout from cart
    """
    serializer_class = CheckoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Order.objects.all()

    def create(self, request, *args, **kwargs):
        print("=== CHECKOUT VIEW CALLED ===")
        print(f"Request method: {request.method}")
        print(f"User: {request.user.email}")
        
        logger.info(f"Checkout request from user: {request.user.email}")
        logger.info(f"Checkout request from user: {request.user.email}")
        logger.info(f"Checkout data: {request.data}")
        logger.info(f"User has cart: {hasattr(request.user, 'cart')}")
        
        if hasattr(request.user, 'cart'):
            logger.info(f"Cart items: {request.user.cart.items.count()}")
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            validated_data = serializer.validated_data
            
            # Get user's cart
            try:
                cart = request.user.cart
                if cart.total_items == 0:
                    return Response({
                        'success': False,
                        'message': _('Your cart is empty.')
                    }, status=status.HTTP_400_BAD_REQUEST)
            except AttributeError:
                # Cart doesn't exist - create one
                cart, created = Cart.objects.get_or_create(user=request.user)
                if cart.total_items == 0:
                    return Response({
                        'success': False,
                        'message': _('Your cart is empty.')
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create order from cart
            order = Order.objects.create(
                user=request.user,
                shipping_method=validated_data['shipping_method'],
                payment_method=validated_data['payment_method'],
                customer_notes=validated_data.get('customer_notes', ''),
                gift_message=validated_data.get('gift_message', ''),
                gift_wrapping=validated_data.get('gift_wrapping', False),
                billing_same_as_shipping=validated_data.get('billing_same_as_shipping', True)
            )
            
            # Set addresses
            shipping_address = validated_data.get('shipping_address')
            if shipping_address:
                order.populate_from_user_address(shipping_address, 'shipping')
            
            if not validated_data.get('billing_same_as_shipping', True):
                billing_address = validated_data.get('billing_address')
                if billing_address:
                    order.populate_from_user_address(billing_address, 'billing')
            
            # Create order items from cart
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    variant=cart_item.variant,
                    quantity=cart_item.quantity,
                    size=cart_item.size,
                    color=cart_item.color,
                    unit_price=cart_item.unit_price
                )
            
            # Calculate totals and save
            order.calculate_totals()
            order.save()
            
            # Clear cart
            cart.clear()
            
            logger.info(f"Checkout completed: {order.order_number} for {request.user.email}")
            
            # Prepare response based on payment method
            payment_required = order.payment_status != 'paid'
            payment_url = None
            payment_instructions = None
            
            if payment_required:
                # Generate payment URL or instructions based on payment method
                if order.payment_method == 'mpesa':
                    payment_instructions = f"Please send KES {order.total_amount} to M-Pesa Paybill 123456, Account {order.order_number}"
                elif order.payment_method in ['credit_card', 'debit_card']:
                    payment_url = f"/api/payments/process/?order={order.order_number}"
            
            response_data = {
                'order': OrderDetailSerializer(order, context={'request': request}).data,
                'payment_required': payment_required,
                'payment_url': payment_url,
                'payment_instructions': payment_instructions,
                'success': True,
                'message': _('Checkout completed successfully.')
            }
            
            response_serializer = CheckoutResponseSerializer(response_data)
            
            return Response({
                'success': True,
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Checkout error for {request.user.email}: {str(e)}")
            return Response({
                'success': False,
                'message': _('Checkout failed. Please try again.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# ==================== ADMIN VIEWS ====================

class AdminOrderListView(generics.ListAPIView):
    """
    GET /api/admin/orders/
    List all orders for admin with advanced filtering
    """
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ['created_at', 'total_amount', 'status', 'payment_status']
    ordering = ['-created_at']
    search_fields = [
        'order_number', 'user__email', 'user__username',
        'shipping_contact_name', 'shipping_contact_phone'
    ]
    
    def get_queryset(self):
        """Return all orders with admin filters."""
        queryset = Order.objects.all()
        
        # Apply filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        payment_status_filter = self.request.query_params.get('payment_status')
        if payment_status_filter:
            queryset = queryset.filter(payment_status=payment_status_filter)
        
        user_filter = self.request.query_params.get('user')
        if user_filter:
            queryset = queryset.filter(
                Q(user__email__icontains=user_filter) |
                Q(user__username__icontains=user_filter)
            )
        
        county_filter = self.request.query_params.get('county')
        if county_filter:
            queryset = queryset.filter(shipping_county__icontains=county_filter)
        
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
        """List all orders with admin summary."""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            # Get admin summary
            total_orders = queryset.count()
            total_revenue = queryset.aggregate(total=Sum('total_amount'))['total'] or 0
            pending_orders = queryset.filter(status='pending').count()
            paid_orders = queryset.filter(payment_status='paid').count()
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'success': True,
                    'summary': {
                        'total_orders': total_orders,
                        'total_revenue': float(total_revenue),
                        'pending_orders': pending_orders,
                        'paid_orders': paid_orders
                    },
                    'data': serializer.data
                })
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'summary': {
                    'total_orders': total_orders,
                    'total_revenue': float(total_revenue),
                    'pending_orders': pending_orders,
                    'paid_orders': paid_orders
                },
                'data': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Admin order list error: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to retrieve orders.')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# Add this NEW view class
