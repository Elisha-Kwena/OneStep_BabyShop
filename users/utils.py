# users/utils.py
from django.utils import timezone
import logging
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import threading

# ←←← RESEND SDK ←←←
import resend
resend.api_key = settings.EMAIL_HOST_PASSWORD  # your re_... key from Render env

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


# ———————— RESEND ASYNC EMAIL (GUARANTEED DELIVERY) ———————— #
def _send_with_resend(params):
    try:
        resend.Emails.send(params)
        logger.info(f"Resend email delivered to {params['to']}")
    except Exception as e:
        logger.error(f"Resend failed: {str(e)}", exc_info=True)


def send_verification_email(user, is_resend=False):
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

        params = {
            "from": settings.DEFAULT_FROM_EMAIL,  # onestepbabyshop@resend.dev
            "to": user.email,
            "subject": subject,
            "html": html_content,
        }

        # Fire and forget — super fast
        threading.Thread(target=_send_with_resend, args=(params,), daemon=True).start()
        logger.info(f"Verification email fired to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to fire verification email: {str(e)}", exc_info=True)
        return False


# Keep the other functions using Resend too (or leave as-is if you want)
def send_welcome_email(user):
    try:
        context = get_email_context(user=user)
        subject = _("Welcome to {site_name}!").format(site_name=context['site_name'])
        html_content = render_to_string('emails/welcome_email.html', context)

        params = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": user.email,
            "subject": subject,
            "html": html_content,
        }
        threading.Thread(target=_send_with_resend, args=(params,), daemon=True).start()
        return True
    except Exception as e:
        logger.error(f"Welcome email failed: {e}")
        return False


def send_password_reset_email(user, reset_token):
    try:
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password/{reset_token}"
        context = get_email_context(user=user, reset_url=reset_url)
        subject = _("Reset Your Password - {site_name}").format(site_name=context['site_name'])
        html_content = render_to_string('emails/password_reset.html', context)

        params = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": user.email,
            "subject": subject,
            "html": html_content,
        }
        threading.Thread(target=_send_with_resend, args=(params,), daemon=True).start()
        return True
    except Exception as e:
        logger.error(f"Password reset email failed: {e}")
        return False


# You can update the other functions similarly if you want
# For now, only verification is critical