from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items"""
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'unit_price', 'total_price', 'created_at']
    fields = [
        'product', 'variant', 'product_name', 'quantity', 
        'size', 'color', 'unit_price', 'total_price'
    ]
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class PaymentStatusFilter(admin.SimpleListFilter):
    """Filter orders by payment status"""
    title = 'Payment Status'
    parameter_name = 'payment_status'
    
    def lookups(self, request, model_admin):
        return Order.PAYMENT_STATUS_CHOICES
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_status=self.value())
        return queryset


class ShippingMethodFilter(admin.SimpleListFilter):
    """Filter orders by shipping method"""
    title = 'Shipping Method'
    parameter_name = 'shipping_method'
    
    def lookups(self, request, model_admin):
        return Order.SHIPPING_METHOD_CHOICES
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(shipping_method=self.value())
        return queryset


class CountyFilter(admin.SimpleListFilter):
    """Filter orders by county (Kenya specific)"""
    title = 'County'
    parameter_name = 'county'
    
    def lookups(self, request, model_admin):
        # Get distinct counties from the database
        counties = Order.objects.values_list('shipping_county', flat=True).distinct()
        return [(county, county) for county in counties if county]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(shipping_county=self.value())
        return queryset


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for Order model"""
    list_display = [
        'order_number', 'customer_email', 'status_badge', 'payment_status_badge',
        'total_amount', 'item_count', 'shipping_county', 'created_at',
        'estimated_delivery'
    ]
    list_filter = [
        'status', PaymentStatusFilter, ShippingMethodFilter, 
        CountyFilter, 'created_at', 'shipping_method'
    ]
    search_fields = [
        'order_number', 'user__email', 'user__first_name', 'user__last_name',
        'shipping_contact_name', 'shipping_contact_phone',
        'payment_reference', 'shipping_tracking_number'
    ]
    readonly_fields = [
        'order_number', 'created_at', 'updated_at', 'confirmed_at', 
        'processed_at', 'shipped_at', 'delivered_at', 'cancelled_at',
        'customer_name', 'customer_email', 'item_count',
        'shipping_address', 'billing_address', 'estimated_delivery_date',
        'can_be_cancelled', 'is_nairobi_order_display'
    ]
    fieldsets = (
        ('Order Information', {
            'fields': (
                'order_number', 'user', 'customer_name', 'customer_email',
                'status', 'payment_status', 'created_at'
            )
        }),
        ('Payment Details', {
            'fields': (
                'payment_method', 'payment_reference', 'payment_date',
                'subtotal', 'shipping_cost', 'tax_amount', 
                'discount_amount', 'gift_wrapping_fee', 'total_amount'
            ),
            'classes': ('collapse',)
        }),
        ('Shipping Information', {
            'fields': (
                'shipping_method', 'shipping_tracking_number', 'shipping_carrier',
                'shipping_contact_name', 'shipping_contact_phone',
                'shipping_address_line1', 'shipping_address_line2',
                'shipping_city', 'shipping_county', 'shipping_postal_code',
                'shipping_country', 'shipping_address_ref'
            )
        }),
        ('Billing Information', {
            'fields': (
                'billing_same_as_shipping',
                'billing_contact_name', 'billing_contact_phone',
                'billing_address_line1', 'billing_address_line2',
                'billing_city', 'billing_county', 'billing_postal_code',
                'billing_country', 'billing_address_ref'
            ),
            'classes': ('collapse',)
        }),
        ('Customer Preferences', {
            'fields': ('customer_notes', 'gift_message', 'gift_wrapping'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'confirmed_at', 'processed_at', 'shipped_at', 
                'delivered_at', 'cancelled_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Computed Fields', {
            'fields': (
                'item_count', 'shipping_address', 'billing_address',
                'estimated_delivery_date', 'can_be_cancelled', 
                'is_nairobi_order_display'
            ),
            'classes': ('collapse',)
        }),
    )
    inlines = [OrderItemInline]
    actions = [
        'mark_as_confirmed', 'mark_as_processing', 'mark_as_shipped',
        'mark_as_delivered', 'mark_as_cancelled', 'mark_as_refunded',
        'export_orders_csv'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'pending': 'gray',
            'confirmed': 'blue',
            'processing': 'orange',
            'shipped': 'purple',
            'delivered': 'green',
            'cancelled': 'red',
            'refunded': 'yellow',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def payment_status_badge(self, obj):
        """Display payment status with colored badge"""
        colors = {
            'pending': 'gray',
            'authorized': 'blue',
            'paid': 'green',
            'partially_paid': 'orange',
            'refunded': 'yellow',
            'failed': 'red',
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Payment'
    
    def estimated_delivery(self, obj):
        """Display estimated delivery date"""
        if obj.status in ['shipped', 'delivered']:
            return obj.delivered_at or 'In Transit'
        
        days = obj.estimated_delivery_days()
        if days:
            delivery_date = timezone.now() + timedelta(days=days)
            return delivery_date.strftime('%b %d, %Y')
        return 'N/A'
    estimated_delivery.short_description = 'Est. Delivery'
    
    def customer_email(self, obj):
        """Display customer email"""
        return obj.user.email if obj.user else 'Guest'
    customer_email.short_description = 'Customer Email'
    
    def shipping_address(self, obj):
        """Display formatted shipping address"""
        return format_html(obj.shipping_address.replace('\n', '<br>'))
    shipping_address.short_description = 'Shipping Address'
    
    def billing_address(self, obj):
        """Display formatted billing address"""
        return format_html(obj.billing_address.replace('\n', '<br>'))
    billing_address.short_description = 'Billing Address'
    
    def estimated_delivery_date(self, obj):
        """Display estimated delivery date in admin"""
        if obj.status in ['shipped', 'delivered']:
            return obj.delivered_at or 'In Transit'
        
        days = obj.estimated_delivery_days()
        if days:
            if obj.shipped_at:
                delivery_date = obj.shipped_at + timedelta(days=days)
            else:
                delivery_date = timezone.now() + timedelta(days=days)
            return delivery_date.strftime('%Y-%m-%d')
        return 'N/A'
    
    def can_be_cancelled(self, obj):
        """Display if order can be cancelled"""
        return obj.can_be_cancelled()
    can_be_cancelled.boolean = True
    can_be_cancelled.short_description = 'Can Cancel?'
    
    def is_nairobi_order_display(self, obj):
        """Display if order is within Nairobi"""
        return obj.is_nairobi_order()
    is_nairobi_order_display.boolean = True
    is_nairobi_order_display.short_description = 'Nairobi Order?'
    
    # Admin Actions
    def mark_as_confirmed(self, request, queryset):
        """Mark selected orders as confirmed"""
        count = queryset.update(
            status='confirmed',
            confirmed_at=timezone.now()
        )
        self.message_user(request, f"{count} orders marked as confirmed.")
    mark_as_confirmed.short_description = "Mark selected orders as confirmed"
    
    def mark_as_processing(self, request, queryset):
        """Mark selected orders as processing"""
        count = queryset.update(
            status='processing',
            processed_at=timezone.now()
        )
        self.message_user(request, f"{count} orders marked as processing.")
    mark_as_processing.short_description = "Mark selected orders as processing"
    
    def mark_as_shipped(self, request, queryset):
        """Mark selected orders as shipped"""
        count = queryset.update(
            status='shipped',
            shipped_at=timezone.now()
        )
        self.message_user(request, f"{count} orders marked as shipped.")
    mark_as_shipped.short_description = "Mark selected orders as shipped"
    
    def mark_as_delivered(self, request, queryset):
        """Mark selected orders as delivered"""
        count = queryset.update(
            status='delivered',
            delivered_at=timezone.now()
        )
        self.message_user(request, f"{count} orders marked as delivered.")
    mark_as_delivered.short_description = "Mark selected orders as delivered"
    
    def mark_as_cancelled(self, request, queryset):
        """Mark selected orders as cancelled"""
        count = queryset.update(
            status='cancelled',
            cancelled_at=timezone.now()
        )
        self.message_user(request, f"{count} orders marked as cancelled.")
    mark_as_cancelled.short_description = "Mark selected orders as cancelled"
    
    def mark_as_refunded(self, request, queryset):
        """Mark selected orders as refunded"""
        count = queryset.update(
            status='refunded',
            payment_status='refunded'
        )
        self.message_user(request, f"{count} orders marked as refunded.")
    mark_as_refunded.short_description = "Mark selected orders as refunded"
    
    def export_orders_csv(self, request, queryset):
        """Export selected orders to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Order Number', 'Customer Email', 'Status', 'Payment Status',
            'Total Amount', 'Shipping County', 'Created At', 'Items Count'
        ])
        
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.user.email if order.user else 'Guest',
                order.get_status_display(),
                order.get_payment_status_display(),
                order.total_amount,
                order.shipping_county,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.item_count
            ])
        
        return response
    export_orders_csv.short_description = "Export selected orders to CSV"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin configuration for OrderItem model"""
    list_display = [
        'order_number', 'product_name', 'quantity', 'unit_price', 
        'total_price', 'size', 'color', 'created_at'
    ]
    list_filter = ['order__status', 'created_at', 'gender', 'age_range']
    search_fields = [
        'order__order_number', 'product_name', 'product_code',
        'order__user__email'
    ]
    readonly_fields = [
        'order_number', 'product_name', 'product_code', 'unit_price',
        'total_price', 'created_at', 'updated_at', 'current_stock'
    ]
    fieldsets = (
        ('Order Information', {
            'fields': ('order', 'order_number')
        }),
        ('Product Details', {
            'fields': (
                'product', 'variant', 'product_name', 'product_code',
                'size', 'color', 'color_code'
            )
        }),
        ('Baby Details', {
            'fields': ('gender', 'age_range'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('unit_price', 'quantity', 'total_price')
        }),
        ('Stock Information', {
            'fields': ('current_stock',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    list_per_page = 50
    
    def order_number(self, obj):
        """Display order number"""
        return obj.order.order_number
    order_number.short_description = 'Order Number'
    
    def current_stock(self, obj):
        """Display current stock"""
        return obj.current_stock
    current_stock.short_description = 'Current Stock'

