# users/utils.py - USING BREVO SMTP with ASYNC sending
from django.core.mail import send_mail
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
import logging
import threading

logger = logging.getLogger(__name__)

def get_email_context(user=None, **extra_context):
    context = {
        'site_name': getattr(settings, 'SITE_NAME', 'BabyShop'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'hatblack9874@gmail.com'),  # Fixed email
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'frontend_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
    }
    if user:
        context.update({
            'user': user,
            'username': user.username,
            'email': user.email,
        })
    context.update(extra_context)
    return context

# ASYNC EMAIL SENDING FUNCTION
def send_verification_email_async(user, is_resend=False):
    """Send verification email in background thread to avoid timeout"""
    def _send_email_in_background():
        try:
            if not user.email_verification_code:
                user.generate_verification_code()

            context = get_email_context(
                user=user,
                verification_code=user.email_verification_code,
                is_resend=is_resend,
            )

            subject = (
                _("Your New Verification Code - {site_name}").format(site_name=context['site_name'])
                if is_resend else
                _("Verify Your Email Address - {site_name}").format(site_name=context['site_name'])
            )

            # Simple HTML if template missing
            html_content = f"""
            <h2>Welcome to {context['site_name']}! 👶</h2>
            <p>Your verification code: <strong>{user.email_verification_code}</strong></p>
            <p>Enter this code to complete your registration.</p>
            <p><small>If you didn't request this, please ignore this email.</small></p>
            """
            plain_text = f"Your verification code: {user.email_verification_code}"

            # Use Django's send_mail with fail_silently=True
            send_mail(
                subject=subject,
                message=plain_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=True,  # Don't crash app if email fails
            )
            
            logger.info(f"✅ Verification email sent to {user.email}")
            
        except Exception as e:
            logger.error(f"❌ Background email failed for {user.email}: {str(e)}")
    
    # Start email sending in background thread
    email_thread = threading.Thread(target=_send_email_in_background, daemon=True)
    email_thread.start()
    
    # Return True immediately (email is processing in background)
    logger.info(f"📧 Email process started for {user.email}")
    return True

# Keep original function but make it use async version
def send_verification_email(user, is_resend=False):
    """Public wrapper - uses async version"""
    return send_verification_email_async(user, is_resend)

# ASYNC WELCOME EMAIL
def send_welcome_email_async(user):
    """Send welcome email in background"""
    def _send_welcome():
        try:
            context = get_email_context(user=user)
            subject = _("Welcome to {site_name}!").format(site_name=context['site_name'])
            html_content = f"""
            <h2>Welcome to {context['site_name']}, {user.username}! 🎉</h2>
            <p>Your account has been successfully created.</p>
            <p>Start browsing our baby products and enjoy your shopping experience!</p>
            """
            plain_text = f"Welcome to {context['site_name']}, {user.username}!"

            send_mail(
                subject=subject,
                message=plain_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=True,
            )
            logger.info(f"✅ Welcome email sent to {user.email}")
        except Exception as e:
            logger.error(f"Welcome email failed: {e}")
    
    threading.Thread(target=_send_welcome, daemon=True).start()
    return True

def send_welcome_email(user):
    """Public wrapper"""
    return send_welcome_email_async(user)

# ASYNC PASSWORD RESET EMAIL
def send_password_reset_email_async(user, reset_token):
    """Send password reset email in background"""
    def _send_reset():
        try:
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_url = f"{frontend_url}/reset-password/{reset_token}"
            context = get_email_context(user=user, reset_url=reset_url)
            subject = _("Reset Your Password - {site_name}").format(site_name=context['site_name'])
            html_content = f"""
            <h2>Password Reset Request</h2>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
            <p>Or copy this link: {reset_url}</p>
            <p><small>This link expires in 24 hours.</small></p>
            """
            plain_text = f"Reset your password: {reset_url}"

            send_mail(
                subject=subject,
                message=plain_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=True,
            )
            logger.info(f"✅ Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Password reset email failed: {e}")
    
    threading.Thread(target=_send_reset, daemon=True).start()
    return True

def send_password_reset_email(user, reset_token):
    """Public wrapper"""
    return send_password_reset_email_async(user, reset_token)