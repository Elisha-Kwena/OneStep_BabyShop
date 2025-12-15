from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Payment, PaymentWebhook, PaymentMethod


class PaymentWebhookInline(admin.TabularInline):
    """Inline admin for payment webhooks"""
    model = PaymentWebhook
    extra = 0
    readonly_fields = ['gateway', 'event_type', 'is_processed', 'created_at']
    fields = ['gateway', 'event_type', 'is_processed', 'created_at']
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False


class PaymentStatusFilter(admin.SimpleListFilter):
    """Filter payments by status"""
    title = 'Payment Status'
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        return Payment.PAYMENT_STATUS_CHOICES
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class PaymentGatewayFilter(admin.SimpleListFilter):
    """Filter payments by gateway"""
    title = 'Payment Gateway'
    parameter_name = 'gateway'
    
    def lookups(self, request, model_admin):
        return Payment.PAYMENT_GATEWAY_CHOICES
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_gateway=self.value())
        return queryset


class MobileMoneyFilter(admin.SimpleListFilter):
    """Filter mobile money payments"""
    title = 'Mobile Money'
    parameter_name = 'mobile_money'
    
    def lookups(self, request, model_admin):
        return [
            ('mpesa', 'M-Pesa'),
            ('airtel_money', 'Airtel Money'),
            ('tkash', 'T-Kash'),
            ('equitel', 'Equitel'),
        ]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_gateway=self.value())
        return queryset


