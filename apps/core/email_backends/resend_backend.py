"""
Resend Email Backend for Django.

Uses the Resend API to send emails instead of SMTP.
"""
import logging
import resend
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
from django.core.mail.message import sanitize_address

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """
    Email backend that sends emails via Resend API.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = getattr(settings, 'RESEND_API_KEY', None)
        if not self.api_key:
            raise ValueError("RESEND_API_KEY must be set in settings or environment variables")
        resend.api_key = self.api_key

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not email_messages:
            return 0

        num_sent = 0
        for message in email_messages:
            try:
                self._send(message)
                num_sent += 1
            except Exception as e:
                logger.error(f"Failed to send email via Resend: {e}")
                if not self.fail_silently:
                    raise

        return num_sent

    def _send(self, email_message):
        """Send a single email message via Resend API."""
        # Prepare from address
        from_email = sanitize_address(email_message.from_email, email_message.encoding)
        
        # Prepare recipients
        recipients = [sanitize_address(addr, email_message.encoding) 
                      for addr in email_message.recipients()]
        
        # Prepare subject
        subject = email_message.subject
        
        # Prepare HTML and text content
        html_content = None
        text_content = None
        
        if email_message.content_subtype == 'html':
            html_content = email_message.body
        else:
            text_content = email_message.body
            
        # Check for multipart/alternative (both text and html)
        if hasattr(email_message, 'alternatives'):
            for content, mimetype in email_message.alternatives:
                if mimetype == 'text/html':
                    html_content = content
                elif mimetype == 'text/plain':
                    text_content = content
        
        # Prepare the email data for Resend
        email_data = {
            "from": email_message.from_email,
            "to": recipients,
            "subject": subject,
        }
        
        if html_content:
            email_data["html"] = html_content
        if text_content:
            email_data["text"] = text_content
        
        # Send via Resend API
        try:
            response = resend.Emails.send(email_data)
            logger.info(f"Email sent via Resend: {response.get('id')}")
        except Exception as e:
            logger.error(f"Resend API error: {e}")
            if not self.fail_silently:
                raise
            return False
        
        return True


# For backward compatibility, also provide a simple function-based interface
def send_email_via_resend(from_email, to_emails, subject, html_content=None, text_content=None):
    """
    Simple function to send email via Resend.
    
    Args:
        from_email: Sender email address
        to_emails: List of recipient email addresses
        subject: Email subject
        html_content: HTML content (optional)
        text_content: Plain text content (optional)
    
    Returns:
        dict: Resend API response
    """
    email_data = {
        "from": from_email,
        "to": to_emails if isinstance(to_emails, list) else [to_emails],
        "subject": subject,
    }
    
    if html_content:
        email_data["html"] = html_content
    if text_content:
        email_data["text"] = text_content
    
    return resend.Emails.send(email_data)