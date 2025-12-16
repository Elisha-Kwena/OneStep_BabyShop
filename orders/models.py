from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth import get_user_model

import random
import string

User = get_user_model()

class Order(models.Model):
    """main order model"""
    ORDER_STATUS_CHOICES = [
        ('draft', 'Draft'),  # Cart stage
        ('pending', 'Pending'),  # Created but not paid
        ('confirmed', 'Confirmed'),  # Payment successful
        ('processing', 'Processing'),  # Preparing for shipment
        ('shipped', 'Shipped'),  # Sent to customer
        ('delivered', 'Delivered'),  # Received by customer
        ('cancelled', 'Cancelled'),  # Order cancelled
        ('refunded', 'Refunded'),  # Refund processed
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('authorized', 'Authorized'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Payment Failed'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('mobile_payment', 'Mobile Payment'),
        ('mpesa', 'M-Pesa'),  
    ]
    SHIPPING_METHOD_CHOICES = [
        ('store_pickup', 'Store Pickup'),
        ('nairobi_only', 'Nairobi Delivery'),
        ('other_towns', 'Other Towns Delivery'),
    ]
    
    # order identification
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="orders")

    # order status
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="pending")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")

    # payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    # shipping details
    shipping_method = models.CharField(max_length=25, choices=SHIPPING_METHOD_CHOICES, default="standard")
    shipping_tracking_number = models.CharField(max_length=100, blank=True)
    shipping_carrier = models.CharField(max_length=50, blank=True)

    # pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Customer notes (useful for baby shop gifts)
    customer_notes = models.TextField(blank=True)
    gift_message = models.TextField(blank=True)
    gift_wrapping = models.BooleanField(default=False)
    gift_wrapping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Shipping address (simplified - Kenya specific)
    shipping_contact_name = models.CharField(max_length=255)
    shipping_contact_phone = models.CharField(max_length=20)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_county = models.CharField(max_length=100)  # Kenya uses counties
    shipping_postal_code = models.CharField(max_length=20, blank=True)
    shipping_country = models.CharField(max_length=100, default='Kenya')

    # Billing address (simplified)
    billing_same_as_shipping = models.BooleanField(default=True)
    billing_contact_name = models.CharField(max_length=255, blank=True)
    billing_contact_phone = models.CharField(max_length=20, blank=True)
    billing_address_line1 = models.CharField(max_length=255, blank=True)
    billing_address_line2 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_county = models.CharField(max_length=100, blank=True)
    billing_postal_code = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=100, blank=True)

    # Optional reference to saved address
    shipping_address_ref = models.ForeignKey(
        'users.UserAddress',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shipping_orders'
    )
    billing_address_ref = models.ForeignKey(
        'users.UserAddress',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_orders'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['payment_status', 'created_at']),
            models.Index(fields=['shipping_county', 'created_at']),
        ]
    
    def __str__(self):
        return f"Order #{self.order_number} - {self.user.email if self.user else 'No User'}"
    
    @property
    def customer_name(self):
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}".strip()
        return "No User"
    
    @property
    def customer_email(self):
        return self.user.email if self.user else None
    
    @property
    def item_count(self):
        return self.items.count()
    
    @property
    def shipping_address(self):
        """Format shipping address for Kenya"""
        address_parts = [
            self.shipping_contact_name,
            self.shipping_contact_phone,
            self.shipping_address_line1,
            self.shipping_address_line2,
            f"{self.shipping_city}, {self.shipping_county} County",
            self.shipping_postal_code,
            self.shipping_country,
        ]
        return "\n".join(filter(None, address_parts))
    
    @property
    def billing_address(self):
        """Format billing address"""
        if self.billing_same_as_shipping:
            return self.shipping_address
        
        address_parts = [
            self.billing_contact_name,
            self.billing_contact_phone,
            self.billing_address_line1,
            self.billing_address_line2,
            f"{self.billing_city}, {self.billing_county} County" if self.billing_city and self.billing_county else "",
            self.billing_postal_code,
            self.billing_country,
        ]
        return "\n".join(filter(None, address_parts))
    
    def generate_order_number(self):
        """Generate a unique order number with Kenya context"""
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"BABY-{date_str}-{random_str}"  # BABY prefix for baby shop
    
    def calculate_totals(self):
        """Calculate order totals from order items"""
        if not self.pk:  # If order not saved yet
            return
            
        items = self.items.all()
        subtotal = sum(item.total_price for item in items)
        
        self.subtotal = subtotal
        self.total_amount = subtotal + self.shipping_cost + self.tax_amount + self.gift_wrapping_fee - self.discount_amount
    
    def populate_from_user_address(self, address, address_type='shipping'):
        """Populate address fields from a UserAddress instance"""
        if address_type == 'shipping':
            self.shipping_contact_name = address.contact_name
            self.shipping_contact_phone = address.contact_phone
            self.shipping_address_line1 = address.address_line_1
            self.shipping_address_line2 = address.address_line_2
            self.shipping_city = address.city
            self.shipping_county = address.county # Assuming state stores county in Kenya
            self.shipping_postal_code = address.postal_code
            self.shipping_country = address.country
            self.shipping_address_ref = address
        elif address_type == 'billing':
            self.billing_contact_name = address.contact_name
            self.billing_contact_phone = address.contact_phone
            self.billing_address_line1 = address.address_line_1
            self.billing_address_line2 = address.address_line_2
            self.billing_city = address.city
            self.billing_county = address.county
            self.billing_postal_code = address.postal_code
            self.billing_country = address.country
            self.billing_address_ref = address  
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Update totals if needed
        if self.pk:
            self.calculate_totals()
        
        # Copy shipping address to billing if same
        if self.billing_same_as_shipping and self.pk:
            self.billing_contact_name = self.shipping_contact_name
            self.billing_contact_phone = self.shipping_contact_phone
            self.billing_address_line1 = self.shipping_address_line1
            self.billing_address_line2 = self.shipping_address_line2
            self.billing_city = self.shipping_city
            self.billing_county = self.shipping_county
            self.billing_postal_code = self.shipping_postal_code
            self.billing_country = self.shipping_country
            self.billing_address_ref = self.shipping_address_ref
        
        # Update timestamps based on status changes
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        elif self.status == 'processing' and not self.processed_at:
            self.processed_at = timezone.now()
        elif self.status == 'shipped' and not self.shipped_at:
            self.shipped_at = timezone.now()
        elif self.status == 'delivered' and not self.delivered_at:
            self.delivered_at = timezone.now()
        elif self.status == 'cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        cancellable_statuses = ['pending', 'confirmed', 'processing']
        return self.status in cancellable_statuses
    
    def mark_as_paid(self, payment_method, reference):
        """Mark order as paid"""
        self.payment_status = 'paid'
        self.payment_method = payment_method
        self.payment_reference = reference
        self.payment_date = timezone.now()
        self.status = 'confirmed'
        self.save()
    
    # Kenya-specific helper methods
    def is_nairobi_order(self):
        """Check if order is within Nairobi (for delivery pricing)"""
        nairobi_counties = ['nairobi', 'nairobi county', 'nairobi city']
        return self.shipping_county.lower() in nairobi_counties
    
    def estimated_delivery_days(self):
        """Get estimated delivery days for Kenya"""
        if self.shipping_method == 'nairobi_only':
            return 1 if self.is_nairobi_order() else None
        elif self.shipping_method == 'other_towns':
            return 3 if not self.is_nairobi_order() else None
        elif self.shipping_method == 'next_day':
            return 1
        elif self.shipping_method == 'express':
            return 2
        elif self.shipping_method == 'standard':
            return 5
        return 7
    
    def get_mpesa_payment_details(self):
        """Get M-Pesa specific payment details"""
        if self.payment_method == 'mpesa':
            return {
                'reference': self.payment_reference,
                'phone': self.user.phone if self.user else '',
                'amount': float(self.total_amount)
            }
        return None
    


