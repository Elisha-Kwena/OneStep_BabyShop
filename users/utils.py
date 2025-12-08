# users/utils.py
from django.utils import timezone
import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import threading  # ← This is the magic

logger = logging.getLogger(__name__)


def get_email_context(user=None, **extra_context):
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


# ———————————————————— ASYNC EMAIL SENDERS ———————————————————— #
def _send_email_async(email_message):
    """Actually sends the email in a background thread"""
    try:
        email_message.send(fail_silently=True)
    except Exception as e:
        logger.error(f"Async email failed: {str(e)}", exc_info=True)


def send_async_email(email_message):
    """Fire-and-forget email — request returns instantly"""
    thread = threading.Thread(target=_send_email_async, args=(email_message,), daemon=True)
    thread.start()
# —————————————————————————————————————————————————————————————— #


def send_verification_email(user, is_resend=False):
    try:
        if not user.email_verification_code:
            user.generate_verification_code()
        
        context = get_email_context(
            user=user,
            verification_code=user.email_verification_code,
            is_resend=is_resend,
        )
        
        if is_resend:
            subject = _("Your New Verification Code - {site_name}").format(site_name=context['site_name'])
        else:
            subject = _("Verify Your Email Address - {site_name}").format(site_name=context['site_name'])
        
        html_content = render_to_string('emails/verification_email.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            reply_to=[context['support_email']],
        )
        email.attach_alternative(html_content, "text/html")
        
        # This returns instantly — email sends in background
        send_async_email(email)
        
        logger.info(f"Verification email queued for {user.email} (resend: {is_resend})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to queue verification email: {str(e)}", exc_info=True)
        return False


def send_welcome_email(user):
    try:
        context = get_email_context(user=user)
        subject = _("Welcome to {site_name}!").format(site_name=context['site_name'])
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
        send_async_email(email)
        
        logger.info(f"Welcome email queued for {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to queue welcome email: {str(e)}")
        return False


def send_email_with_template(to_email, subject_template, html_template, context):
    try:
        full_context = get_email_context()
        full_context.update(context)
        subject = subject_template.format(**full_context)
        html_content = render_to_string(html_template, full_context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.attach_alternative(html_content, "text/html")
        send_async_email(email)
        
        logger.info(f"Custom email queued to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to queue custom email: {str(e)}")
        return False


def send_password_reset_email(user, reset_token):
    try:
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password/{reset_token}"
        context = get_email_context(user=user, reset_url=reset_url)
        
        subject = _("Reset Your Password - {site_name}").format(site_name=context['site_name'])
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
        send_async_email(email)
        
        logger.info(f"Password reset email queued for {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to queue password reset email: {str(e)}")
        return False


def send_password_reset_success_email(user, request=None):
    try:
        context = get_email_context(user=user)
        context.update({
            'changed_at': timezone.now(),
            'ip_address': request.META.get('REMOTE_ADDR') if request else 'Unknown',
            'login_url': f"{context['frontend_url']}/login"
        })
        
        subject = _("Password Updated - {site_name}").format(site_name=context['site_name'])
        html_content = render_to_string('emails/password_reset_success.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")
        send_async_email(email)
        
        logger.info(f"Password reset success email queued for {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to queue password reset success email: {str(e)}")
        return False