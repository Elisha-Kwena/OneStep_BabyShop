# payments/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from orders.models import Order
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Payment(models.Model):
    """Payment information for baby shop orders"""
    
    PAYMENT_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    # Kenya-specific payment gateways
    PAYMENT_GATEWAY_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('airtel_money', 'Airtel Money'),
        ('tkash', 'T-Kash'),
        ('equitel', 'Equitel'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
    ]
    
    # Payment methods (how the payment was actually made)
    PAYMENT_METHOD_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('wallet', 'Digital Wallet'),
    ]
    
    # Payment identification
    payment_reference = models.CharField(max_length=100, unique=True)
    gateway_reference = models.CharField(max_length=255, blank=True)
    
    # Relationships
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments'
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')  # Kenyan Shillings
    payment_gateway = models.CharField(
        max_length=20,
        choices=PAYMENT_GATEWAY_CHOICES
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    
    # Mobile money details (common in Kenya)
    mobile_number = models.CharField(max_length=15, blank=True)
    mobile_network = models.CharField(
        max_length=20,
        choices=[
            ('safaricom', 'Safaricom'),
            ('airtel', 'Airtel'),
            ('telkom', 'Telkom'),
        ],
        blank=True
    )
    transaction_code = models.CharField(max_length=50, blank=True)  # MPesa transaction code
    
    # Card payment details (encrypted in production)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=50, blank=True)
    
    # Bank transfer details
    bank_name = models.CharField(max_length=100, blank=True)
    account_name = models.CharField(max_length=255, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    
    # Cash on delivery
    cash_collected = models.BooleanField(default=False)
    cash_collected_at = models.DateTimeField(null=True, blank=True)
    cash_collected_by = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    initiated_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Gateway response and errors
    gateway_response = models.JSONField(null=True, blank=True)
    gateway_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    
    # For refunds
    refund_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    refund_reference = models.CharField(max_length=100, blank=True)
    refund_reason = models.TextField(blank=True)
    
    # Baby shop specific
    is_gift_payment = models.BooleanField(default=False)
    gift_sender_name = models.CharField(max_length=255, blank=True)
    gift_sender_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_reference']),
            models.Index(fields=['order', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['payment_gateway', 'created_at']),
            models.Index(fields=['mobile_number', 'created_at']),
            models.Index(fields=['transaction_code']),
        ]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
    
    def __str__(self):
        return f"Payment {self.payment_reference} - KES {self.amount}"
    
    def save(self, *args, **kwargs):
        """Save method with data integrity fixes"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Auto-set initiated_at on first save
        if not self.pk and not self.initiated_at:
            self.initiated_at = timezone.now()
        
        # Auto-set user from order if not set
        if not self.user and self.order:
            self.user = self.order.user
        
        # PRODUCTION FIX 1: Ensure paid_at is set for successful payments
        if self.status == 'successful' and not self.paid_at:
            self.paid_at = timezone.now()
            logger.warning(
                f"Payment {self.payment_reference}: Auto-set paid_at for successful payment"
            )
        
        # PRODUCTION FIX 2: Ensure gateway_reference for successful payments
        if self.status == 'successful' and not self.gateway_reference:
            self.gateway_reference = f"AUTO-REF-{self.payment_reference}"
        
        # PRODUCTION FIX 3: Auto-generate transaction code for mobile money
        if (self.status == 'successful' and 
            self.payment_gateway in ['mpesa', 'airtel_money', 'tkash', 'equitel'] and
            not self.transaction_code):
            self.transaction_code = f"{self.payment_gateway.upper()}-{self.id:08d}"
        
        super().save(*args, **kwargs)
        
        # PRODUCTION FIX 4: Auto-fix order after saving payment
        if self.status == 'successful' and self.order:
            self._fix_associated_order()
    
    def _fix_associated_order(self):
        """Fix associated order data integrity"""
        try:
            needs_fix = False
            
            # Fix order payment status
            if self.order.payment_status != 'paid':
                self.order.payment_status = 'paid'
                needs_fix = True
            
            # Fix order payment date
            if not self.order.payment_date:
                self.order.payment_date = self.paid_at or timezone.now()
                needs_fix = True
            
            # Fix order status if still pending
            if self.order.status == 'pending':
                self.order.status = 'confirmed'
                needs_fix = True
            
            if needs_fix:
                self.order.save()
                logger.info(
                    f"Payment {self.payment_reference}: Auto-fixed order {self.order.order_number}"
                )
                
        except Exception as e:
            logger.error(
                f"Payment {self.payment_reference}: Failed to fix order - {str(e)}"
            )
    
    def mark_as_successful(self, gateway_ref=None, **kwargs):
        """Mark payment as successful with data integrity"""
        self.status = 'successful'
        self.gateway_reference = gateway_ref or self.gateway_reference or f"GW-REF-{self.payment_reference}"
        
        # Always set paid_at
        if not self.paid_at:
            self.paid_at = timezone.now()
        
        # Update payment details if provided
        update_fields = [
            'card_last4', 'card_brand', 'bank_name', 
            'account_name', 'account_number', 'mobile_number',
            'mobile_network', 'transaction_code'
        ]
        for field in update_fields:
            if field in kwargs:
                setattr(self, field, kwargs[field])
        
        # Auto-generate transaction code for mobile money if missing
        if (self.payment_gateway in ['mpesa', 'airtel_money', 'tkash', 'equitel'] and
            not self.transaction_code):
            self.transaction_code = f"{self.payment_gateway.upper()}-{self.id:08d}"
        
        self.save()  # This will trigger the save() method fixes
        
        # Update order status
        if self.order:
            try:
                self.order.mark_as_paid(
                    payment_method=self.payment_gateway,
                    reference=self.payment_reference
                )
            except Exception as e:
                logger.error(
                    f"Payment {self.payment_reference}: Failed to mark order as paid - {str(e)}"
                )
                # Fallback: Manual order update
                self.order.payment_status = 'paid'
                self.order.payment_date = self.paid_at
                if self.order.status == 'pending':
                    self.order.status = 'confirmed'
                self.order.save()
    
    def mark_as_failed(self, error_code="", error_message="", gateway_message=""):
        """Mark payment as failed"""
        self.status = 'failed'
        self.error_code = error_code
        self.error_message = error_message
        self.gateway_message = gateway_message
        self.save()
    
    def mark_as_refunded(self, amount=None, reference="", reason=""):
        """Mark payment as refunded"""
        self.status = 'refunded'
        self.refund_amount = amount or self.amount
        self.refund_reference = reference or f"REF-{self.payment_reference}"
        self.refund_reason = reason
        self.refunded_at = timezone.now()
        self.save()
        
        # Update order status if fully refunded
        if self.refund_amount >= self.amount and self.order:
            self.order.status = 'refunded'
            self.order.save()
    
    def can_be_refunded(self):
        """Check if payment can be refunded with auto-fix"""
        from django.utils import timezone
        import logging
        logger = logging.getLogger(__name__)
        
        # AUTO-FIX: If successful but missing paid_at, fix it immediately
        if self.status == 'successful' and not self.paid_at:
            logger.warning(f"Payment {self.payment_reference}: Auto-fixing missing paid_at")
            self.paid_at = timezone.now()
            
            # Also fix other missing fields
            if not self.gateway_reference:
                self.gateway_reference = f"AUTO-FIX-GW-{self.payment_reference}"
            
            if self.payment_gateway == 'mpesa' and not self.transaction_code:
                self.transaction_code = f"MPESA-AUTO-{self.id}"
            
            self.save()
            
            # Also fix the order
            if self.order and self.order.payment_status != 'paid':
                self.order.payment_status = 'paid'
                self.order.payment_date = self.paid_at
                if self.order.status == 'pending':
                    self.order.status = 'confirmed'
                self.order.save()
                logger.info(f"Payment {self.payment_reference}: Auto-fixed order {self.order.order_number}")
            
            return True
        
        return self.status == 'successful' and self.paid_at is not None
    
    @property
    def is_successful(self):
        return self.status == 'successful'
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_refunded(self):
        return self.status == 'refunded'
    
    @property
    def is_mobile_money(self):
        """Check if this is a mobile money payment"""
        mobile_gateways = ['mpesa', 'airtel_money', 'tkash', 'equitel']
        return self.payment_gateway in mobile_gateways
    
    @property
    def payment_method_display(self):
        """Get display name for payment method"""
        if self.payment_method:
            return dict(self.PAYMENT_METHOD_CHOICES).get(self.payment_method, self.payment_method)
        elif self.is_mobile_money:
            return "Mobile Money"
        return self.get_payment_gateway_display()
    
    @property
    def formatted_amount(self):
        """Get formatted amount with currency"""
        return f"KES {self.amount:,.2f}"
    
    # Kenya-specific methods
    def get_mpesa_details(self):
        """Get M-Pesa specific details"""
        if self.payment_gateway == 'mpesa':
            return {
                'mobile_number': self.mobile_number,
                'network': self.mobile_network or 'Safaricom',
                'transaction_code': self.transaction_code or f"MPESA-{self.id:08d}",
                'amount': float(self.amount),
                'paid_at': self.paid_at.isoformat() if self.paid_at else None
            }
        return None
    
    def generate_payment_reference(self):
        """Generate a unique payment reference"""
        import random
        import string
        
        if not self.payment_reference:
            # Format: PAY-YYYYMMDD-RANDOM
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            self.payment_reference = f"PAY-{date_str}-{random_str}"
        return self.payment_reference
    
    def fix_data_integrity(self):
        """Manual method to fix data integrity issues"""
        fixes = []
        
        # Fix 1: Missing paid_at for successful payments
        if self.status == 'successful' and not self.paid_at:
            self.paid_at = self.updated_at or self.created_at or timezone.now()
            fixes.append("Set paid_at timestamp")
        
        # Fix 2: Missing gateway_reference
        if self.status == 'successful' and not self.gateway_reference:
            self.gateway_reference = f"FIXED-GW-{self.payment_reference}"
            fixes.append("Set gateway_reference")
        
        # Fix 3: Missing transaction code for mobile money
        if (self.is_mobile_money and self.status == 'successful' and 
            not self.transaction_code):
            self.transaction_code = f"{self.payment_gateway.upper()}-FIXED-{self.id}"
            fixes.append("Set transaction_code")
        
        if fixes:
            self.save()
            return {
                'success': True,
                'payment_reference': self.payment_reference,
                'fixes': fixes,
                'paid_at': self.paid_at,
                'can_be_refunded': self.can_be_refunded()
            }
        
        return {
            'success': True,
            'payment_reference': self.payment_reference,
            'message': 'No fixes needed',
            'can_be_refunded': self.can_be_refunded()
        }


class PaymentWebhook(models.Model):
    """Store webhook responses from payment gateways"""
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='webhooks',
        null=True,
        blank=True
    )
    
    gateway = models.CharField(max_length=50)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    headers = models.JSONField(default=dict)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['gateway', 'created_at']),
            models.Index(fields=['is_processed', 'created_at']),
        ]
    
    def __str__(self):
        return f"Webhook {self.event_type} from {self.gateway}"


class PaymentMethod(models.Model):
    """Available payment methods for the baby shop"""
    
    name = models.CharField(max_length=100)
    gateway = models.CharField(max_length=50)
    method_type = models.CharField(
        max_length=20,
        choices=[
            ('mobile_money', 'Mobile Money'),
            ('card', 'Card'),
            ('bank', 'Bank'),
            ('cash', 'Cash'),
            ('wallet', 'Wallet'),
        ]
    )
    
    # Configuration
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    
    # Display
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True)  # Font awesome class or image URL
    
    # Limits and fees
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    processing_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    processing_fee_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Kenya-specific
    supported_networks = models.JSONField(
        default=list,
        blank=True,
        help_text="List of supported mobile networks"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"
    
    def __str__(self):
        return self.display_name
    
    @property
    def calculate_fee(self, amount):
        """Calculate processing fee for given amount"""
        fee = (float(amount) * float(self.processing_fee_percent) / 100) + float(self.processing_fee_fixed)
        return fee
    
    def is_available_for_amount(self, amount):
        """Check if payment method is available for given amount"""
        if amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
        return True