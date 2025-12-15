# orders/serializers.py
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import datetime, timedelta
import re

from users.seriallizers.profile import UserProfileSerializer,UserProfileMinimalSerializer
from .models import Order, OrderItem
from products.serializers import ProductListSerializer, ProductVariantSerializer


# ==================== ORDER ITEM SERIALIZERS ====================

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    product_name = serializers.CharField(read_only=True, source='product.name')
    product_image = serializers.SerializerMethodField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'variant', 'product_name',
            'quantity', 'size', 'color', 'unit_price',
            'total_price', 'product_image', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_product_image(self, obj):
        """Get product image URL - safely handle missing images"""
        try:
            # Try different ways to get product image
            product = obj.product
            
            # Method 1: Check for image field
            if hasattr(product, 'image') and product.image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(product.image.url)
                return product.image.url
            
            # Method 2: Check for images relation
            if hasattr(product, 'images') and product.images.exists():
                first_image = product.images.first()
                if first_image and hasattr(first_image, 'image'):
                    request = self.context.get('request')
                    if request:
                        return request.build_absolute_uri(first_image.image.url)
                    return first_image.image.url
                    
            # Method 3: Check for primary_image
            if hasattr(product, 'primary_image') and product.primary_image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(product.primary_image.url)
                return product.primary_image.url
                
        except (AttributeError, ValueError) as e:
            # Log error but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting product image: {str(e)}")
            
        return None
    
    def get_total_price(self, obj):
        """Calculate total price"""
        try:
            if obj.unit_price and obj.quantity:
                return obj.unit_price * obj.quantity
        except (TypeError, AttributeError):
            pass
        return 0
    
    def validate_quantity(self, value):
        """Validate quantity"""
        if value < 1:
            raise serializers.ValidationError(_("Quantity must be at least 1."))
        if value > 100:
            raise serializers.ValidationError(_("Quantity cannot exceed 100."))
        return value

class OrderItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating order items"""
    class Meta:
        model = OrderItem
        fields = ['product', 'variant', 'quantity', 'size', 'color']
    
    def validate(self, data):
        """Validate order item data"""
        product = data.get('product')
        variant = data.get('variant')
        quantity = data.get('quantity', 1)
        
        # Check stock availability
        if variant:
            if variant.stock_quantity < quantity:
                raise serializers.ValidationError({
                    'quantity': _('Insufficient stock for this variant.')
                })
        elif product:
            if product.stock_quantity < quantity:
                raise serializers.ValidationError({
                    'quantity': _('Insufficient stock for this product.')
                })
        
        # Check if product is active
        if not product.is_active:
            raise serializers.ValidationError({
                'product': _('This product is not available.')
            })
        
        return data


# ==================== ORDER SERIALIZERS ====================

class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new orders"""
    items = OrderItemCreateSerializer(many=True, write_only=True)
    shipping_address_ref = serializers.IntegerField(
    required=False,
    allow_null=True,
    write_only=True,
    help_text="ID of the shipping address from user's addresses"
    )
    billing_address_ref = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="ID of the billing address from user's addresses"
    )
    
    class Meta:
        model = Order
        fields = [
            'shipping_method', 'customer_notes', 'gift_message',
            'gift_wrapping', 'payment_method', 'shipping_address_ref',
            'billing_address_ref', 'billing_same_as_shipping', 'items'
        ]
    
    def validate(self, data):
        """Validate order data"""
        request = self.context.get('request')

        # Ensure items are provided
        items = data.get('items', [])
        if not items:
            raise serializers.ValidationError({
                'items': _('At least one item is required.')
            })

        # Validate shipping method for Kenya
        shipping_method = data.get('shipping_method')

        # Get shipping county from address reference or user's default address
        shipping_address_ref = data.get('shipping_address_ref')
        shipping_county = None

        if shipping_address_ref:
            # shipping_address_ref is already a UserAddress object from validate_shipping_address_ref()
            # So we can directly access its county attribute
            shipping_county = shipping_address_ref.county
        elif request and request.user.is_authenticated:
            # If no shipping address provided, use user's default shipping address
            default_shipping = request.user.get_default_shipping_address()
            if default_shipping:
                shipping_county = default_shipping.county

        # Validate Nairobi-only shipping
        if shipping_method == 'nairobi_only' and shipping_county and shipping_county.lower() != 'nairobi':
            raise serializers.ValidationError({
                'shipping_method': _('Nairobi-only delivery is only available for Nairobi county.')
            })

        # Validate other towns shipping
        if shipping_method == 'other_towns' and shipping_county and shipping_county.lower() == 'nairobi':
            raise serializers.ValidationError({
                'shipping_method': _('Other towns delivery is not available for Nairobi county.')
            })

        return data
    
    def validate_shipping_address_ref(self, value):
        """Validate shipping address belongs to user"""
        if value:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                from users.models import UserAddress
                try:
                    # Validate the address exists and belongs to user
                    address = UserAddress.objects.get(id=value, user=request.user)
                    return address  # Return the UserAddress instance
                except UserAddress.DoesNotExist:
                    raise serializers.ValidationError(
                        _("Shipping address not found or doesn't belong to you.")
                    )
        return value
    
    def validate_billing_address_ref(self, value):
        """Validate billing address belongs to user"""
        if value:
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                from users.models import UserAddress
                try:
                    # Validate the address exists and belongs to user
                    address = UserAddress.objects.get(id=value, user=request.user)
                    return address
                except UserAddress.DoesNotExist:
                    raise serializers.ValidationError(
                        _("Billing address not found or doesn't belong to you.")
                    )
        return value
    
    def create(self, validated_data):
        """Create order with items"""
        request = self.context.get('request')
        items_data = validated_data.pop('items', [])
        
        # Get addresses from validated data
        shipping_address = validated_data.pop('shipping_address_ref', None)
        billing_address = validated_data.pop('billing_address_ref', None)
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            **validated_data
        )
        
        # Populate addresses if references provided
        if shipping_address:
            order.populate_from_user_address(shipping_address, 'shipping')
        elif request and request.user.is_authenticated:
            default_shipping = request.user.get_default_shipping_address()
            if default_shipping:
                order.populate_from_user_address(default_shipping, 'shipping')
        
        if billing_address:
            order.populate_from_user_address(billing_address, 'billing')
            order.billing_same_as_shipping = False
        elif validated_data.get('billing_same_as_shipping', True):
            order.billing_same_as_shipping = True
        
        # Create order items
        for item_data in items_data:
            product = item_data['product']
            # Get price from product - THIS IS MISSING!
            unit_price = product.price if product.price else 0
            
            OrderItem.objects.create(
                order=order,
                unit_price=unit_price,  # ADD THIS LINE
                **item_data
            )
        
        # Calculate totals
        order.calculate_totals()
        order.save()
        
        return order

