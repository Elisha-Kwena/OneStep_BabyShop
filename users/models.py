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