"""
Email notification service
"""
import aiosmtplib
from email.message import EmailMessage
from typing import List, Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Send email notifications"""
    
    def __init__(self):
        self.smtp_host = getattr(settings, 'smtp_host', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_user = getattr(settings, 'smtp_user', '')
        self.smtp_password = getattr(settings, 'smtp_password', '')
        self.from_email = getattr(settings, 'from_email', 'noreply@pragyaa.ai')
        self.enabled = bool(self.smtp_user and self.smtp_password)
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """Send an email"""
        if not self.enabled:
            logger.warning("Email service not configured")
            return False
        
        try:
            message = EmailMessage()
            message["From"] = self.from_email
            message["To"] = ", ".join(to_emails)
            message["Subject"] = subject
            message.set_content(body)
            
            if html_body:
                message.add_alternative(html_body, subtype="html")
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True
            )
            
            logger.info(f"Email sent to {to_emails}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def send_model_down_alert(self, model_id: str, error: str):
        """Send alert when model goes down"""
        subject = f"🚨 Alert: Model '{model_id}' is Down"
        body = f"""
ML Gateway Alert

Model: {model_id}
Status: DOWN
Error: {error}
Time: {datetime.utcnow().isoformat()}

Please check the model endpoint and restart if needed.

- ML Gateway Admin
"""
        
        admin_emails = ["gulshan@pragyaa.ai", "manoj@pragyaa.ai", "krishna@pragyaa.ai"]
        await self.send_email(admin_emails, subject, body)
    
    async def send_high_error_rate_alert(self, model_id: str, error_rate: float):
        """Send alert for high error rate"""
        subject = f"⚠️ Warning: High Error Rate for '{model_id}'"
        body = f"""
ML Gateway Warning

Model: {model_id}
Error Rate: {error_rate:.1f}%
Threshold: 10%
Time: {datetime.utcnow().isoformat()}

The model is experiencing elevated error rates. Please investigate.

- ML Gateway Admin
"""
        
        admin_emails = ["gulshan@pragyaa.ai", "manoj@pragyaa.ai", "krishna@pragyaa.ai"]
        await self.send_email(admin_emails, subject, body)


from datetime import datetime

# Global email service
email_service = EmailService()