class OrderItem(models.Model):
    """Individual items within an order"""
    
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product', 
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    variant = models.ForeignKey(
        'products.ProductVariant', 
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    # Product details at time of purchase (denormalized)
    product_name = models.CharField(max_length=255)
    product_code = models.CharField(max_length=100)
    size = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=50, blank=True)
    color_code = models.CharField(max_length=7, blank=True)
    
    # Pricing
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        editable=False
    )
    
    # Baby-specific details preserved
    gender = models.CharField(max_length=20, blank=True)
    age_range = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order', 'product']),
            models.Index(fields=['product_code']),
        ]
    
    def __str__(self):
        return f"{self.quantity} x {self.product_name} (Order #{self.order.order_number})"
    
    @property
    def current_stock(self):
        """Get current stock of the variant or product"""
        if self.variant:
            return self.variant.stock_quantity
        return self.product.stock_quantity
    
    def save(self, *args, **kwargs):
        # Capture product details at time of order
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_code:
            if self.variant:
                self.product_code = self.variant.product_code
            else:
                self.product_code = self.product.product_code
        
        # Capture variant details
        if self.variant:
            if not self.size:
                self.size = self.variant.size
            if not self.color:
                self.color = self.variant.color
            if not self.color_code:
                self.color_code = self.variant.color_code
        
        # Capture baby-specific details
        if not self.gender:
            self.gender = self.product.gender
        if not self.age_range:
            self.age_range = self.product.age_range
        
        # Calculate total price
        self.total_price = self.unit_price * self.quantity
        
        super().save(*args, **kwargs)
        
        # Update order totals after saving item
        if self.order:
            self.order.calculate_totals()
            self.order.save()