class RefundFilter(admin.SimpleListFilter):
    """Filter payments by refund status"""
    title = 'Refund Status'
    parameter_name = 'refund'
    
    def lookups(self, request, model_admin):
        return [
            ('refunded', 'Refunded'),
            ('not_refunded', 'Not Refunded'),
            ('partially_refunded', 'Partially Refunded'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'refunded':
            return queryset.filter(status='refunded')
        elif self.value() == 'not_refunded':
            return queryset.exclude(status__in=['refunded', 'partially_refunded'])
        elif self.value() == 'partially_refunded':
            return queryset.filter(status='partially_refunded')
        return queryset


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for Payment model"""
    list_display = [
        'payment_reference', 'order_link', 'customer_email', 'amount_display',
        'status_badge', 'gateway_badge', 'payment_method_display',
        'mobile_number_display', 'created_date', 'is_gift_indicator'
    ]
    list_filter = [
        PaymentStatusFilter, PaymentGatewayFilter, MobileMoneyFilter,
        RefundFilter, 'is_gift_payment', 'created_at'
    ]
    search_fields = [
        'payment_reference', 'gateway_reference', 'order__order_number',
        'user__email', 'user__first_name', 'user__last_name',
        'mobile_number', 'transaction_code', 'card_last4'
    ]
    readonly_fields = [
        'payment_reference', 'order_link', 'user_link', 'amount_display',
        'formatted_amount', 'is_successful', 'is_pending', 'is_refunded',
        'can_be_refunded', 'is_mobile_money', 'mpesa_details_display',
        'created_at', 'updated_at', 'initiated_at', 'paid_at', 'refunded_at',
        'cash_collected_details'
    ]
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'payment_reference', 'gateway_reference', 'order_link', 'user_link',
                'amount_display', 'currency', 'formatted_amount'
            )
        }),
        ('Payment Status', {
            'fields': (
                'status', 'payment_gateway', 'payment_method',
                'is_successful', 'is_pending', 'is_refunded', 'can_be_refunded'
            )
        }),
        ('Mobile Money Details (Kenya)', {
            'fields': (
                'mobile_number', 'mobile_network', 'transaction_code',
                'is_mobile_money', 'mpesa_details_display'
            ),
            'classes': ('collapse',)
        }),
        ('Card Payment Details', {
            'fields': ('card_last4', 'card_brand'),
            'classes': ('collapse',)
        }),
        ('Bank Transfer Details', {
            'fields': ('bank_name', 'account_name', 'account_number'),
            'classes': ('collapse',)
        }),
        ('Cash on Delivery', {
            'fields': (
                'cash_collected', 'cash_collected_at', 'cash_collected_by',
                'cash_collected_details'
            ),
            'classes': ('collapse',)
        }),
        ('Refund Information', {
            'fields': (
                'refund_amount', 'refund_reference', 'refund_reason',
                'refunded_at'
            ),
            'classes': ('collapse',)
        }),
        ('Baby Shop Gift Details', {
            'fields': (
                'is_gift_payment', 'gift_sender_name', 'gift_sender_message'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'initiated_at', 'paid_at'
            ),
            'classes': ('collapse',)
        }),
        ('Technical Details', {
            'fields': (
                'ip_address', 'user_agent', 'gateway_response',
                'gateway_message', 'error_code', 'error_message'
            ),
            'classes': ('collapse',)
        }),
    )
    inlines = [PaymentWebhookInline]
    actions = [
        'mark_as_successful', 'mark_as_failed', 'mark_as_refunded',
        'mark_as_cash_collected', 'export_payments_csv'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    def order_link(self, obj):
        """Display order number with link"""
        if obj.order:
            url = f'/admin/orders/order/{obj.order.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return 'No Order'
    order_link.short_description = 'Order'
    order_link.admin_order_field = 'order__order_number'
    
    def user_link(self, obj):
        """Display user with link"""
        if obj.user:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            url = f'/admin/{User._meta.app_label}/{User._meta.model_name}/{obj.user.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return 'No User'
    user_link.short_description = 'Customer'
    user_link.admin_order_field = 'user__email'
    
    def customer_email(self, obj):
        """Display customer email"""
        if obj.user:
            return obj.user.email
        elif obj.order and obj.order.user:
            return obj.order.user.email
        return 'Guest'
    customer_email.short_description = 'Customer Email'
    
    def amount_display(self, obj):
        """Display amount with currency"""
        return obj.formatted_amount
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'successful': 'green',
            'pending': 'orange',
            'initiated': 'blue',
            'failed': 'red',
            'cancelled': 'gray',
            'refunded': 'yellow',
            'partially_refunded': 'lightblue',
        }
        color = colors.get(obj.status, 'gray')
        status_text = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">{}</span>',
            color, status_text
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def gateway_badge(self, obj):
        """Display payment gateway with badge"""
        colors = {
            'mpesa': '#FF6900',  # M-Pesa orange
            'airtel_money': '#CE0E2D',  # Airtel red
            'tkash': '#009966',  # T-Kash green
            'equitel': '#662D91',  # Equitel purple
            'paypal': '#003087',  # PayPal blue
            'stripe': '#6772E5',  # Stripe blue
            'bank_transfer': '#666666',  # Gray
            'cash_on_delivery': '#333333',  # Dark gray
        }
        color = colors.get(obj.payment_gateway, 'gray')
        gateway_text = obj.get_payment_gateway_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, gateway_text
        )
    gateway_badge.short_description = 'Gateway'
    
    def payment_method_display(self, obj):
        """Display payment method"""
        return obj.payment_method_display
    payment_method_display.short_description = 'Method'
    
    def mobile_number_display(self, obj):
        """Display mobile number if available"""
        if obj.mobile_number:
            network_icon = ''
            if obj.mobile_network == 'safaricom':
                network_icon = '📶'
            elif obj.mobile_network == 'airtel':
                network_icon = '📱'
            elif obj.mobile_network == 'telkom':
                network_icon = '📞'
            return format_html(f'{network_icon} {obj.mobile_number}')
        return ''
    mobile_number_display.short_description = 'Mobile'
    
    def created_date(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%b %d, %Y')
    created_date.short_description = 'Created'
    created_date.admin_order_field = 'created_at'
    
    def is_gift_indicator(self, obj):
        """Display gift payment indicator"""
        if obj.is_gift_payment:
            return format_html('🎁')
        return ''
    is_gift_indicator.short_description = 'Gift'
    
    # Read-only field methods
    def formatted_amount(self, obj):
        """Display formatted amount in read-only field"""
        return obj.formatted_amount
    formatted_amount.short_description = 'Formatted Amount'
    
    def mpesa_details_display(self, obj):
        """Display M-Pesa details"""
        details = obj.get_mpesa_details()
        if details:
            html = '<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">'
            html += f'<strong>Mobile:</strong> {details["mobile_number"]}<br>'
            html += f'<strong>Network:</strong> {details["network"]}<br>'
            html += f'<strong>Transaction Code:</strong> {details["transaction_code"]}<br>'
            html += f'<strong>Amount:</strong> KES {details["amount"]:,.2f}'
            html += '</div>'
            return format_html(html)
        return 'Not an M-Pesa payment'
    mpesa_details_display.short_description = 'M-Pesa Details'
    
    def cash_collected_details(self, obj):
        """Display cash collection details"""
        if obj.payment_gateway == 'cash_on_delivery':
            html = '<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">'
            if obj.cash_collected:
                html += '<span style="color: green; font-weight: bold;">✓ Cash Collected</span><br>'
                html += f'<strong>Collected At:</strong> {obj.cash_collected_at.strftime("%Y-%m-%d %H:%M") if obj.cash_collected_at else "N/A"}<br>'
                html += f'<strong>Collected By:</strong> {obj.cash_collected_by or "N/A"}'
            else:
                html += '<span style="color: orange; font-weight: bold;">⏳ Pending Collection</span>'
            html += '</div>'
            return format_html(html)
        return 'Not a cash on delivery payment'
    cash_collected_details.short_description = 'Cash Collection Status'
    
    # Admin Actions
    def mark_as_successful(self, request, queryset):
        """Mark selected payments as successful"""
        count = queryset.filter(status__in=['pending', 'initiated']).update(
            status='successful',
            paid_at=timezone.now()
        )
        self.message_user(request, f"{count} payments marked as successful.")
    mark_as_successful.short_description = "Mark as successful"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected payments as failed"""
        count = queryset.filter(status__in=['pending', 'initiated']).update(
            status='failed',
            error_message='Manually marked as failed by admin'
        )
        self.message_user(request, f"{count} payments marked as failed.")
    mark_as_failed.short_description = "Mark as failed"
    
    def mark_as_refunded(self, request, queryset):
        """Mark selected payments as refunded"""
        count = 0
        for payment in queryset.filter(status='successful'):
            payment.mark_as_refunded(reference=f"ADMIN-REFUND-{timezone.now().strftime('%Y%m%d')}")
            count += 1
        self.message_user(request, f"{count} payments marked as refunded.")
    mark_as_refunded.short_description = "Mark as refunded"
    
    def mark_as_cash_collected(self, request, queryset):
        """Mark cash on delivery payments as collected"""
        count = queryset.filter(
            payment_gateway='cash_on_delivery',
            cash_collected=False
        ).update(
            cash_collected=True,
            cash_collected_at=timezone.now(),
            cash_collected_by=request.user.get_full_name() or request.user.username
        )
        self.message_user(request, f"{count} cash payments marked as collected.")
    mark_as_cash_collected.short_description = "Mark cash as collected"
    
    def export_payments_csv(self, request, queryset):
        """Export payments to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Payment Reference', 'Order Number', 'Customer Email', 'Amount',
            'Status', 'Gateway', 'Method', 'Mobile Number', 'Transaction Code',
            'Created At', 'Paid At', 'Is Gift'
        ])
        
        for payment in queryset:
            writer.writerow([
                payment.payment_reference,
                payment.order.order_number if payment.order else '',
                payment.user.email if payment.user else '',
                float(payment.amount),
                payment.get_status_display(),
                payment.get_payment_gateway_display(),
                payment.payment_method_display,
                payment.mobile_number,
                payment.transaction_code,
                payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                payment.paid_at.strftime('%Y-%m-%d %H:%M:%S') if payment.paid_at else '',
                'Yes' if payment.is_gift_payment else 'No'
            ])
        
        return response
    export_payments_csv.short_description = "Export selected payments to CSV"


@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    """Admin configuration for PaymentWebhook model"""
    list_display = [
        'gateway_badge', 'event_type', 'payment_reference',
        'is_processed_badge', 'created_date', 'processing_status'
    ]
    list_filter = ['gateway', 'event_type', 'is_processed', 'created_at']
    search_fields = [
        'payment__payment_reference', 'gateway', 'event_type',
        'payload'
    ]
    readonly_fields = [
        'gateway', 'event_type', 'payload_display', 'headers_display',
        'payment_link', 'ip_address', 'is_processed', 'processing_error',
        'created_at', 'processed_at'
    ]
    fieldsets = (
        ('Webhook Information', {
            'fields': ('gateway', 'event_type', 'payment_link')
        }),
        ('Payload Data', {
            'fields': ('payload_display', 'headers_display'),
            'classes': ('collapse',)
        }),
        ('Processing Status', {
            'fields': ('is_processed', 'processing_error', 'processed_at')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['process_webhooks', 'mark_as_processed', 'delete_old_webhooks']
    list_per_page = 100
    
    def gateway_badge(self, obj):
        """Display gateway with badge"""
        colors = {
            'mpesa': '#FF6900',
            'stripe': '#6772E5',
            'paypal': '#003087',
        }
        color = colors.get(obj.gateway.lower(), 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, obj.gateway.upper()
        )
    gateway_badge.short_description = 'Gateway'
    
    def payment_reference(self, obj):
        """Display payment reference"""
        if obj.payment:
            return obj.payment.payment_reference
        return 'No Payment Linked'
    payment_reference.short_description = 'Payment Ref'
    
    def is_processed_badge(self, obj):
        """Display processing status with badge"""
        if obj.is_processed:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">✓ Processed</span>'
            )
        else:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">⏳ Pending</span>'
            )
    is_processed_badge.short_description = 'Processed'
    
    def created_date(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%b %d, %H:%M')
    created_date.short_description = 'Received'
    created_date.admin_order_field = 'created_at'
    
    def processing_status(self, obj):
        """Display processing status with time"""
        if obj.is_processed and obj.processed_at:
            seconds = (obj.processed_at - obj.created_at).total_seconds()
            return f"{seconds:.1f}s"
        elif not obj.is_processed:
            hours_ago = (timezone.now() - obj.created_at).total_seconds() / 3600
            if hours_ago > 24:
                return f"{int(hours_ago/24)}d ago"
            elif hours_ago > 1:
                return f"{int(hours_ago)}h ago"
            else:
                return "Recent"
        return ''
    processing_status.short_description = 'Process Time'
    
    # Read-only field methods
    def payload_display(self, obj):
        """Display formatted JSON payload"""
        import json
        formatted_json = json.dumps(obj.payload, indent=2, sort_keys=True)
        return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 300px; overflow: auto;">{}</pre>', formatted_json)
    payload_display.short_description = 'Payload (JSON)'
    
    def headers_display(self, obj):
        """Display formatted headers"""
        import json
        formatted_json = json.dumps(obj.headers, indent=2, sort_keys=True)
        return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 200px; overflow: auto;">{}</pre>', formatted_json)
    headers_display.short_description = 'Headers (JSON)'
    
    def payment_link(self, obj):
        """Display payment with link"""
        if obj.payment:
            url = f'/admin/payments/payment/{obj.payment.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.payment.payment_reference)
        return 'No Payment'
    payment_link.short_description = 'Payment'
    
    # Admin Actions
    def process_webhooks(self, request, queryset):
        """Process selected webhooks"""
        count = 0
        for webhook in queryset.filter(is_processed=False):
            # Simulate processing
            webhook.is_processed = True
            webhook.processed_at = timezone.now()
            webhook.save()
            count += 1
        self.message_user(request, f"{count} webhooks processed.")
    process_webhooks.short_description = "Process selected webhooks"
    
    def mark_as_processed(self, request, queryset):
        """Mark webhooks as processed"""
        count = queryset.filter(is_processed=False).update(
            is_processed=True,
            processed_at=timezone.now()
        )
        self.message_user(request, f"{count} webhooks marked as processed.")
    mark_as_processed.short_description = "Mark as processed"
    
    def delete_old_webhooks(self, request, queryset):
        """Delete webhooks older than 30 days"""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        old_webhooks = queryset.filter(created_at__lt=thirty_days_ago, is_processed=True)
        count = old_webhooks.count()
        old_webhooks.delete()
        self.message_user(request, f"{count} old webhooks deleted.")
    delete_old_webhooks.short_description = "Delete old processed webhooks"


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin configuration for PaymentMethod model"""
    list_display = [
        'display_name', 'gateway_display', 'method_type_display',
        'is_active', 'is_default', 'sort_order',
        'min_max_amount', 'created_date'
    ]
    list_filter = ['method_type', 'is_active', 'is_default', 'gateway']
    search_fields = ['name', 'display_name', 'description', 'gateway']
    list_editable = ['sort_order', 'is_active', 'is_default']
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'display_name', 'gateway', 'method_type',
                'description', 'icon'
            )
        }),
        ('Status & Ordering', {
            'fields': ('is_active', 'is_default', 'sort_order')
        }),
        ('Amount Limits', {
            'fields': ('min_amount', 'max_amount')
        }),
        ('Processing Fees', {
            'fields': ('processing_fee_percent', 'processing_fee_fixed'),
            'classes': ('collapse',)
        }),
        ('Kenya Mobile Networks', {
            'fields': ('supported_networks_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at', 'supported_networks_display']
    actions = ['activate_methods', 'deactivate_methods', 'set_as_default']
    list_per_page = 30
    
    def gateway_display(self, obj):
        """Display gateway with badge"""
        colors = {
            'mpesa': '#FF6900',
            'airtel_money': '#CE0E2D',
            'tkash': '#009966',
            'equitel': '#662D91',
            'paypal': '#003087',
            'stripe': '#6772E5',
            'bank_transfer': '#666666',
            'cash_on_delivery': '#333333',
        }
        color = colors.get(obj.gateway, 'gray')
        gateway_text = obj.gateway.replace('_', ' ').title()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, gateway_text
        )
    gateway_display.short_description = 'Gateway'
    
    def method_type_display(self, obj):
        """Display method type with badge"""
        colors = {
            'mobile_money': '#FF6900',
            'card': '#003087',
            'bank': '#666666',
            'cash': '#333333',
            'wallet': '#009966',
        }
        color = colors.get(obj.method_type, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, obj.get_method_type_display()
        )
    method_type_display.short_description = 'Type'
    
    def min_max_amount(self, obj):
        """Display min/max amount range"""
        if obj.max_amount:
            return f"KES {obj.min_amount:,.0f} - KES {obj.max_amount:,.0f}"
        return f"KES {obj.min_amount:,.0f}+"
    min_max_amount.short_description = 'Amount Range'
    
    def created_date(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%b %d, %Y')
    created_date.short_description = 'Created'
    created_date.admin_order_field = 'created_at'
    
    # Read-only field method
    def supported_networks_display(self, obj):
        """Display supported networks"""
        if obj.supported_networks:
            html = '<div style="display: flex; gap: 5px; flex-wrap: wrap;">'
            for network in obj.supported_networks:
                colors = {
                    'safaricom': '#FF6900',
                    'airtel': '#CE0E2D',
                    'telkom': '#662D91',
                }
                color = colors.get(network, 'gray')
                html += f'<span style="background-color: {color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 11px;">{network.title()}</span>'
            html += '</div>'
            return format_html(html)
        return 'No specific networks'
    supported_networks_display.short_description = 'Supported Networks'
    
    # Admin Actions
    def activate_methods(self, request, queryset):
        """Activate selected payment methods"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} payment methods activated.")
    activate_methods.short_description = "Activate selected methods"
    
    def deactivate_methods(self, request, queryset):
        """Deactivate selected payment methods"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} payment methods deactivated.")
    deactivate_methods.short_description = "Deactivate selected methods"
    
    def set_as_default(self, request, queryset):
        """Set selected method as default (only one can be default)"""
        # First, unset all defaults
        PaymentMethod.objects.filter(is_default=True).update(is_default=False)
        
        # Set the first selected as default
        if queryset.exists():
            method = queryset.first()
            method.is_default = True
            method.save()
            self.message_user(request, f"'{method.display_name}' set as default payment method.")
    set_as_default.short_description = "Set as default method"