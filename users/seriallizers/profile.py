# users/serializers/profile.py
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import datetime, date
import re

from ..models import (
    CustomUser, 
    UserAddress, 
    NotificationPreferences, 
    LoyaltyPointsHistory, 
    UserActivityLog
)


# ==================== USER ADDRESS SERIALIZERS ====================

class UserAddressSerializer(serializers.ModelSerializer):
    """Serializer for user addresses"""
    full_address = serializers.CharField(read_only=True)
    county_display = serializers.SerializerMethodField()
    
    # Kenya phone number validation
    contact_phone = serializers.CharField(
        validators=[
            RegexValidator(
                regex=r'^(?:254|\+254|0)?(7(?:(?:[129][0-9])|(?:0[0-9])|(4[0-9])|(5[0-9])|(6[0-9])|(8[0-9]))[0-9]{6})$',
                message=_("Please enter a valid Kenyan phone number (e.g., 0712345678 or +254712345678)")
            )
        ]
    )
    
    class Meta:
        model = UserAddress
        fields = [
            'id', 'contact_name', 'contact_phone',
            'address_line_1', 'address_line_2', 'estate',
            'building', 'floor', 'city', 'county',
            'county_display', 'postal_code', 'country',
            'address_type', 'is_default_shipping',
            'is_default_billing', 'delivery_instructions',
            'full_address', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_county_display(self, obj):
        """Get human-readable county name"""
        return obj.get_county_display()
    
    def validate_contact_name(self, value):
        """Validate contact name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError(_("Contact name must be at least 2 characters."))
        return value.strip()
    
    def validate_city(self, value):
        """Validate city name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError(_("City must be at least 2 characters."))
        return value.strip().title()
    
    def create(self, validated_data):
        """Create new address for user"""
        # Get user from context (should be set in view)
        user = self.context['request'].user
        validated_data['user'] = user
        
        # Create address
        address = super().create(validated_data)
        return address
    
    def update(self, instance, validated_data):
        """Update existing address"""
        # Handle default address logic
        if validated_data.get('is_default_shipping'):
            # Clear other default shipping addresses
            UserAddress.objects.filter(
                user=instance.user,
                is_default_shipping=True
            ).exclude(id=instance.id).update(is_default_shipping=False)
        
        if validated_data.get('is_default_billing'):
            # Clear other default billing addresses
            UserAddress.objects.filter(
                user=instance.user,
                is_default_billing=True
            ).exclude(id=instance.id).update(is_default_billing=False)
        
        return super().update(instance, validated_data)


class UserAddressCreateSerializer(UserAddressSerializer):
    """Serializer for creating new addresses (simplified required fields)"""
    class Meta(UserAddressSerializer.Meta):
        fields = [
            'contact_name', 'contact_phone',
            'address_line_1', 'city', 'county',
            'address_type', 'is_default_shipping',
            'is_default_billing'
        ]
    
    def validate(self, data):
        """Additional validation for address creation"""
        # Ensure at least address_line_1 is provided
        if not data.get('address_line_1'):
            raise serializers.ValidationError({
                'address_line_1': _("Address line 1 is required.")
            })
        
        # Ensure city is provided
        if not data.get('city'):
            raise serializers.ValidationError({
                'city': _("City is required.")
            })
        
        return data


# ==================== NOTIFICATION PREFERENCES SERIALIZERS ====================

class NotificationPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for user notification preferences"""
    
    class Meta:
        model = NotificationPreferences
        fields = [
            # Order notifications
            'order_confirmation', 'order_shipped', 'order_delivered',
            'order_cancelled', 'payment_confirmation',
            
            # Promotional notifications
            'flash_sales', 'daily_deals', 'price_drop_alerts',
            'new_arrivals', 'back_in_stock', 'baby_care_tips',
            
            # Account notifications
            'security_alerts', 'account_updates', 'birthday_offers',
            
            # Social notifications
            'reviews_replies', 'wishlist_reminders', 'abandoned_cart_reminders',
            
            # Delivery channels
            'email_notifications', 'sms_notifications', 'push_notifications',
            
            'updated_at'
        ]
        read_only_fields = ['updated_at']
    
    def validate(self, data):
        """Ensure at least one notification channel is enabled"""
        channels = ['email_notifications', 'sms_notifications', 'push_notifications']
        if not any(data.get(channel, False) for channel in channels):
            raise serializers.ValidationError(
                _("At least one notification channel must be enabled.")
            )
        return data


class NotificationPreferencesUpdateSerializer(serializers.ModelSerializer):
    """Simplified serializer for updating notification preferences"""
    class Meta:
        model = NotificationPreferences
        fields = [
            'email_notifications', 'sms_notifications', 'push_notifications'
        ]
    
    def validate(self, data):
        """Ensure at least one notification channel is enabled"""
        if not any(data.values()):
            raise serializers.ValidationError(
                _("At least one notification channel must be enabled.")
            )
        return data


# ==================== LOYALTY POINTS SERIALIZERS ====================

class LoyaltyPointsHistorySerializer(serializers.ModelSerializer):
    """Serializer for loyalty points history"""
    action_type = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()
    
    class Meta:
        model = LoyaltyPointsHistory
        fields = [
            'id', 'points', 'balance_after', 'reason',
            'action_type', 'order_number', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_action_type(self, obj):
        """Get action type (earned or spent)"""
        if obj.points > 0:
            return 'earned'
        return 'spent'
    
    def get_order_number(self, obj):
        """Get order number if associated with order"""
        if obj.order:
            return obj.order.order_number
        return None


# ==================== USER ACTIVITY LOG SERIALIZERS ====================

class UserActivityLogSerializer(serializers.ModelSerializer):
    """Serializer for user activity logs"""
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = UserActivityLog
        fields = [
            'id', 'activity_type', 'description',
            'user_email', 'ip_address', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_user_email(self, obj):
        """Get user email"""
        if obj.user:
            return obj.user.email
        return 'Anonymous'


# ==================== USER PROFILE SERIALIZERS ====================

class UserProfileSerializer(serializers.ModelSerializer):
    """Main serializer for user profile"""
    full_name = serializers.CharField(read_only=True)
    is_complete_profile = serializers.BooleanField(read_only=True)
    customer_tier = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    age_recommendations = serializers.SerializerMethodField()
    default_shipping_address = serializers.SerializerMethodField()
    default_billing_address = serializers.SerializerMethodField()
    notification_preferences = serializers.SerializerMethodField()
    addresses_count = serializers.SerializerMethodField()
    recent_activity = serializers.SerializerMethodField()
    loyalty_summary = serializers.SerializerMethodField()
    
    # Baby shop specific read-only stats
    loyalty_points = serializers.IntegerField(read_only=True)
    total_orders = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    children_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            # Basic info
            'id', 'email', 'username', 'full_name', 'first_name', 'last_name', 'phone',
            'avatar', 'avatar_url', 'date_of_birth', 'gender',
            
            # Baby shop info
            'has_children', 'children_count', 'child_gender', 'child_age_range',
            
            # Verification status
            'is_email_verified', 'email_verified_at', 'is_phone_verified', 'phone_verified_at',
            
            # Preferences
            'newsletter_subscription', 'marketing_emails', 'sms_notifications',
            
            # E-commerce metrics (read-only)
            'loyalty_points', 'total_orders', 'total_spent', 'customer_tier',
            
            # Computed fields
            'is_complete_profile', 'age_recommendations',
            'default_shipping_address', 'default_billing_address', 'notification_preferences',
            'addresses_count', 'recent_activity', 'loyalty_summary',
            
            # Timestamps (read-only)
            'date_joined', 'last_login', 'last_activity', 'last_order_date',
        ]
        read_only_fields = [
            'id', 'email', 'username', 'is_email_verified', 'email_verified_at',
            'is_phone_verified', 'phone_verified_at', 'loyalty_points',
            'total_orders', 'total_spent', 'date_joined', 'last_login',
            'last_activity', 'last_order_date', 'customer_tier',
        ]
    
    def get_avatar_url(self, obj):
        """Get avatar URL"""
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    
    def get_age_recommendations(self, obj):
        """Get age-based recommendations"""
        return obj.get_age_recommendations()
    
    def get_default_shipping_address(self, obj):
        """Get default shipping address"""
        address = obj.get_default_shipping_address()
        if address:
            return UserAddressSerializer(address, context=self.context).data
        return None
    
    def get_default_billing_address(self, obj):
        """Get default billing address"""
        address = obj.get_default_billing_address()
        if address:
            return UserAddressSerializer(address, context=self.context).data
        return None
    
    def get_notification_preferences(self, obj):
        """Get notification preferences"""
        try:
            prefs = obj.notification_prefs
            return NotificationPreferencesSerializer(prefs).data
        except NotificationPreferences.DoesNotExist:
            return None
    
    def get_addresses_count(self, obj):
        """Get count of user addresses"""
        return obj.addresses.count()
    
    def get_recent_activity(self, obj):
        """Get recent user activity"""
        recent_logs = obj.activity_logs.all()[:5]
        return UserActivityLogSerializer(recent_logs, many=True).data
    
    def get_loyalty_summary(self, obj):
        """Get loyalty points summary"""
        return {
            'current_points': obj.loyalty_points,
            'tier': obj.customer_tier,
            'next_tier': self._get_next_tier(obj),
            'points_to_next_tier': self._get_points_to_next_tier(obj)
        }
    
    def _get_next_tier(self, user):
        """Get next loyalty tier"""
        tiers = {
            'bronze': {'min': 0, 'next': 'silver'},
            'silver': {'min': 5000, 'next': 'gold'},
            'gold': {'min': 20000, 'next': 'platinum'},
            'platinum': {'min': 50000, 'next': None}
        }
        current_tier = user.customer_tier
        return tiers[current_tier]['next']
    
    def _get_points_to_next_tier(self, user):
        """Calculate points needed for next tier"""
        tier_thresholds = {
            'bronze': 5000,
            'silver': 20000,
            'gold': 50000,
            'platinum': None
        }
        current_tier = user.customer_tier
        threshold = tier_thresholds[current_tier]
        
        if threshold:
            return max(0, threshold - float(user.total_spent))
        return 0
    
    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        if value:
            # Check if user is at least 18 years old
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 18:
                raise serializers.ValidationError(_("You must be at least 18 years old."))
            if age > 100:
                raise serializers.ValidationError(_("Please enter a valid date of birth."))
        return value
    
    def validate_phone(self, value):
        """Validate phone number"""
        if value:
            # Kenya phone number validation
            kenya_phone_regex = r'^(?:254|\+254|0)?(7(?:(?:[129][0-9])|(?:0[0-9])|(4[0-9])|(5[0-9])|(6[0-9])|(8[0-9]))[0-9]{6})$'
            if not re.match(kenya_phone_regex, value):
                raise serializers.ValidationError(_("Please enter a valid Kenyan phone number."))
        return value
    
    def update(self, instance, validated_data):
        """Update user profile with proper handling"""
        # Handle avatar upload separately if needed
        avatar = validated_data.pop('avatar', None)
        
        # Update other fields
        user = super().update(instance, validated_data)
        
        # If avatar was provided in update, save it
        if avatar:
            user.avatar = avatar
            user.save()
        
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating specific profile fields"""
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'phone',
            'avatar', 'date_of_birth', 'gender',
            'has_children', 'children_count', 'child_gender', 'child_age_range',
            'newsletter_subscription', 'marketing_emails', 'sms_notifications'
        ]
    
    def validate_phone(self, value):
        """Validate phone number"""
        if value:
            # Kenya phone number validation
            kenya_phone_regex = r'^(?:254|\+254|0)?(7(?:(?:[129][0-9])|(?:0[0-9])|(4[0-9])|(5[0-9])|(6[0-9])|(8[0-9]))[0-9]{6})$'
            if not re.match(kenya_phone_regex, value):
                raise serializers.ValidationError(_("Please enter a valid Kenyan phone number."))
            
            # Check if phone is already used by another user
            if CustomUser.objects.filter(phone=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(_("This phone number is already in use."))
        
        return value
    
    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        if value:
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 18:
                raise serializers.ValidationError(_("You must be at least 18 years old."))
        return value


class UserProfileMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for user info (used in orders, reviews, etc.)"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'full_name',
            'avatar_url', 'phone'
        ]
        read_only_fields = fields
    
    def get_full_name(self, obj):
        """Get user's full name safely"""
        try:
            if isinstance(obj, dict):
                # Handle dictionary
                first_name = obj.get('first_name', '')
                last_name = obj.get('last_name', '')
            else:
                # Handle User object
                first_name = obj.first_name or ''
                last_name = obj.last_name or ''
            
            full_name = f"{first_name} {last_name}".strip()
            return full_name if full_name else obj.get('email', '') if isinstance(obj, dict) else obj.email
        except Exception:
            return ''
    
    def get_avatar_url(self, obj):
        """Get avatar URL safely"""
        try:
            # Check if obj is a dict
            if isinstance(obj, dict):
                return None
            
            # Check if avatar exists and has a file
            if hasattr(obj, 'avatar') and obj.avatar:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.avatar.url)
                return obj.avatar.url
            return None
        except (AttributeError, ValueError) as e:
            # Handle missing file or other errors
            return None