class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for listing orders (compact view)"""
    user = UserProfileMinimalSerializer(read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    shipping_method_display = serializers.CharField(source='get_shipping_method_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    estimated_delivery_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'status', 'status_display',
            'payment_status', 'payment_status_display', 'payment_method',
            'payment_method_display', 'shipping_method', 'shipping_method_display',
            'total_amount', 'item_count', 'created_at', 'estimated_delivery_date'
        ]
        read_only_fields = fields
    
    def get_estimated_delivery_date(self, obj):
        """Calculate estimated delivery date - handle both dict and object"""
        try:
            # Handle case where obj might be a dictionary
            if isinstance(obj, dict):
                status = obj.get('status')
                shipped_at = obj.get('shipped_at')
            else:
                # Normal Order object
                status = obj.status
                shipped_at = obj.shipped_at
            
            if status in ['pending', 'confirmed', 'processing']:
                days = self._get_delivery_days(obj)
                if days:
                    return (timezone.now() + timedelta(days=days)).date()
            elif status == 'shipped' and shipped_at:
                days = self._get_delivery_days(obj)
                if days:
                    if isinstance(shipped_at, str):
                        shipped_at = datetime.fromisoformat(shipped_at.replace('Z', '+00:00'))
                    return (shipped_at + timedelta(days=days)).date()
            return None
            
        except Exception as e:
            # Log error but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error calculating delivery date: {str(e)}")
            return None
    
    def _get_delivery_days(self, obj):
        """Helper to get delivery days from object or dict"""
        try:
            if isinstance(obj, dict):
                shipping_method = obj.get('shipping_method')
                shipping_county = obj.get('shipping_county')
            else:
                shipping_method = obj.shipping_method
                shipping_county = obj.shipping_county
            
            # Delivery day logic
            if shipping_method == 'nairobi_only':
                is_nairobi = shipping_county and shipping_county.lower() == 'nairobi'
                return 1 if is_nairobi else None
            elif shipping_method == 'other_towns':
                is_nairobi = shipping_county and shipping_county.lower() == 'nairobi'
                return 3 if not is_nairobi else None
            elif shipping_method == 'next_day':
                return 1
            elif shipping_method == 'express':
                return 2
            elif shipping_method == 'standard':
                return 5
            return 7
            
        except Exception:
            return None


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed order view"""
    user = UserProfileMinimalSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    shipping_method_display = serializers.CharField(source='get_shipping_method_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    shipping_address = serializers.CharField(read_only=True)
    billing_address = serializers.CharField(read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    estimated_delivery_date = serializers.SerializerMethodField()
    can_be_cancelled = serializers.BooleanField(read_only=True)
    is_nairobi_order = serializers.BooleanField(read_only=True)
    mpesa_payment_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            # Order identification
            'id', 'order_number', 'user',
            
            # Status
            'status', 'status_display', 'payment_status', 'payment_status_display',
            'payment_method', 'payment_method_display',
            
            # Shipping
            'shipping_method', 'shipping_method_display',
            'shipping_tracking_number', 'shipping_carrier',
            
            # Pricing
            'subtotal', 'shipping_cost', 'tax_amount',
            'discount_amount', 'total_amount',
            
            # Customer info
            'customer_notes', 'gift_message', 'gift_wrapping', 'gift_wrapping_fee',
            
            # Shipping address
            'shipping_contact_name', 'shipping_contact_phone',
            'shipping_address_line1', 'shipping_address_line2',
            'shipping_city', 'shipping_county', 'shipping_postal_code',
            'shipping_country', 'shipping_address',
            
            # Billing address
            'billing_same_as_shipping',
            'billing_contact_name', 'billing_contact_phone',
            'billing_address_line1', 'billing_address_line2',
            'billing_city', 'billing_county', 'billing_postal_code',
            'billing_country', 'billing_address',
            
            # Address references
            'shipping_address_ref', 'billing_address_ref',
            
            # Items
            'items', 'item_count',
            
            # Timestamps
            'created_at', 'updated_at', 'confirmed_at', 'processed_at',
            'shipped_at', 'delivered_at', 'cancelled_at', 'payment_date',
            
            # Metadata
            'ip_address', 'user_agent',
            
            # Computed fields
            'estimated_delivery_date', 'can_be_cancelled',
            'is_nairobi_order', 'mpesa_payment_details'
        ]
        read_only_fields = fields
    
    def get_estimated_delivery_date(self, obj):
        """Calculate estimated delivery date"""
        if obj.status in ['pending', 'confirmed', 'processing']:
            days = obj.estimated_delivery_days()
            if days:
                return (timezone.now() + timedelta(days=days)).date()
        elif obj.status == 'shipped' and obj.shipped_at:
            days = obj.estimated_delivery_days()
            if days:
                return (obj.shipped_at + timedelta(days=days)).date()
        return None
    
    def get_mpesa_payment_details(self, obj):
        """Get M-Pesa payment details if applicable"""
        return obj.get_mpesa_payment_details()


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating orders (admin only)"""
    class Meta:
        model = Order
        fields = [
            'status', 'payment_status', 'shipping_tracking_number',
            'shipping_carrier', 'customer_notes'
        ]
    
    def validate_status(self, value):
        """Validate status transitions"""
        instance = self.instance
        
        # Prevent moving from delivered/cancelled/refunded to other statuses
        if instance.status in ['delivered', 'cancelled', 'refunded']:
            raise serializers.ValidationError(
                _('Cannot update order status from %(current_status)s.') % {
                    'current_status': instance.get_status_display()
                }
            )
        
        return value
    
    def validate_shipping_tracking_number(self, value):
        """Validate tracking number format"""
        if value and not re.match(r'^[A-Za-z0-9\-\s]+$', value):
            raise serializers.ValidationError(
                _('Tracking number can only contain letters, numbers, hyphens, and spaces.')
            )
        return value


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating order status only"""
    class Meta:
        model = Order
        fields = ['status']
    
    def validate_status(self, value):
        """Validate status transition"""
        instance = self.instance
        
        # Only allow certain status transitions
        allowed_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered'],
            'delivered': ['refunded'],
            'cancelled': [],
            'refunded': []
        }
        
        current_status = instance.status
        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                _('Cannot change status from %(current)s to %(new)s.') % {
                    'current': instance.get_status_display(),
                    'new': dict(Order.ORDER_STATUS_CHOICES).get(value, value)
                }
            )
        
        return value


class OrderPaymentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating payment information"""
    class Meta:
        model = Order
        fields = ['payment_status', 'payment_reference', 'payment_method', 'payment_date']
    
    def validate_payment_status(self, value):
        """Validate payment status transitions"""
        instance = self.instance
        
        # Only allow certain payment status transitions
        allowed_transitions = {
            'pending': ['authorized', 'paid', 'failed', 'cancelled'],
            'authorized': ['paid', 'failed', 'cancelled'],
            'paid': ['refunded', 'partially_paid'],
            'partially_paid': ['paid', 'refunded'],
            'failed': ['pending'],
            'cancelled': [],
            'refunded': []
        }
        
        current_status = instance.payment_status
        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                _('Cannot change payment status from %(current)s to %(new)s.') % {
                    'current': instance.get_payment_status_display(),
                    'new': dict(Order.PAYMENT_STATUS_CHOICES).get(value, value)
                }
            )
        
        return value
    
    def validate(self, data):
        """Validate payment data"""
        payment_status = data.get('payment_status')
        payment_date = data.get('payment_date')
        payment_reference = data.get('payment_reference')
        
        # If marking as paid, require payment date and reference
        if payment_status == 'paid':
            if not payment_date:
                data['payment_date'] = timezone.now()
            if not payment_reference:
                raise serializers.ValidationError({
                    'payment_reference': _('Payment reference is required when marking as paid.')
                })
        
        return data


# ==================== DASHBOARD/SUMMARY SERIALIZERS ====================

class OrderSummarySerializer(serializers.Serializer):
    """Serializer for order summary statistics"""
    total_orders = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_orders = serializers.IntegerField()
    delivered_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    most_ordered_product = serializers.CharField(allow_null=True)
    favorite_category = serializers.CharField(allow_null=True)


class MonthlyOrderStatsSerializer(serializers.Serializer):
    """Serializer for monthly order statistics"""
    month = serializers.CharField()
    year = serializers.IntegerField()
    order_count = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Serializer for order tracking information"""
    order_number = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    shipping_method_display = serializers.CharField(source='get_shipping_method_display', read_only=True)
    estimated_delivery_date = serializers.SerializerMethodField()
    tracking_url = serializers.SerializerMethodField()
    status_history = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'order_number', 'status', 'status_display',
            'shipping_method', 'shipping_method_display',
            'shipping_tracking_number', 'shipping_carrier',
            'estimated_delivery_date', 'tracking_url', 'status_history'
        ]
        read_only_fields = fields
    
    def get_estimated_delivery_date(self, obj):
        """Get estimated delivery date"""
        days = obj.estimated_delivery_days()
        if days:
            if obj.shipped_at:
                return (obj.shipped_at + timedelta(days=days)).date()
            return (timezone.now() + timedelta(days=days)).date()
        return None
    
    def get_tracking_url(self, obj):
        """Generate tracking URL based on carrier"""
        if obj.shipping_tracking_number and obj.shipping_carrier:
            carriers = {
                'fedex': 'https://www.fedex.com/fedextrack/?trknbr={}',
                'ups': 'https://www.ups.com/track?tracknum={}',
                'dhl': 'https://www.dhl.com/en/express/tracking.html?AWB={}',
                'usps': 'https://tools.usps.com/go/TrackConfirmAction?tLabels={}',
                # Add Kenyan carriers
                'posta': 'https://posta.co.ke/tracking?number={}',
                'g4s': 'https://www.g4s.co.ke/track?code={}',
                'sendy': 'https://sendy.co.ke/track/{}',
            }
            template = carriers.get(obj.shipping_carrier.lower())
            if template:
                return template.format(obj.shipping_tracking_number)
        return None
    
    def get_status_history(self, obj):
        """Get status change history"""
        history = []
        
        # Add created timestamp
        if obj.created_at:
            history.append({
                'status': 'created',
                'timestamp': obj.created_at,
                'description': 'Order created'
            })
        
        # Add confirmed timestamp
        if obj.confirmed_at:
            history.append({
                'status': 'confirmed',
                'timestamp': obj.confirmed_at,
                'description': 'Order confirmed'
            })
        
        # Add processed timestamp
        if obj.processed_at:
            history.append({
                'status': 'processing',
                'timestamp': obj.processed_at,
                'description': 'Order processing started'
            })
        
        # Add shipped timestamp
        if obj.shipped_at:
            history.append({
                'status': 'shipped',
                'timestamp': obj.shipped_at,
                'description': 'Order shipped'
            })
        
        # Add delivered timestamp
        if obj.delivered_at:
            history.append({
                'status': 'delivered',
                'timestamp': obj.delivered_at,
                'description': 'Order delivered'
            })
        
        # Add cancelled timestamp
        if obj.cancelled_at:
            history.append({
                'status': 'cancelled',
                'timestamp': obj.cancelled_at,
                'description': 'Order cancelled'
            })
        
        # Sort by timestamp
        history.sort(key=lambda x: x['timestamp'])
        return history


