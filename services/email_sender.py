import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
TO_EMAIL = os.getenv('TO_EMAIL')

def send_email(subject, body):
  msg = EmailMessage()
  msg['from'] = EMAIL_ADDRESS
  msg['To'] = TO_EMAIL
  msg['Subject'] = subject
  msg.set_content(body)

  with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    smtp.send_message(msg)