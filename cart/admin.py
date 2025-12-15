from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils import timezone
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    """Inline admin for cart items"""
    model = CartItem
    extra = 0
    readonly_fields = ['unit_price', 'total_price', 'is_available', 'added_at']
    fields = [
        'product', 'variant', 'quantity', 'size', 'color',
        'unit_price', 'total_price', 'is_available'
    ]
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def unit_price(self, obj):
        """Display unit price"""
        return f"KSh {obj.unit_price:,.2f}"
    unit_price.short_description = 'Unit Price'
    
    def total_price(self, obj):
        """Display total price"""
        return f"KSh {obj.total_price:,.2f}"
    total_price.short_description = 'Total'


class ActiveCartFilter(admin.SimpleListFilter):
    """Filter carts by activity"""
    title = 'Cart Activity'
    parameter_name = 'activity'
    
    def lookups(self, request, model_admin):
        return [
            ('active', 'Active (Last 7 days)'),
            ('inactive', 'Inactive (Older than 7 days)'),
            ('abandoned', 'Abandoned (Older than 30 days)'),
        ]
    
    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'active':
            week_ago = now - timezone.timedelta(days=7)
            return queryset.filter(updated_at__gte=week_ago)
        elif self.value() == 'inactive':
            week_ago = now - timezone.timedelta(days=7)
            month_ago = now - timezone.timedelta(days=30)
            return queryset.filter(updated_at__lt=week_ago, updated_at__gte=month_ago)
        elif self.value() == 'abandoned':
            month_ago = now - timezone.timedelta(days=30)
            return queryset.filter(updated_at__lt=month_ago)
        return queryset


