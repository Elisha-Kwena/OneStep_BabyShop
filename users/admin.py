# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser,PasswordResetToken
from django.utils import timezone
from django.conf import settings
from django.utils.html import format_html
from django.urls import reverse

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Display in list view
    list_display = ('email', 'username', 'phone', 'is_email_verified', 'is_active', 'is_staff', 'date_joined')
    
    # Search fields
    search_fields = ('email', 'username', 'phone')
    
    # Filters
    list_filter = ('is_email_verified', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    
    # Ordering
    ordering = ('-date_joined',)
    
    # Fieldsets for edit view
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ('username', 'phone', 'avatar')}),
        (_('Email Verification'), {'fields': ('is_email_verified', 'email_verification_code', 'email_verification_sent_at')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important Dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    # Fields for add form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'phone', 'password1', 'password2'),
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin interface for PasswordResetToken model"""
    
    # Display fields in list view
    list_display = (
        'user_email',
        'token_truncated',
        'created_at_formatted',
        'expires_at_formatted',
        'status_badge',
        'is_used',
        'time_remaining',
    )
    
    # Fields to search
    search_fields = (
        'user__email',
        'user__username',
        'token',
    )
    
    # Filters
    list_filter = (
        'is_used',
        'created_at',
        'expires_at',
    )
    
    # Ordering
    ordering = ('-created_at',)
    
    # Readonly fields (for viewing only)
    readonly_fields = (
        'user',
        'token',
        'created_at',
        'expires_at',
        'is_used',
        'used_at',
        'status',
        'time_remaining_detailed',
        'token_link',
    )
    
    # Fieldsets for detail view
    fieldsets = (
        (_('Token Information'), {
            'fields': (
                'token_link',
                'user',
                'status',
                'time_remaining_detailed',
            )
        }),
        
        (_('Timestamps'), {
            'fields': (
                'created_at',
                'expires_at',
                'is_used',
                'used_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Custom methods for display
    def user_email(self, obj):
        """Display user email with link to user admin"""
        url = reverse('admin:users_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = _('User Email')
    user_email.admin_order_field = 'user__email'
    
    def token_truncated(self, obj):
        """Display truncated token"""
        token_str = str(obj.token)
        return f"{token_str[:8]}...{token_str[-8:]}"
    token_truncated.short_description = _('Token')
    
    def created_at_formatted(self, obj):
        """Format created_at datetime"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = _('Created')
    created_at_formatted.admin_order_field = 'created_at'
    
    def expires_at_formatted(self, obj):
        """Format expires_at datetime"""
        return obj.expires_at.strftime('%Y-%m-%d %H:%M')
    expires_at_formatted.short_description = _('Expires')
    expires_at_formatted.admin_order_field = 'expires_at'
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        if obj.is_used:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">Used</span>'
            )
        elif obj.is_expired():
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">Expired</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 10px; font-size: 12px;">Active</span>'
            )
    status_badge.short_description = _('Status')
    
    def time_remaining(self, obj):
        """Show time remaining for active tokens"""
        if obj.is_used:
            return "Used"
        elif obj.is_expired():
            return "Expired"
        else:
            remaining = obj.expires_at - timezone.now()
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours}h {minutes}m"
    time_remaining.short_description = _('Time Left')
    
    # Detailed view methods
    def status(self, obj):
        """Detailed status in view"""
        if obj.is_used:
            return f"Used on {obj.used_at.strftime('%Y-%m-%d %H:%M:%S')}"
        elif obj.is_expired():
            return "Expired"
        else:
            return "Active (Valid)"
    
    def time_remaining_detailed(self, obj):
        """Detailed time remaining"""
        if obj.is_used or obj.is_expired():
            return "N/A"
        remaining = obj.expires_at - timezone.now()
        days = remaining.days
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        
        return ", ".join(parts) + " remaining"
    time_remaining_detailed.short_description = _('Time Remaining')
    
    def token_link(self, obj):
        """Display token as clickable link (for frontend)"""
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password/{obj.token}"
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            reset_url,
            str(obj.token)
        )
    token_link.short_description = _('Reset Link')
    
    # Disable adding new tokens from admin (they should be created via API)
    def has_add_permission(self, request):
        return False
    
    # Optional: Add action to delete expired tokens
    actions = ['delete_expired_tokens']
    
    def delete_expired_tokens(self, request, queryset):
        """Admin action to delete expired tokens"""
        expired_count = 0
        for token in queryset:
            if token.is_expired() or token.is_used:
                token.delete()
                expired_count += 1
        
        self.message_user(
            request, 
            f"Successfully deleted {expired_count} expired/used tokens."
        )
    delete_expired_tokens.short_description = _("Delete expired/used tokens")


# Register both models
# admin.site.register(CustomUser, CustomUserAdmin)
# admin.site.register(PasswordResetToken, PasswordResetTokenAdmin)