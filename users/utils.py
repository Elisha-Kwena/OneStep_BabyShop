# users/utils.py
from django.utils import timezone
import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def get_email_context(user=None, **extra_context):
    """
    Get common context for all email templates.
    """
    context = {
        'site_name': getattr(settings, 'SITE_NAME', 'Your Site'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com'),
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
    """
    Send HTML verification email with 6-digit code.
    """
    try:
        # Generate verification code if needed
        if not user.email_verification_code:
            user.generate_verification_code()
        
        # Prepare context
        context = get_email_context(
            user=user,
            verification_code=user.email_verification_code,
            is_resend=is_resend,
        )
        
        # Subject
        if is_resend:
            subject = _("Your New Verification Code - {site_name}").format(
                site_name=context['site_name']
            )
        else:
            subject = _("Verify Your Email Address - {site_name}").format(
                site_name=context['site_name']
            )
        
        # Render HTML template
        html_content = render_to_string('emails/verification_email.html', context)
        
        # Create plain text version (important for email clients)
        text_content = strip_tags(html_content)
        
        # Send email with both HTML and plain text versions
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,  # Plain text version
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            reply_to=[context['support_email']],
        )
        
        # Attach HTML version
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        logger.info(f"HTML verification email sent to {user.email} (resend: {is_resend})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}", 
                     exc_info=True)
        return False


def send_welcome_email(user):
    """
    Send HTML welcome email after successful verification.
    """
    try:
        context = get_email_context(user=user)
        
        subject = _("Welcome to {site_name}!").format(
            site_name=context['site_name']
        )
        
        # Render HTML template
        html_content = render_to_string('emails/welcome_email.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            reply_to=[context['support_email']],
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"HTML welcome email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        return False


def send_email_with_template(to_email, subject_template, html_template, context):
    """
    Generic function to send any HTML email.
    
    Usage:
        send_email_with_template(
            to_email='user@example.com',
            subject_template='Welcome {username}!',
            html_template='emails/custom_email.html',
            context={'username': 'John'}
        )
    """
    try:
        # Add base context
        full_context = get_email_context()
        full_context.update(context)
        
        # Render subject (allowing template variables in subject)
        subject = subject_template.format(**full_context)
        
        # Render HTML content
        html_content = render_to_string(html_template, full_context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Email sent to {to_email} with template {html_template}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False
    
# ==========================password rest==================================================
def send_password_reset_email(user, reset_token):
    """Send password reset email with token"""
    try:
        # Create reset URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password/{reset_token}"
        
        context = get_email_context(user=user, reset_url=reset_url)
        
        subject = _("Reset Your Password - {site_name}").format(
            site_name=context['site_name']
        )
        
        # Render HTML template
        html_content = render_to_string('emails/password_reset.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            reply_to=[context['support_email']],
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Password reset email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        return False


def send_password_reset_success_email(user, request=None):
    """Send confirmation email after password reset"""
    try:
        context = get_email_context(user=user)
        
        # Add additional context
        context.update({
            'changed_at': timezone.now(),
            'ip_address': request.META.get('REMOTE_ADDR') if request else 'Unknown',
            'login_url': f"{context['frontend_url']}/login"
        })
        
        subject = _("Password Updated - {site_name}").format(
            site_name=context['site_name']
        )
        
        html_content = render_to_string('emails/password_reset_success.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Password reset success email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset success email: {str(e)}")
        return False