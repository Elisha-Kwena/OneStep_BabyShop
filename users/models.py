from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import logging
from datetime import timedelta
import uuid
import random

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    
    # Authentication fields
    email = models.EmailField(
        verbose_name=_("email address"),
        max_length=255,
        unique=True,
        error_messages={
            'unique': _("A user with that email already exists")
        }
    )
    username = models.CharField(
        verbose_name=_('username'),
        max_length=30,
        unique=True,
        error_messages={
            'unique': _('A user with that username already exists.'),
        }
    )
    
    # Personal information
    first_name = models.CharField(
        verbose_name=_("first name"),
        max_length=255,
        blank=True
    )
    last_name = models.CharField(
        verbose_name=_("last name"),
        max_length=255,
        blank=True
    )
    phone = models.CharField(
        verbose_name=_("phone number"),
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        error_messages={
            'unique': _('A user with that phone number already exists.'),
        }
    )
    
    # Baby shop specific information
    has_children = models.BooleanField(
        verbose_name=_("has children"),
        default=False,
        help_text=_("Does this user have children?")
    )
    children_count = models.PositiveIntegerField(
        verbose_name=_("number of children"),
        default=0,
        help_text=_("Number of children the user has")
    )
    child_gender = models.CharField(
        verbose_name=_("child gender"),
        max_length=20,
        blank=True,
        choices=[
            ('boy', _('Boy')),
            ('girl', _('Girl')),
            ('both', _('Both')),
            ('prefer_not_to_say', _('Prefer not to say')),
        ]
    )
    child_age_range = models.CharField(
        verbose_name=_("child age range"),
        max_length=20,
        blank=True,
        choices=[
            ('0-6m', _('0-6 Months')),
            ('6-12m', _('6-12 Months')),
            ('1-2y', _('1-2 Years')),
            ('2-3y', _('2-3 Years')),
            ('3-4y', _('3-4 Years')),
            ('4-5y', _('4-5 Years')),
            ('5-6y', _('5-6 Years')),
            ('multiple', _('Multiple ages')),
        ]
    )
    
    # Profile
    avatar = models.ImageField(
        verbose_name=_('avatar'),
        upload_to='avatars/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text=_('Profile picture for the user.')
    )
    date_of_birth = models.DateField(
        verbose_name=_("date of birth"),
        null=True,
        blank=True
    )
    gender = models.CharField(
        verbose_name=_("gender"),
        max_length=20,
        blank=True,
        choices=[
            ('male', _('Male')),
            ('female', _('Female')),
            ('other', _('Other')),
            ('prefer_not_to_say', _('Prefer not to say')),
        ]
    )
    
    # Email verification
    is_email_verified = models.BooleanField(
        verbose_name=_('email verified'),
        default=False,
        help_text=_('Designates whether the user has verified their email address.')
    )
    email_verified_at = models.DateTimeField(
        verbose_name=_('email verified at'),
        null=True,
        blank=True
    )
    email_verification_code = models.CharField(
        verbose_name=_('email verification code'),
        max_length=6,
        blank=True,
        null=True,
        help_text=_('Six-digit verification code sent to email.')
    )
    email_verification_sent_at = models.DateTimeField(
        verbose_name=_('verification code sent at'),
        blank=True,
        null=True,
        help_text=_('Timestamp when verification code was sent.')
    )
    
    # Phone verification
    is_phone_verified = models.BooleanField(
        verbose_name=_('phone verified'),
        default=False,
        help_text=_('Designates whether the user has verified their phone number.')
    )
    phone_verified_at = models.DateTimeField(
        verbose_name=_('phone verified at'),
        null=True,
        blank=True
    )
    phone_verification_code = models.CharField(
        verbose_name=_('phone verification code'),
        max_length=6,
        blank=True,
        null=True,
    )
    phone_verification_sent_at = models.DateTimeField(
        verbose_name=_('phone verification sent at'),
        null=True,
        blank=True
    )
    
    # Account status
    is_active = models.BooleanField(
        verbose_name=_('active'),
        default=True,
        help_text=_('Designates whether this user should be treated as active.')
    )
    is_staff = models.BooleanField(
        verbose_name=_('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.')
    )
    
    # Preferences
    newsletter_subscription = models.BooleanField(
        verbose_name=_('newsletter subscription'),
        default=True,
        help_text=_('User has subscribed to newsletters.')
    )
    marketing_emails = models.BooleanField(
        verbose_name=_('marketing emails'),
        default=True,
        help_text=_('User agrees to receive marketing emails.')
    )
    sms_notifications = models.BooleanField(
        verbose_name=_('SMS notifications'),
        default=False,
        help_text=_('User agrees to receive SMS notifications.')
    )
    
    # E-commerce metrics
    loyalty_points = models.PositiveIntegerField(
        verbose_name=_('loyalty points'),
        default=0
    )
    total_orders = models.PositiveIntegerField(
        verbose_name=_('total orders'),
        default=0,
        editable=False
    )
    total_spent = models.DecimalField(
        verbose_name=_('total spent'),
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        verbose_name=_('date joined'),
        default=timezone.now
    )
    last_login = models.DateTimeField(
        verbose_name=_('last login'),
        null=True,
        blank=True
    )
    last_activity = models.DateTimeField(
        verbose_name=_('last activity'),
        null=True,
        blank=True
    )
    last_order_date = models.DateTimeField(
        verbose_name=_('last order date'),
        null=True,
        blank=True
    )
    
    # Security
    password_reset_token = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    password_reset_token_expiry = models.DateTimeField(
        null=True,
        blank=True
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['phone']),
            models.Index(fields=['date_joined']),
            models.Index(fields=['last_order_date']),
            models.Index(fields=['is_active', 'is_email_verified']),
        ]
    
    def __str__(self):
        return self.username or self.email
    
    # Properties
    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return ""
    
    @property
    def is_complete_profile(self):
        """Check if user has completed their profile"""
        return bool(self.first_name and self.last_name and self.phone and self.is_email_verified)
    
    @property
    def customer_tier(self):
        """Determine customer loyalty tier"""
        if self.total_spent >= 50000:
            return 'platinum'
        elif self.total_spent >= 20000:
            return 'gold'
        elif self.total_spent >= 5000:
            return 'silver'
        return 'bronze'
    
    # Methods
    def generate_verification_code(self, field='email'):
        """Generate verification code for email or phone"""
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        if field == 'email':
            self.email_verification_code = code
            self.email_verification_sent_at = timezone.now()
        elif field == 'phone':
            self.phone_verification_code = code
            self.phone_verification_sent_at = timezone.now()
        
        self.save(update_fields=[
            f'{field}_verification_code',
            f'{field}_verification_sent_at'
        ])
        return code
    
    def is_verification_code_valid(self, code, field='email'):
        """Check if verification code is valid"""
        if field == 'email':
            if not self.email_verification_code or not self.email_verification_sent_at:
                return False
            if self.email_verification_code != code:
                return False
            expiry_time = self.email_verification_sent_at + timedelta(hours=24)
        else:  # phone
            if not self.phone_verification_code or not self.phone_verification_sent_at:
                return False
            if self.phone_verification_code != code:
                return False
            expiry_time = self.phone_verification_sent_at + timedelta(minutes=30)
        
        return timezone.now() <= expiry_time
    
    def verify_email(self):
        """Mark email as verified"""
        self.is_email_verified = True
        self.email_verified_at = timezone.now()
        self.email_verification_code = None
        self.email_verification_sent_at = None
        self.save()
    
    def verify_phone(self):
        """Mark phone as verified"""
        self.is_phone_verified = True
        self.phone_verified_at = timezone.now()
        self.phone_verification_code = None
        self.phone_verification_sent_at = None
        self.save()
    
    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def add_loyalty_points(self, points, reason=""):
        """Add loyalty points to user"""
        self.loyalty_points += points
        self.save()
        # Create history entry
        LoyaltyPointsHistory.objects.create(
            user=self,
            points=points,
            balance_after=self.loyalty_points,
            reason=reason
        )
    
    def get_default_shipping_address(self):
        """Get user's default shipping address"""
        return self.addresses.filter(is_default_shipping=True).first()
    
    def get_default_billing_address(self):
        """Get user's default billing address"""
        return self.addresses.filter(is_default_billing=True).first()
    
    def get_age_recommendations(self):
        """Get product recommendations based on child age"""
        if not self.child_age_range:
            return []
        
        age_map = {
            '0-6m': ['0-3m', '3-6m'],
            '6-12m': ['6-12m'],
            '1-2y': ['12-18m', '18-24m'],
            '2-3y': ['2-3y'],
            '3-4y': ['3-4y'],
            '4-5y': ['4-5y'],
            '5-6y': ['5-6y'],
        }
        return age_map.get(self.child_age_range, [])


