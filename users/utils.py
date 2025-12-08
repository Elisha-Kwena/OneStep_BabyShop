# users/utils.py - USING BREVO SMTP (Django's built-in)
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
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'elishakwena@gmaiell.com'),
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

def send_verification_email(user, is_resend=False):
    """Send verification email using Brevo SMTP"""
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

        html_content = render_to_string('emails/verification_email.html', context)
        plain_text = f"Your verification code: {user.email_verification_code}"

        # Use Django's send_mail (will use Brevo SMTP from settings)
        send_mail(
            subject=subject,
            message=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"✅ Verification email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send verification email: {str(e)}", exc_info=True)
        return False

def send_welcome_email(user):
    """Send welcome email"""
    try:
        context = get_email_context(user=user)
        subject = _("Welcome to {site_name}!").format(site_name=context['site_name'])
        html_content = render_to_string('emails/welcome_email.html', context)
        plain_text = f"Welcome to {context['site_name']}, {user.username}!"

        send_mail(
            subject=subject,
            message=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Welcome email failed: {e}")
        return False

def send_password_reset_email(user, reset_token):
    """Send password reset email"""
    try:
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password/{reset_token}"
        context = get_email_context(user=user, reset_url=reset_url)
        subject = _("Reset Your Password - {site_name}").format(site_name=context['site_name'])
        html_content = render_to_string('emails/password_reset.html', context)
        plain_text = f"Reset your password: {reset_url}"

        send_mail(
            subject=subject,
            message=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Password reset email failed: {e}")
        return False