# users/managers.py
from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        """Create regular user"""
        if not email:
            raise ValueError("Email required")
        if not username:
            raise ValueError("Username required")
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self.db)
        return user
    
    def create_superuser(self, email, username=None, password=None, **extra_fields):
        """Create superuser - username is optional"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_email_verified', True)
        
        # If username not provided, use part of email
        if username is None:
            username = email.split('@')[0]
        
        # Ensure unique phone
        if 'phone' not in extra_fields:
            extra_fields['phone'] = 'admin-0000000000'

        return self.create_user(email, username, password, **extra_fields)