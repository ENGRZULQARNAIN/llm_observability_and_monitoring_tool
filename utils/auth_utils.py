import secrets
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import shortuuid
from core.config import Settings
from modules.Auth.models import Users
from dotenv import load_dotenv
import os
load_dotenv()
import bcrypt

class AuthManager:
    def __init__(self):
        self.settings = Settings()
        self.base_url = self.settings.BASE_URL
        
        # Email settings
        self.smtp_server = "smtp.hostinger.com"
        self.smtp_port = 465
        self.sender_email = "obamai@sarihorganics.com"
        self.smtp_password = self.settings.EMAIL_PASSWORD

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

    def get_password_hash(self, password: str) -> str:
        pwd_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password=pwd_bytes, salt=salt)

    def generate_verification_token(self) -> str:
        return secrets.token_urlsafe(16)

    def generate_verification_code(self) -> str:
        return secrets.token_hex(3).upper()

    def generate_unique_user_id(self, db: Session) -> str:
        unique_id = str(shortuuid.uuid())
        while db.query(Users).filter(Users.user_id == unique_id).first():
            unique_id = str(shortuuid.uuid())
        return unique_id

    def send_verification_email(self, receiver: str, good_name: str, verification_token: str) -> None:
        subject = "ACCOUNT VERIFICATION LINK (OBAM AI)"
        html_body = self._generate_verification_email_template(good_name, verification_token)
        self._send_email(receiver, subject, html_body)

    def send_reset_password_email(self, receiver: str, good_name: str, reset_token: str) -> None:
        subject = "Password Reset Link (OBAM AI)"
        html_body = self._generate_reset_password_email_template(good_name, reset_token)
        self._send_email(receiver, subject, html_body)

    def _send_email(self, receiver: str, subject: str, html_body: str) -> None:
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = receiver
        message["Subject"] = subject
        message.attach(MIMEText(html_body, "html"))

        context = ssl.create_default_context()
        
        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                server.login(self.sender_email, self.smtp_password)
                server.sendmail(self.sender_email, receiver, message.as_string())
        except Exception as e:
            print(f"Failed to send email: {e}")

    def _generate_verification_email_template(self, good_name: str, verification_token: str) -> str:
        body = f"""<!DOCTYPE html>
        <html>
          <head>
            <style>
              * {{
                font-family: "Montserrat", sans-serif;
                color:#000000;
              }}
              ul li {{
                  margin-bottom:5px;
              }}
              body {{
                font-family: Arial, sans-serif;
                background-color: #b3daff;
                color: #000000;
                padding:20px;
              }}
              .container {{
                max-width: 100%;
                color: white;
                margin: 0 auto;
                padding: 20px;
                border: 1px solid white;
                background-color: #EFF3EA;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
              }}
              .footer-like {{
                margin-top: auto;
                padding: 6px;
                text-align: center;
              }}
              .footer-like p {{
                margin: 0;
                padding: 4px;
                color: #fafafa;
                font-family: "Raleway", sans-serif;
                letter-spacing: 1px;
              }}
              .footer-like p a {{
                text-decoration: none;
                font-weight: 600;
              }}
              .logo {{
                width: 150px;
                border:1px solid #8a3aff;
              }}
              .verify-button {{
                text-decoration:none;
                background-color:#8a3aff;
                border-radius:5px;
                padding:10px;
                border: none;
              }}
            </style>
          </head>
          <body>
            <div class="container">
              <img src="https://sarihorganics.com/wp-content/uploads/2024/12/Purple_and_White_Modern_AI_Technology_Logo-removebg.png" alt="our logo" border="0" class="logo" />
              <p>Dear {good_name},</p>
              <h1><strong>Welcome to the OBAM AI!</strong></h1>
              <p>Your Account Verification Link is placed below. Click on the link to get verified:</p>
              <h4><b><a href="{self.base_url}verify?token={verification_token}" class="verify-button" style="color:#b3daff;">Click here to Verify Your Account</a></b></h4>
              <p><b>Sincerely,</b><br />The OBAM AI Team</p>
              <div class="footer-like">
                <p>
                  Powered by OBAM AI
                </p>
              </div>
            </div>
          </body>
        </html>"""
        return body

    def _generate_reset_password_email_template(self, good_name: str, reset_token: str) -> str:
        body = f"""<!DOCTYPE html>
        <html>
          <head>
            <style>
              * {{
                font-family: "Montserrat", sans-serif;
                color:#000000;
              }}
              ul li {{
                  margin-bottom:5px;
              }}
              body {{
                font-family: Arial, sans-serif;
                background-color: #b3daff;
                color: #000000;
                font-family: "Montserrat", sans-serif;
                padding:20px;
              }}
              .container {{
                max-width: 100%;
                color: white;
                margin: 0 auto;
                padding: 20px;
                border: 1px solid white;
                background-color: #EFF3EA;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
              }}
              .footer-like {{
                margin-top: auto;
                padding: 6px;
                text-align: center;
              }}
              .footer-like p {{
                margin: 0;
                padding: 4px;
                color: #fafafa;
                font-family: "Raleway", sans-serif;
                letter-spacing: 1px;
              }}
              .footer-like p a {{
                text-decoration: none;
                font-weight: 600;
              }}
              .logo {{
                width: 150px;
                border:1px solid #8a3aff;
              }}
              .verify-button {{
                background-color:#8a3aff;
                border-radius:5px;
                padding:10px;
                border: none;
                text-decoration:none;
              }}
            </style>
          </head>
          <body>
            <div class="container">
              <img src="https://sarihorganics.com/wp-content/uploads/2024/12/Purple_and_White_Modern_AI_Technology_Logo-removebg.png" 
                   alt="OBAM-Logo" border="0" class="logo" />
              <p>Dear {good_name},</p>
              <h1><strong>Password Reset Request - OBAM AI</strong></h1>
              <p>We received a request to reset your password. Click the button below to set a new password:</p>
              <h4><b><a href="{self.base_url}update-reset-password/{reset_token}" 
                   class="verify-button" style="color:#b3daff;">Reset Your Password</a></b></h4>
              <p>If you didn't request this password reset, you can safely ignore this email.</p>
              <p><b>Sincerely,</b><br />The OBAM AI Team</p>
              <div class="footer-like">
                <p>
                  Powered by OBAM AI
                </p>
              </div>
            </div>
          </body>
        </html>"""
        return body
