# payments/serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import datetime
from django.core.validators import RegexValidator
import re

from .models import Payment, PaymentMethod, PaymentWebhook
from orders.serializers import OrderListSerializer
from users.seriallizers.profile import UserProfileMinimalSerializer


# ==================== PAYMENT METHOD SERIALIZERS ====================

class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'gateway', 'method_type', 'display_name',
            'description', 'icon', 'is_active', 'is_default', 'sort_order',
            'min_amount', 'max_amount', 'processing_fee_percent',
            'processing_fee_fixed', 'supported_networks', 'is_available'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_is_available(self, obj):
        """Check if payment method is available for current request context."""
        request = self.context.get('request')
        if request and hasattr(request, 'data'):
            amount = request.data.get('amount')
            if amount:
                return obj.is_available_for_amount(float(amount))
        return obj.is_active


class PaymentMethodListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing payment methods"""
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'display_name', 'description', 'icon',
            'method_type', 'is_active', 'sort_order'
        ]


# ==================== PAYMENT SERIALIZERS ====================

class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for initiating a payment"""
    order_number = serializers.CharField(write_only=True, max_length=20)
    mobile_number = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[
            RegexValidator(
                regex=r'^(?:254|\+254|0)?(7(?:(?:[129][0-9])|(?:0[0-9])|(4[0-9])|(5[0-9])|(6[0-9])|(8[0-9]))[0-9]{6})$',
                message=_("Please enter a valid Kenyan phone number.")
            )
        ]
    )
    
    class Meta:
        model = Payment
        fields = [
            'order_number', 'payment_gateway', 'payment_method',
            'mobile_number', 'mobile_network', 'amount'
        ]
    
    def validate(self, data):
        """Validate payment creation data."""
        request = self.context.get('request')
        order_number = data.pop('order_number')
        
        # Get order by order_number
        from orders.models import Order
        try:
            order = Order.objects.get(order_number=order_number, user=request.user)
        except Order.DoesNotExist:
            raise serializers.ValidationError({
                'order_number': _('Order not found.')
            })
        
        # Check if order already has successful payment
        if order.payments.filter(status='successful').exists():
            raise serializers.ValidationError({
                'order_number': _('This order already has a successful payment.')
            })
        
        # Validate amount matches order total
        amount = data.get('amount')
        if amount and float(amount) != float(order.total_amount):
            raise serializers.ValidationError({
                'amount': _('Payment amount must match order total.')
            })
        
        # Set amount from order if not provided
        if not amount:
            data['amount'] = order.total_amount
        
        # Validate payment gateway selection
        payment_gateway = data.get('payment_gateway')
        if payment_gateway:
            # TODO: Validate payment gateway availability
            pass
        
        # Validate mobile number for mobile money payments
        if data.get('payment_gateway') in ['mpesa', 'airtel_money', 'tkash', 'equitel']:
            if not data.get('mobile_number'):
                raise serializers.ValidationError({
                    'mobile_number': _('Mobile number is required for mobile money payments.')
                })
        
        data['order'] = order
        return data
    
    def create(self, validated_data):
        """Create payment record."""
        request = self.context.get('request')
        order = validated_data.pop('order')
        
        # Generate payment reference
        payment_reference = validated_data.pop('payment_reference', None)
        if not payment_reference:
            # Use order number + timestamp for unique reference
            timestamp = timezone.now().strftime('%H%M%S')
            payment_reference = f"PAY-{order.order_number}-{timestamp}"
        
        payment = Payment.objects.create(
            order=order,
            user=request.user,
            payment_reference=payment_reference,
            currency='KES',
            status='initiated',
            **validated_data
        )
        
        return payment


