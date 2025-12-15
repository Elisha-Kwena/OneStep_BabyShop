from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.mail import send_mail
from django.conf import settings
from ..models import CustomUser,PasswordResetToken

import re
import logging
logger = logging.getLogger(__name__)

from ..utils import send_verification_email,send_welcome_email


# ===================== Strong Password Validation =====================
def validate_strong_password(value):
    """Used in Register & Password Reset"""
    if len(value) < 8:
        raise serializers.ValidationError(_("Password must be at least 8 characters long."))

    if value.isdigit():
        raise serializers.ValidationError(_("Password cannot be entirely numeric."))

    if not re.search(r'[A-Za-z]', value):
        raise serializers.ValidationError(_("Password must contain at least one letter."))

    if not re.search(r'\d', value):
        raise serializers.ValidationError(_("Password must contain at least one number."))

    # Check common passwords
    try:
        CommonPasswordValidator().validate(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(_("This password is too common."))

    return value
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        validators=[validate_strong_password],
        min_length=8,
    )
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})


    class Meta:
        model = CustomUser
        fields = [
            'id','email', 'username', 'password', 'password_confirm'
        ]


    def validate_email(self,value):
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("A user with that email already exists"))
        return value
    def validate_username(self,value):
        if CustomUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(_("A user with that username already exists"))
        return value
    
    def validate(self,data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm":_("Password do not match.")})
        return data
    
    def create(self,validated_data):
        validated_data.pop("password_confirm",None)
        password = validated_data.pop("password")
        user = CustomUser.objects.create_user(
            email=validated_data['email'], 
            password=password, 
            **{k: v for k, v in validated_data.items() if k != 'email'}  # exclude email
            )
        
        email_sent = send_verification_email(user, is_resend=False)

        if not email_sent:
            logger.error(f"CRITICAL: Failed to send verification email to {user.email}")
    
        return user


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    verification_code = serializers.CharField(
        max_length=6, 
        min_length=6, 
        required=True,
        help_text="6-digit verification code"
    )

    def validate(self,data):
        email = data.get('email')
        verification_code = data.get('verification_code')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                "email":_("No user found with this email address")
            })
        
        if user.is_email_verified:
            raise serializers.ValidationError({
                "email":_("This email is already verified")
            })
        
        if not user.is_verification_code_valid(verification_code):
            raise serializers.ValidationError({
                "verification_code":_("Invalid or expired verification code")
            })
        
        data['user'] = user

        return data
    def save(self):
        user = self.validated_data['user']
        user.verify_email()

        send_welcome_email(user)
        return user
    

class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    def validate(self,data):
        email = data.get('email')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                "email": _("No user found with this email address.")
            })

        if user.is_email_verified:
            raise serializers.ValidationError({
                "email": _("This email is already verified.")
            }) 

        if user.email_verification_sent_at:
            time_since_last = timezone.now() - user.email_verification_sent_at
            if time_since_last < timedelta(minutes=2):
                raise serializers.ValidationError({
                    "email": _("Please wait 2 minutes before requesting a new code.")
                })          

        data['user'] = user
        return data
    
    def save(self):
        user = self.validated_data['user']
        user.generate_verification_code()

        email_sent = send_verification_email(user, is_resend=True)

        self._email_sent = email_sent

        if not email_sent:
            raise serializers.ValidationError({
                "email":_("Failed to send verification email. Please try again.")
            })
        
        return user


class VerifiedEmailLoginSerializer(TokenObtainPairSerializer):
    """Simple serializer that only checks if email is verified"""
    
    def validate(self, attrs):
        # First, let Django check username/password
        data = super().validate(attrs)
        
        # Then check if email is verified
        if not self.user.is_email_verified:
            raise serializers.ValidationError(
                _("Please verify your email address before logging in.")
            )
        
        return data
    


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self,attrs):
        self.token = attrs['refresh']
        return attrs
    
    def save(self,**kwargs):
        try:
            refresh_token = RefreshToken(self.token)
            refresh_token.blacklist()
            return True
        except TokenError as e:
            raise serializers.ValidationError(
                _("Invalid or expired token")
            )
        except Exception as e:
            raise serializers.ValidationError(
                _("An error occured during logout")
            )
        

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self,data):
        email = data.get('email')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                "email":"If this system exists in our System, you will receive a password reset link"
            })
        
        if not user.is_email_verified:
            raise serializers.ValidationError({
                "email":"Please verify your email before resetting password"
            })
        
        data['user']=user
        return data
    
class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_strong_password],
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self,data):
        token = data.get('token')
        password = data.get('password')
        password_confirm = data.get('password_confirm')

        if password != password_confirm:
            raise serializers.ValidationError({
                "password_confirm":"Passwords do not match!"
            })

        try:
            reset_token = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({
                "token":"Invalid or expired reset token!"
            })
        
        if not reset_token.is_valid():
            raise serializers.ValidationError({
                "token":"This reset link has expired or already been used."
            })
        
        data['reset_token'] = reset_token
        return data
    
    def save(self):
        reset_token = self.validated_data['reset_token']
        user = reset_token.user
        new_password = self.validated_data['password']

        user.set_password(new_password)
        user.save()

        reset_token.mark_as_used()

        # Logout user from all devices
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        from rest_framework_simplejwt.tokens import RefreshToken   

        tokens = OutstandingToken.objects.filter(user=user)
        for token in tokens:
            try:
                RefreshToken(token.token).blacklist()
            except:
                pass
        return user    