# ==================== COMPOSITE SERIALIZERS ====================

# users/serializers/profile.py (update the UserDashboardSerializer)
class UserDashboardSerializer(serializers.Serializer):
    """Serializer for user dashboard data"""
    profile = UserProfileSerializer()
    addresses = UserAddressSerializer(many=True)
    recent_orders = serializers.SerializerMethodField()
    wishlist_items = serializers.SerializerMethodField()
    cart_summary = serializers.SerializerMethodField()
    loyalty_history = LoyaltyPointsHistorySerializer(many=True)
    notification_preferences = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    
    def get_recent_orders(self, obj):
        """Get recent orders"""
        try:
            from orders.serializers import OrderListSerializer
            recent_orders = obj['profile'].orders.all()[:5]
            return OrderListSerializer(recent_orders, many=True, context=self.context).data
        except ImportError:
            return []
        except Exception:
            return []
    
    def get_wishlist_items(self, obj):
        """Get wishlist items"""
        try:
            from products.serializers import ProductListSerializer
            user = obj['profile']
            if hasattr(user, 'wishlists') and user.wishlists.exists():
                wishlist = user.wishlists.first()
                wishlist_items = wishlist.products.all()[:5]
                return ProductListSerializer(wishlist_items, many=True, context=self.context).data
            return []
        except ImportError:
            return []
        except Exception:
            return []
    
    def get_cart_summary(self, obj):
        """Get cart summary"""
        try:
            user = obj['profile']
            cart = user.cart
            return {
                'item_count': cart.total_items,
                'subtotal': float(cart.subtotal),
                'age_ranges': cart.get_age_ranges_in_cart(),
                'genders': cart.get_genders_in_cart()
            }
        except Exception:
            return None
    
    def get_notification_preferences(self, obj):
        """Get notification preferences"""
        try:
            user = obj['profile']
            prefs = user.notification_prefs
            return NotificationPreferencesSerializer(prefs).data
        except NotificationPreferences.DoesNotExist:
            return None
        except Exception:
            return None
    
    def get_stats(self, obj):
        """Get user statistics"""
        try:
            user = obj['profile']
            return {
                'total_addresses': user.addresses.count(),
                'total_orders': user.total_orders,
                'total_spent': float(user.total_spent),
                'loyalty_points': user.loyalty_points,
                'customer_tier': user.customer_tier,
                'children_count': user.children_count,
                'is_complete_profile': user.is_complete_profile
            }
        except Exception:
            return {}