class PaymentDetailSerializer(serializers.ModelSerializer):
    """Serializer for payment details"""
    order = OrderListSerializer(read_only=True)
    user = UserProfileMinimalSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_gateway_display = serializers.CharField(source='get_payment_gateway_display', read_only=True)
    payment_method_display = serializers.CharField(read_only=True)
    formatted_amount = serializers.CharField(read_only=True)
    payment_instructions = serializers.SerializerMethodField()
    can_be_refunded = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            # Identification
            'id', 'payment_reference', 'gateway_reference',
            
            # Relationships
            'order', 'user',
            
            # Payment details
            'amount', 'formatted_amount', 'currency',
            'payment_gateway', 'payment_gateway_display',
            'payment_method', 'payment_method_display',
            'status', 'status_display',
            
            # Mobile money details
            'mobile_number', 'mobile_network', 'transaction_code',
            
            # Card details
            'card_last4', 'card_brand',
            
            # Bank details
            'bank_name', 'account_name', 'account_number',
            
            # Cash on delivery
            'cash_collected', 'cash_collected_at', 'cash_collected_by',
            
            # Timestamps
            'created_at', 'updated_at', 'initiated_at',
            'paid_at', 'refunded_at',
            
            # Metadata
            'ip_address', 'user_agent',
            
            # Refund info
            'refund_amount', 'refund_reference', 'refund_reason',
            
            # Baby shop specific
            'is_gift_payment', 'gift_sender_name', 'gift_sender_message',
            
            # Computed fields
            'payment_instructions', 'can_be_refunded'
        ]
        read_only_fields = fields
    
    def get_payment_instructions(self, obj):
        """Get payment instructions - handle both dict and object"""
        try:
            # Handle case where obj might be a dictionary/ReturnDict
            if isinstance(obj, dict):
                status = obj.get('status')
                amount = obj.get('amount')
                payment_gateway = obj.get('payment_gateway')
                payment_reference = obj.get('payment_reference')
            else:
                # Normal Payment object
                status = obj.status
                amount = obj.amount
                payment_gateway = obj.payment_gateway
                payment_reference = obj.payment_reference
            
            if status != 'pending':
                return None
            
            # TODO: Implement actual payment instructions for each gateway
            instructions = {
                'mpesa': f"Send KES {amount} to Paybill 123456, Account {payment_reference}",
                'airtel_money': f"Send KES {amount} to Airtel Money 123456",
                'bank_transfer': f"Transfer KES {amount} to account XYZ",
                'cash_on_delivery': "Pay cash on delivery",
            }
            
            return instructions.get(payment_gateway, "Payment instructions not available")
            
        except Exception as e:
            # Log but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error getting payment instructions: {str(e)}")
            return None


class PaymentListSerializer(serializers.ModelSerializer):
    """Serializer for listing payments"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_gateway_display = serializers.CharField(source='get_payment_gateway_display', read_only=True)
    formatted_amount = serializers.CharField(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_reference', 'order_number',
            'amount', 'formatted_amount', 'currency',
            'payment_gateway', 'payment_gateway_display',
            'status', 'status_display',
            'created_at', 'paid_at'
        ]
        read_only_fields = fields


class PaymentStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating payment status"""
    class Meta:
        model = Payment
        fields = ['status']
    
    def validate_status(self, value):
        """Validate status transition."""
        instance = self.instance
        
        # Only allow specific status transitions
        allowed_transitions = {
            'initiated': ['pending', 'failed', 'cancelled'],
            'pending': ['successful', 'failed', 'cancelled'],
            'successful': ['refunded', 'partially_refunded'],
            'failed': ['pending'],
            'cancelled': [],
            'refunded': [],
            'partially_refunded': ['refunded']
        }
        
        current_status = instance.status
        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                _('Cannot change status from %(current)s to %(new)s.') % {
                    'current': instance.get_status_display(),
                    'new': dict(Payment.PAYMENT_STATUS_CHOICES).get(value, value)
                }
            )
        
        return value


class PaymentRefundSerializer(serializers.Serializer):
    """Serializer for refunding payments"""
    refund_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01
    )
    refund_reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True
    )
    
    def validate(self, data):
        """Validate refund data."""
        payment = self.context.get('payment')
        refund_amount = data.get('refund_amount')
        
        if not payment.can_be_refunded():
            raise serializers.ValidationError({
                'refund_amount': _('This payment cannot be refunded.')
            })
        
        if refund_amount > payment.amount:
            raise serializers.ValidationError({
                'refund_amount': _('Refund amount cannot exceed payment amount.')
            })
        
        return data


# ==================== WEBHOOK SERIALIZERS ====================

class PaymentWebhookSerializer(serializers.ModelSerializer):
    """Serializer for payment webhooks"""
    class Meta:
        model = PaymentWebhook
        fields = [
            'id', 'gateway', 'event_type', 'payload',
            'headers', 'ip_address', 'is_processed',
            'processing_error', 'created_at', 'processed_at'
        ]
        read_only_fields = fields


# ==================== RESPONSE SERIALIZERS ====================

class PaymentInitiationResponseSerializer(serializers.Serializer):
    """Serializer for payment initiation response"""
    payment = PaymentDetailSerializer()
    checkout_url = serializers.URLField(required=False, allow_null=True)
    payment_instructions = serializers.CharField(required=False, allow_null=True)
    success = serializers.BooleanField()
    message = serializers.CharField()


class PaymentVerificationResponseSerializer(serializers.Serializer):
    """Serializer for payment verification response"""
    payment = PaymentDetailSerializer()
    is_verified = serializers.BooleanField()
    verification_message = serializers.CharField()
    success = serializers.BooleanField()
    message = serializers.CharField()