class PasswordResetToken(models.Model):
    """Password reset tokens"""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        return not self.is_expired() and not self.is_used
    
    def mark_as_used(self):
        self.is_used = True
        self.used_at = timezone.now()
        self.save()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Reset token for {self.user.email}"


class UserAddress(models.Model):
    """User shipping and billing addresses"""
    
    # Kenya county choices
    KENYA_COUNTIES = [
        ('nairobi', 'Nairobi'),
        ('mombasa', 'Mombasa'),
        ('kisumu', 'Kisumu'),
        ('nakuru', 'Nakuru'),
        ('eldoret', 'Eldoret'),
        ('thika', 'Thika'),
        ('nyeri', 'Nyeri'),
        ('kakamega', 'Kakamega'),
        ('kisii', 'Kisii'),
        ('meru', 'Meru'),
        ('machakos', 'Machakos'),
        ('kitale', 'Kitale'),
        ('kericho', 'Kericho'),
        ('bungoma', 'Bungoma'),
        ('malindi', 'Malindi'),
        ('lamu', 'Lamu'),
        ('garissa', 'Garissa'),
        ('wajir', 'Wajir'),
        ('mandera', 'Mandera'),
        ('marsabit', 'Marsabit'),
        ('isiolo', 'Isiolo'),
        ('kitui', 'Kitui'),
        ('embu', 'Embu'),
        ('busia', 'Busia'),
        ('siaya', 'Siaya'),
        ('homa_bay', 'Homa Bay'),
        ('migori', 'Migori'),
        ('kilifi', 'Kilifi'),
        ('taita_taveta', 'Taita Taveta'),
        ('tana_river', 'Tana River'),
        ('west_pokot', 'West Pokot'),
        ('samburu', 'Samburu'),
        ('trans_nzoia', 'Trans Nzoia'),
        ('uasin_gishu', 'Uasin Gishu'),
        ('elgeyo_marakwet', 'Elgeyo Marakwet'),
        ('nandi', 'Nandi'),
        ('baringo', 'Baringo'),
        ('laikipia', 'Laikipia'),
        ('nakuru', 'Nakuru'),
        ('narok', 'Narok'),
        ('kajiado', 'Kajiado'),
        ('kericho', 'Kericho'),
        ('bomet', 'Bomet'),
        ('kakamega', 'Kakamega'),
        ('vihiga', 'Vihiga'),
        ('bungoma', 'Bungoma'),
        ('busia', 'Busia'),
        ('siaya', 'Siaya'),
        ('kisumu', 'Kisumu'),
        ('homa_bay', 'Homa Bay'),
        ('migori', 'Migori'),
        ('kisii', 'Kisii'),
        ('nyamira', 'Nyamira'),
        ('nairobi', 'Nairobi'),
        ('kiambu', 'Kiambu'),
        ('muranga', 'Murang\'a'),
        ('nyandarua', 'Nyandarua'),
        ('nyeri', 'Nyeri'),
        ('kirinyaga', 'Kirinyaga'),
        ('meru', 'Meru'),
        ('tharaka_nithi', 'Tharaka Nithi'),
        ('embu', 'Embu'),
        ('kitui', 'Kitui'),
        ('machakos', 'Machakos'),
        ('makueni', 'Makueni'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    
    # Contact info
    contact_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=20)
    
    # Address details for Kenya
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    estate = models.CharField(max_length=100, blank=True)  # Common in Kenya
    building = models.CharField(max_length=100, blank=True)  # Building name/number
    floor = models.CharField(max_length=50, blank=True)  # Floor/room number
    city = models.CharField(max_length=100)
    county = models.CharField(
        max_length=50,
        choices=KENYA_COUNTIES,
        default='nairobi'
    )
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="Kenya")
    
    # Address type for baby shop context
    address_type = models.CharField(
        max_length=20,
        choices=[
            ('home', 'Home (Family Residence)'),
            ('office', 'Office/Work'),
            ('grandparents', 'Grandparents House'),
            ('daycare', 'Daycare/Nursery'),
            ('relative', 'Relative\'s House'),
            ('other', 'Other'),
        ],
        default='home'
    )
    
    # Default flags with constraints
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)
    
    # Delivery instructions for baby clothes
    delivery_instructions = models.TextField(
        blank=True,
        help_text="Specific instructions for delivering baby clothes"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default_shipping', '-created_at']
        verbose_name_plural = "User Addresses"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'is_default_shipping'],
                condition=models.Q(is_default_shipping=True),
                name='unique_default_shipping_per_user'
            ),
            models.UniqueConstraint(
                fields=['user', 'is_default_billing'],
                condition=models.Q(is_default_billing=True),
                name='unique_default_billing_per_user'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'is_default_shipping']),
            models.Index(fields=['user', 'is_default_billing']),
            models.Index(fields=['county', 'city']),
        ]
    
    def __str__(self):
        return f"{self.contact_name} - {self.city}, {self.get_county_display()}"
    
    @property
    def full_address(self):
        """Get formatted full address"""
        parts = [
            self.contact_name,
            self.address_line_1,
            self.address_line_2,
            self.estate,
            self.building,
            self.floor,
            f"{self.city}, {self.get_county_display()} County",
            self.postal_code,
            self.country,
            f"Phone: {self.contact_phone}",
        ]
        if self.delivery_instructions:
            parts.append(f"Instructions: {self.delivery_instructions}")
        
        return "\n".join(filter(None, parts))
    
    def save(self, *args, **kwargs):
        # Ensure only one default shipping address per user
        if self.is_default_shipping:
            UserAddress.objects.filter(
                user=self.user, 
                is_default_shipping=True
            ).exclude(pk=self.pk).update(is_default_shipping=False)
        
        # Ensure only one default billing address per user
        if self.is_default_billing:
            UserAddress.objects.filter(
                user=self.user, 
                is_default_billing=True
            ).exclude(pk=self.pk).update(is_default_billing=False)
        
        super().save(*args, **kwargs)