# ==================== CHECKOUT SERIALIZERS ====================

class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout process"""
    shipping_address_id = serializers.IntegerField(required=False)
    billing_address_id = serializers.IntegerField(required=False)
    billing_same_as_shipping = serializers.BooleanField(default=True)
    shipping_method = serializers.ChoiceField(
        choices=Order.SHIPPING_METHOD_CHOICES,
        default='standard'
    )
    payment_method = serializers.ChoiceField(
        choices=Order.PAYMENT_METHOD_CHOICES,
        required=True
    )
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    gift_message = serializers.CharField(required=False, allow_blank=True)
    gift_wrapping = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Validate checkout data"""
        request = self.context.get('request')
        
        # Validate addresses exist and belong to user
        shipping_address_id = data.get('shipping_address_id')
        billing_address_id = data.get('billing_address_id')
        
        if shipping_address_id:
            from users.models import UserAddress
            try:
                # Use integer ID lookup
                address = UserAddress.objects.get(
                    id=shipping_address_id,  # ← Integer, not UUID
                    user=request.user
                )
                data['shipping_address'] = address
            except UserAddress.DoesNotExist:
                raise serializers.ValidationError({
                    'shipping_address_id': _('Shipping address not found.')
                })
        else:
            # Use default shipping address
            default_address = request.user.get_default_shipping_address()
            if not default_address:
                raise serializers.ValidationError({
                    'shipping_address_id': _('Please select a shipping address.')
                })
            data['shipping_address'] = default_address
        
        if not data.get('billing_same_as_shipping') and billing_address_id:
            from users.models import UserAddress
            try:
                address = UserAddress.objects.get(
                    id=billing_address_id,  # ← Integer, not UUID
                    user=request.user
                )
                data['billing_address'] = address
            except UserAddress.DoesNotExist:
                raise serializers.ValidationError({
                    'billing_address_id': _('Billing address not found.')
                })
        
        # Validate shipping method for Kenya
        shipping_method = data.get('shipping_method')
        shipping_county = data['shipping_address'].county
        
        if shipping_method == 'nairobi_only' and shipping_county.lower() != 'nairobi':
            raise serializers.ValidationError({
                'shipping_method': _('Nairobi-only delivery is only available for Nairobi county.')
            })
        
        if shipping_method == 'other_towns' and shipping_county.lower() == 'nairobi':
            raise serializers.ValidationError({
                'shipping_method': _('Other towns delivery is not available for Nairobi county.')
            })
        
        return data


class CheckoutResponseSerializer(serializers.Serializer):
    """Serializer for checkout response"""
    order = OrderDetailSerializer()
    payment_required = serializers.BooleanField()
    payment_url = serializers.URLField(required=False, allow_null=True)
    payment_instructions = serializers.CharField(required=False, allow_null=True)
    success = serializers.BooleanField()
    message = serializers.CharField()