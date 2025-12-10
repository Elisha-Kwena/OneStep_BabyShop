from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging
from datetime import timedelta
import uuid
from uuid import uuid4

import random

from .managers import CustomUserManager
class CustomUser(AbstractBaseUser,PermissionsMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    email = models.EmailField(
        verbose_name=_("email address"),
        max_length=255,
        unique=True,
        error_messages={
            'unique':_("A user with that email already exists")
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

    first_name = models.CharField(
        verbose_name=_("first_name"),
        max_length=255,
        blank=True
    )
    last_name = models.CharField(
        verbose_name=_("last_name"),
        max_length=255,
        blank=True
    )

    phone = models.CharField(
        verbose_name=_("phoneNumber"),
        max_length=20,
        blank=True,     
        null=True,       
        unique=True,     
        error_messages={
            'unique': _('A user with that phoneNumber already exists.'),
        }
    )

    avatar = models.ImageField(
        verbose_name=_('avatar'),
        upload_to='avatars/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text=_('Profile picture for the user.')
    )


    is_email_verified = models.BooleanField(
        verbose_name=_('email verified'),
        default=False,
        help_text=_('Designates whether the user has verified their email address.')
    ) 

    email_verification_code = models.CharField(
        verbose_name=_('email verification code'),
        max_length=6,
        blank=True,
        null=True,
        help_text=_('Six-digit verification code sent to email.')
    )

    is_active = models.BooleanField(
        verbose_name=_('active'),
        default=True,
        help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')
    )

    email_verification_sent_at = models.DateTimeField(
        verbose_name=_('verification code sent at'),
        blank=True,
        null=True,
        help_text=_('Timestamp when verification code was sent.')
    )

    is_staff = models.BooleanField(
        verbose_name=_('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.')
    )

    date_joined = models.DateTimeField(
        verbose_name=_('date joined'),
        default=timezone.now
    )


    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.username
    

    def generate_verification_code(self):
        code = ''.join([str(random.randint(0,9)) for _ in range(6)])
        self.email_verification_code = code
        self.email_verification_sent_at = timezone.now()
        self.save()

        return code
    
    def is_verification_code_valid(self,code):
        if not self.email_verification_code or not self.email_verification_sent_at:
            return False
        
        if self.email_verification_code != code:
            return False
        
        expiry_time = self.email_verification_sent_at + timedelta(hours=24)
        if timezone.now() > expiry_time:
            return False
        return True
    
    def verify_email(self):
        self.is_email_verified = True
        self.email_verified_at = timezone.now()
        self.email_verification_code = None
        self.email_verification_sent_at = None
        self.save()


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True,blank=True)


    def save(self,*args,**Kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args,**Kwargs)

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
    """User can have multiple addresses like Jumia."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    
    # Contact info for this address
    contact_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=20)
    
    # Address details
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="Nigeria")
    
    # Address type
    address_type = models.CharField(
        max_length=20,
        choices=[
            ('home', 'Home'),
            ('office', 'Office'),
            ('other', 'Other'),
        ],
        default='home'
    )
    
    # Default flags
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default_shipping', '-created_at']
        verbose_name_plural = "User Addresses"
    
    def __str__(self):
        return f"{self.contact_name} - {self.city}"
    


class NotificationPreferences(models.Model):
    """Fine-grained notification settings like Jumia."""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_prefs')
    
    # Order notifications
    order_confirmation = models.BooleanField(default=True)
    order_shipped = models.BooleanField(default=True)
    order_delivered = models.BooleanField(default=True)
    
    # Promotional notifications
    flash_sales = models.BooleanField(default=True)
    daily_deals = models.BooleanField(default=True)
    price_drop_alerts = models.BooleanField(default=False)
    
    # Account notifications
    security_alerts = models.BooleanField(default=True)
    account_updates = models.BooleanField(default=True)
    
    # Social notifications
    reviews_replies = models.BooleanField(default=True)
    wishlist_reminders = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification prefs for {self.user.email}"
    


class ChildInfo(models.Model):
    """Child information for baby clothing shop (up to 6 years)."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='children')
    
    # Basic Info
    name = models.CharField(
        max_length=100,
        help_text="Child's first name"
    )
    
    birth_date = models.DateField(
        help_text="Child's date of birth"
    )
    
    gender = models.CharField(
        max_length=100,
        choices=[
            ('male', 'Boy'),
            ('female', 'Girl'),
            ('prefer_not_to_say', 'Prefer not to say'),
        ],
        default='prefer_not_to_say'
    )
    
    # Clothing Sizes (up to 6 years)
    SIZE_CHOICES = [
        # Age-based sizes
        ('newborn', 'Newborn (NB) - Up to 3kg'),
        ('0-3m', '0-3 Months - 3-6kg'),
        ('3-6m', '3-6 Months - 6-8kg'),
        ('6-9m', '6-9 Months - 8-9kg'),
        ('9-12m', '9-12 Months - 9-10kg'),
        
        # Toddler sizes (1-2 years)
        ('12-18m', '12-18 Months - 10-11kg'),
        ('18-24m', '18-24 Months - 11-12kg'),
        
        # Preschool sizes (2-4 years)
        ('2t', '2T (2 Years) - 12-14kg'),
        ('3t', '3T (3 Years) - 14-16kg'),
        ('4t', '4T (4 Years) - 16-18kg'),
        
        # Early childhood (5-6 years)
        ('5t', '5T (5 Years) - 18-20kg'),
        ('6t', '6T (6 Years) - 20-22kg'),
    ]
    
    current_size = models.CharField(
        max_length=10,
        choices=SIZE_CHOICES,
        blank=True,
        help_text="Current clothing size"
    )
    
    # Optional: Growth tracking
    height = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Height in centimeters (optional)"
    )
    
    weight = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Weight in kilograms (optional)"
    )
    
    # Preferences (for personalized recommendations)
    favorite_colors = models.JSONField(
        default=list,
        blank=True,
        help_text="Child's favorite colors"
    )
    
    style_preference = models.CharField(
        max_length=50,
        choices=[
            ('casual', 'Casual'),
            ('formal', 'Formal'),
            ('playful', 'Playful'),
            ('sporty', 'Sporty'),
            ('mix', 'Mix of everything'),
        ],
        default='casual',
        blank=True
    )
    
    # Special notes
    allergies = models.TextField(
        blank=True,
        help_text="Any fabric/material allergies (e.g., wool allergy)"
    )
    
    special_notes = models.TextField(
        blank=True,
        help_text="Any special requirements (e.g., sensory-friendly fabrics)"
    )
    
    # Active status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this child profile is currently active"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Child Information"
        verbose_name_plural = "Children Information"
        ordering = ['-birth_date']
        unique_together = ['user', 'name', 'birth_date']
    
    def __str__(self):
        return f"{self.name} ({self.age_display})"
    
    # Property methods
    @property
    def age_years(self):
        """Calculate age in years."""
        from datetime import date
        today = date.today()
        age = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            age -= 1
        return age
    
    @property
    def age_months(self):
        """Calculate age in months."""
        from datetime import date
        today = date.today()
        months = (today.year - self.birth_date.year) * 12 + (today.month - self.birth_date.month)
        if today.day < self.birth_date.day:
            months -= 1
        return months
    
    @property
    def age_display(self):
        """Display age in user-friendly format."""
        years = self.age_years
        months = self.age_months
        
        if years >= 1:
            if years == 1:
                return "1 year old"
            elif years < 7:
                return f"{years} years old"
        else:
            if months == 1:
                return "1 month old"
            elif months < 24:
                return f"{months} months old"
        
        return f"{years} years {months % 12} months"
    
    @property
    def recommended_size(self):
        """Recommend clothing size based on age."""
        if self.current_size:
            return self.current_size
        
        months = self.age_months
        
        if months <= 3:
            return 'newborn'
        elif months <= 6:
            return '0-3m'
        elif months <= 9:
            return '3-6m'
        elif months <= 12:
            return '6-9m'
        elif months <= 18:
            return '9-12m'
        elif months <= 24:
            return '12-18m'
        elif months <= 36:
            return '2t'
        elif months <= 48:
            return '3t'
        elif months <= 60:
            return '4t'
        elif months <= 72:
            return '5t'
        else:
            return '6t'
    
    @property
    def next_size(self):
        """Predict next size based on age."""
        months = self.age_months
        
        size_mapping = {
            'newborn': '0-3m',
            '0-3m': '3-6m',
            '3-6m': '6-9m',
            '6-9m': '9-12m',
            '9-12m': '12-18m',
            '12-18m': '18-24m',
            '18-24m': '2t',
            '2t': '3t',
            '3t': '4t',
            '4t': '5t',
            '5t': '6t',
            '6t': '6t',  # Max size
        }
        
        current = self.recommended_size
        return size_mapping.get(current, current)
    
    @property
    def growth_percentile(self):
        """Calculate growth percentile (simplified)."""
        if not self.height or not self.weight or not self.birth_date:
            return None
        
        # Simplified percentile calculation (in real app, use WHO charts)
        months = self.age_months
        
        # Very basic example - in reality, use WHO growth standards
        if months <= 12:
            if self.weight < 7:
                return '10th'
            elif self.weight < 9:
                return '50th'
            else:
                return '90th'
        elif months <= 36:
            if self.weight < 12:
                return '10th'
            elif self.weight < 15:
                return '50th'
            else:
                return '90th'
        else:
            if self.weight < 16:
                return '10th'
            elif self.weight < 20:
                return '50th'
            else:
                return '90th'
    
    @property
    def needs_size_update(self):
        """Check if size might need updating based on age."""
        months = self.age_months
        last_updated_months = (timezone.now().date() - self.updated_at.date()).days // 30
        
        # Suggest update every 3 months for infants, 6 months for toddlers
        if months < 12:
            return last_updated_months >= 3
        elif months < 36:
            return last_updated_months >= 6
        else:
            return last_updated_months >= 12
    
    def save(self, *args, **kwargs):
        # Auto-calculate current size if not set
        if not self.current_size:
            self.current_size = self.recommended_size
        
        # Ensure name is capitalized
        if self.name:
            self.name = self.name.strip().title()
        
        super().save(*args, **kwargs)