class NotificationPreferences(models.Model):
    """Fine-grained notification settings"""
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='notification_prefs'
    )
    
    # Order notifications
    order_confirmation = models.BooleanField(default=True)
    order_shipped = models.BooleanField(default=True)
    order_delivered = models.BooleanField(default=True)
    order_cancelled = models.BooleanField(default=True)
    payment_confirmation = models.BooleanField(default=True)
    
    # Promotional notifications (baby shop specific)
    flash_sales = models.BooleanField(default=True)
    daily_deals = models.BooleanField(default=True)
    price_drop_alerts = models.BooleanField(default=False)
    new_arrivals = models.BooleanField(default=True)
    back_in_stock = models.BooleanField(default=True)
    baby_care_tips = models.BooleanField(default=True)
    
    # Account notifications
    security_alerts = models.BooleanField(default=True)
    account_updates = models.BooleanField(default=True)
    birthday_offers = models.BooleanField(default=True)
    
    # Social notifications
    reviews_replies = models.BooleanField(default=True)
    wishlist_reminders = models.BooleanField(default=True)
    abandoned_cart_reminders = models.BooleanField(default=True)
    
    # Delivery channels
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Preferences"
        verbose_name_plural = "Notification Preferences"
    
    def __str__(self):
        return f"Notification prefs for {self.user.email}"
    
    def save(self, *args, **kwargs):
        # Ensure at least one notification channel is enabled
        if not any([self.email_notifications, self.sms_notifications, self.push_notifications]):
            self.email_notifications = True
        super().save(*args, **kwargs)


class LoyaltyPointsHistory(models.Model):
    """Track loyalty points history"""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='loyalty_points_history'
    )
    points = models.IntegerField(help_text="Positive for addition, negative for deduction")
    balance_after = models.IntegerField()
    reason = models.CharField(max_length=255)
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loyalty_points_earned'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Loyalty Points History"
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['order', 'created_at']),
        ]
    
    def __str__(self):
        action = "added" if self.points > 0 else "deducted"
        return f"{abs(self.points)} points {action} for {self.user.email}"


class UserActivityLog(models.Model):
    """Log user activities"""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        null=True,
        blank=True
    )
    activity_type = models.CharField(max_length=50)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['activity_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.activity_type}"