class CartItemCountFilter(admin.SimpleListFilter):
    """Filter carts by item count"""
    title = 'Item Count'
    parameter_name = 'item_count'
    
    def lookups(self, request, model_admin):
        return [
            ('empty', 'Empty (0 items)'),
            ('small', 'Small (1-3 items)'),
            ('medium', 'Medium (4-9 items)'),
            ('large', 'Large (10+ items)'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'empty':
            return queryset.filter(items__isnull=True)
        elif self.value() == 'small':
            return queryset.annotate(item_count=models.Count('items')).filter(item_count__range=(1, 3))
        elif self.value() == 'medium':
            return queryset.annotate(item_count=models.Count('items')).filter(item_count__range=(4, 9))
        elif self.value() == 'large':
            return queryset.annotate(item_count=models.Count('items')).filter(item_count__gte=10)
        return queryset


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin configuration for Cart model"""
    list_display = [
        'user_email', 'item_count', 'unique_items', 'cart_subtotal',
        'activity_status', 'created_date', 'last_updated'
    ]
    list_filter = [ActiveCartFilter, CartItemCountFilter, 'created_at']
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'items__product__name'
    ]
    readonly_fields = [
        'user_email', 'created_at', 'updated_at', 'total_items',
        'unique_items_count', 'subtotal_display', 'estimated_total_display',
        'age_ranges_list', 'genders_list', 'has_gift_items_status',
        'activity_indicator'
    ]
    fieldsets = (
        ('Cart Information', {
            'fields': (
                'user', 'user_email', 'created_at', 'updated_at',
                'activity_indicator'
            )
        }),
        ('Cart Statistics', {
            'fields': (
                'total_items', 'unique_items_count', 'subtotal_display',
                'estimated_total_display'
            )
        }),
        ('Baby Shop Insights', {
            'fields': (
                'age_ranges_list', 'genders_list', 'has_gift_items_status'
            ),
            'classes': ('collapse',)
        }),
    )
    inlines = [CartItemInline]
    actions = ['clear_carts', 'export_carts_summary']
    list_per_page = 30
    
    def user_email(self, obj):
        """Display user email with link"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = obj.user
        url = f'/admin/{User._meta.app_label}/{User._meta.model_name}/{user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, user.email)
    user_email.short_description = 'Customer'
    user_email.admin_order_field = 'user__email'
    
    def item_count(self, obj):
        """Display total item count with badge"""
        count = obj.total_items
        color = 'green' if count > 0 else 'gray'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, count
        )
    item_count.short_description = 'Items'
    
    def unique_items(self, obj):
        """Display unique item count"""
        return obj.unique_items_count
    unique_items.short_description = 'Unique Items'
    
    def cart_subtotal(self, obj):
        """Display cart subtotal"""
        if obj.subtotal > 0:
            return f"KSh {obj.subtotal:,.2f}"
        return "KSh 0.00"
    cart_subtotal.short_description = 'Subtotal'
    cart_subtotal.admin_order_field = 'subtotal'
    
    def activity_status(self, obj):
        """Display activity status with colored indicator"""
        now = timezone.now()
        days_since_update = (now - obj.updated_at).days
        
        if days_since_update < 1:
            color = 'green'
            status = 'Today'
        elif days_since_update < 3:
            color = 'orange'
            status = f'{days_since_update}d ago'
        elif days_since_update < 7:
            color = 'red'
            status = f'{days_since_update}d ago'
        else:
            color = 'gray'
            status = f'{days_since_update}d ago'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, status
        )
    activity_status.short_description = 'Activity'
    activity_status.admin_order_field = 'updated_at'
    
    def created_date(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%b %d, %Y')
    created_date.short_description = 'Created'
    created_date.admin_order_field = 'created_at'
    
    def last_updated(self, obj):
        """Format last updated date"""
        return obj.updated_at.strftime('%b %d, %Y')
    last_updated.short_description = 'Last Updated'
    
    # Read-only field methods
    def subtotal_display(self, obj):
        """Display subtotal in read-only field"""
        return f"KSh {obj.subtotal:,.2f}"
    subtotal_display.short_description = 'Cart Subtotal'
    
    def estimated_total_display(self, obj):
        """Display estimated total in read-only field"""
        return f"KSh {obj.estimated_total:,.2f}"
    estimated_total_display.short_description = 'Estimated Total'
    
    def age_ranges_list(self, obj):
        """Display age ranges in cart"""
        age_ranges = obj.get_age_ranges_in_cart()
        if age_ranges:
            return format_html(
                '<ul style="margin: 0; padding-left: 20px;">{}</ul>',
                ''.join(f'<li>{age}</li>' for age in age_ranges)
            )
        return 'No age-specific items'
    age_ranges_list.short_description = 'Age Ranges in Cart'
    
    def genders_list(self, obj):
        """Display genders in cart"""
        genders = obj.get_genders_in_cart()
        if genders:
            badges = []
            for gender in genders:
                color = 'blue' if 'boy' in gender.lower() else 'pink' if 'girl' in gender.lower() else 'purple'
                badges.append(
                    f'<span style="background-color: {color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px; margin-right: 5px;">{gender}</span>'
                )
            return format_html(' '.join(badges))
        return 'No gender-specific items'
    genders_list.short_description = 'Genders in Cart'
    
    def has_gift_items_status(self, obj):
        """Display gift item status"""
        return obj.has_gift_items()
    has_gift_items_status.boolean = True
    has_gift_items_status.short_description = 'Has Gift Items?'
    
    def activity_indicator(self, obj):
        """Display activity indicator"""
        now = timezone.now()
        days_since_update = (now - obj.updated_at).days
        
        if days_since_update == 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active Today</span>'
            )
        elif days_since_update < 3:
            return format_html(
                '<span style="color: orange; font-weight: bold;">↻ Active Recently</span>'
            )
        elif days_since_update < 7:
            return format_html(
                '<span style="color: #ff6b6b; font-weight: bold;">⚠ Inactive</span>'
            )
        else:
            return format_html(
                '<span style="color: gray; font-weight: bold;">✗ Abandoned</span>'
            )
    activity_indicator.short_description = 'Activity Status'
    
    # Admin Actions
    def clear_carts(self, request, queryset):
        """Clear all items from selected carts"""
        for cart in queryset:
            cart.clear()
        self.message_user(request, f"{queryset.count()} carts cleared successfully.")
    clear_carts.short_description = "Clear selected carts"
    
    def export_carts_summary(self, request, queryset):
        """Export cart summary to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="carts_summary.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Customer Email', 'Total Items', 'Unique Items', 'Subtotal',
            'Last Updated', 'Age Ranges', 'Genders', 'Has Gift Items'
        ])
        
        for cart in queryset:
            writer.writerow([
                cart.user.email,
                cart.total_items,
                cart.unique_items_count,
                float(cart.subtotal),
                cart.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                ', '.join(cart.get_age_ranges_in_cart()),
                ', '.join(cart.get_genders_in_cart()),
                'Yes' if cart.has_gift_items() else 'No'
            ])
        
        return response
    export_carts_summary.short_description = "Export selected carts to CSV"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Admin configuration for CartItem model"""
    list_display = [
        'product_with_variant', 'customer_email', 'cart_activity',
        'quantity_badge', 'unit_price', 'total_price', 'availability_status_badge',
        'added_date'
    ]
    list_filter = ['added_at', 'product__category']
    search_fields = [
        'cart__user__email', 'product__name', 'product__product_code',
        'variant__product_code', 'size', 'color'
    ]
    readonly_fields = [
        'unit_price', 'total_price', 'product_name', 'product_image_display',
        'is_available', 'availability_status', 'product_gender',
        'product_age_range', 'is_gift_suitable_display', 'added_at', 'updated_at'
    ]
    fieldsets = (
        ('Cart & Customer', {
            'fields': ('cart', 'customer_email')
        }),
        ('Product Details', {
            'fields': (
                'product', 'variant', 'product_name', 'product_image_display',
                'size', 'color'
            )
        }),
        ('Quantity & Pricing', {
            'fields': ('quantity', 'unit_price', 'total_price')
        }),
        ('Availability', {
            'fields': ('is_available', 'availability_status'),
            'classes': ('collapse',)
        }),
        ('Baby Shop Details', {
            'fields': ('product_gender', 'product_age_range', 'is_gift_suitable_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('added_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['increase_quantity', 'decrease_quantity', 'check_availability']
    list_per_page = 50
    
    def product_with_variant(self, obj):
        """Display product name with variant info"""
        if obj.variant:
            return f"{obj.product.name} ({obj.variant.size}/{obj.variant.color})"
        elif obj.size or obj.color:
            parts = []
            if obj.size:
                parts.append(obj.size)
            if obj.color:
                parts.append(obj.color)
            if parts:
                return f"{obj.product.name} ({'/'.join(parts)})"
        return obj.product.name
    product_with_variant.short_description = 'Product'
    product_with_variant.admin_order_field = 'product__name'
    
    def customer_email(self, obj):
        """Display customer email"""
        return obj.cart.user.email
    customer_email.short_description = 'Customer'
    customer_email.admin_order_field = 'cart__user__email'
    
    def cart_activity(self, obj):
        """Display cart activity indicator"""
        now = timezone.now()
        days_since_update = (now - obj.cart.updated_at).days
        
        if days_since_update < 1:
            color = 'green'
            text = 'Active'
        elif days_since_update < 3:
            color = 'orange'
            text = 'Recent'
        else:
            color = 'gray'
            text = 'Old'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, text
        )
    cart_activity.short_description = 'Cart Activity'
    
    def quantity_badge(self, obj):
        """Display quantity with colored badge"""
        color = 'blue' if obj.quantity == 1 else 'green' if obj.quantity <= 3 else 'orange'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            color, obj.quantity
        )
    quantity_badge.short_description = 'Qty'
    
    def unit_price(self, obj):
        """Display unit price"""
        return f"KSh {obj.unit_price:,.2f}"
    unit_price.short_description = 'Unit Price'
    unit_price.admin_order_field = 'unit_price'
    
    def total_price(self, obj):
        """Display total price"""
        return f"KSh {obj.total_price:,.2f}"
    total_price.short_description = 'Total'
    total_price.admin_order_field = 'total_price'
    
    def availability_status_badge(self, obj):
        """Display availability status with badge"""
        status = obj.availability_status
        colors = {
            'in_stock': 'green',
            'low_stock': 'orange',
            'out_of_stock': 'red',
        }
        color = colors.get(status, 'gray')
        
        status_text = status.replace('_', ' ').title()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, status_text
        )
    availability_status_badge.short_description = 'Availability'
    
    def added_date(self, obj):
        """Format added date"""
        return obj.added_at.strftime('%b %d')
    added_date.short_description = 'Added'
    added_date.admin_order_field = 'added_at'
    
    # Read-only field methods
    def product_name(self, obj):
        """Display product name in read-only field"""
        return obj.product_name
    
    def product_image_display(self, obj):
        """Display product image in admin"""
        if obj.product_image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.product_image.url
            )
        return 'No image'
    product_image_display.short_description = 'Product Image'
    
    def is_gift_suitable_display(self, obj):
        """Display gift suitability"""
        return obj.is_gift_suitable
    is_gift_suitable_display.boolean = True
    is_gift_suitable_display.short_description = 'Gift Suitable?'
    
    # Admin Actions
    def increase_quantity(self, request, queryset):
        """Increase quantity by 1 for selected items"""
        for item in queryset:
            item.increase_quantity(1)
        self.message_user(request, f"Quantity increased for {queryset.count()} items.")
    increase_quantity.short_description = "Increase quantity by 1"
    
    def decrease_quantity(self, request, queryset):
        """Decrease quantity by 1 for selected items"""
        for item in queryset:
            item.decrease_quantity(1)
        self.message_user(request, f"Quantity decreased for {queryset.count()} items.")
    decrease_quantity.short_description = "Decrease quantity by 1"
    
    def check_availability(self, request, queryset):
        """Check and update availability status"""
        updated = 0
        for item in queryset:
            # Trigger save to update availability status
            item.save()
            updated += 1
        self.message_user(request, f"Availability checked for {updated} items.")
    check_availability.short_description = "Check availability"


