from django.conf import settings

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email


def send_email_confirmation(to_email: str, username: str, session_uid: str) -> bool:
    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=to_email,
        subject="Email Confirmation",
        html_content=f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 8px; background-color: #f9f9f9;">
  <h2 style="color: #333;">Welcome, {username} 👋</h2>
  <p style="font-size: 16px; color: #555;">
    Thank you for registering with us!
  </p>
  <p style="font-size: 16px; color: #555;">
    Please confirm your email address to activate your account. Once confirmed, you’ll be redirected to set your password and get started.
  </p>
  <div style="text-align: center; margin: 30px 0;">
    <a href="http://127.0.0.1:8000/api/auth/{session_uid}/password-set"
       style="background-color: #007bff; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
      Confirm Email & Set Password
    </a>
  </div>
  <p style="font-size: 14px; color: #888;">
    If you didn’t sign up, you can safely ignore this email.
  </p>
  <p style="font-size: 14px; color: #888;">
    — Raptor Tech
  </p>
</div>
""",
    )
    message.reply_to = Email("raptortech2025@gmail.com")

    try:
        sg = SendGridAPIClient(settings.EMAIL_SEND_API_KEY)

        response = sg.send(message)

        print(f"Email sent: {response.status_code}")

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
