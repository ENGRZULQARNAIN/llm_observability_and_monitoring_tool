import secrets
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from passlib.context import CryptContext
from core.config import Settings
import shortuuid
from sqlalchemy.orm import Session
from modules.Auth.models import Users

settings = Settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# from core.config import Settings

BASE_URL = settings.BASE_URL
def send_verifiaction_code_on_email(receiver,good_name,verification_token):

    port = 465 # For starttls
    smtp_server = "smtp.hostinger.com,"
    sender_email = "support@sarihorganics.com"
    receiver_email = receiver
    subject = "Password Reset Link (OBAM AI)"
    password = "Support@4791"

    body="""<!DOCTYPE html>
    <html>
      <head>
        <style>
          * {
            font-family: "Montserrat", sans-serif;
            color:#000000;
          }
          ul li
            {
                margin-bottom:5px;
            }
          body {
            font-family: Arial, sans-serif;
            background-color: #b3daff;
            color: #000000;
            font-family: "Montserrat", sans-serif;
            padding:20px;
          }
          .container {
            max-width: 100%;
            color: white;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid white;
            background-color: #b3daff;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
          }

          .footer-like {
            margin-top: auto;
            padding: 6px;
            text-align: center;
          }
          .footer-like p {
            margin: 0;
            padding: 4px;
            color: #fafafa;
            font-family: "Raleway", sans-serif;
            letter-spacing: 1px;
          }
          .footer-like p a {
            text-decoration: none;
            font-weight: 600;
          }

          .logo {
            width: 100px;
            border:1px solid white;
          }
          .verify-button
          {
          text-decoration:none;
          background-color:#009933;
          border-radius:5px;
          padding:10px;
          border: none;
          text-decoration:none;
          }
        </style>
      </head>
      <body>
        <div class="container">
    <img src="https://i.ibb.co/2k2YhLC/image-.png" alt="our logo" border="0" class="logo" />
    """
    body += f'<p>Dear {good_name},</p>' \
            f'<h1><strong>Welcome to the OBAM AI!</strong></h1>' \
            f'<p>Your Account Verification Link is placed below. Click on the link to get verified:</p>' \
            f'<h4><b><a href="{BASE_URL}verify?token={verification_token}" class="verify-button" style="color:#b3daff;">Click here to Verify Your Account</a></b></h4>'
    body+="""
          <p><b>Sincerely,</b><br />The OBAM AI Team</p>
          <div class="footer-like">
            <p>
              Powered by OBAM AI
            </p>
          </div>
        </div>
      </body>
    </html>"""

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Add body to email
    message.attach(MIMEText(body, "html"))

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Try to log in to server and send email
    try:
        server = smtplib.SMTP_SSL(smtp_server, port,context)
        # server.starttls(context=context)  # Secure the connection
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()


########################## for got ###################################################
def send_reset_code_on_email(receiver,good_name,reset_token):

    port = 465 # For starttls
    smtp_server = "smtp.hostinger.com,"
    sender_email = "support@sarihorganics.com"
    receiver_email = receiver
    subject = "Password Reset Link (OBAM AI)"
    password = "Support@4791"

    body="""<!DOCTYPE html>
    <html>
      <head>
        <style>
          * {
            font-family: "Montserrat", sans-serif;
            color:#000000;
          }
          ul li
            {
                margin-bottom:5px;
            }
          body {
            font-family: Arial, sans-serif;
            background-color: #b3daff;
            color: #000000;
            font-family: "Montserrat", sans-serif;
            padding:20px;
          }
          .container {
            max-width: 100%;
            color: white;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid white;
            background-color: #b3daff;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
          }

          .footer-like {
            margin-top: auto;
            padding: 6px;
            text-align: center;
          }
          .footer-like p {
            margin: 0;
            padding: 4px;
            color: #fafafa;
            font-family: "Raleway", sans-serif;
            letter-spacing: 1px;
          }
          .footer-like p a {
            text-decoration: none;
            font-weight: 600;
          }

          .logo {
            width: 100px;
            border:1px solid white;
          }
          .verify-button
          {
          text-decoration:none;
          background-color:#009933;
          border-radius:5px;
          padding:10px;
          border: none;
          text-decoration:none;
          }
        </style>
      </head>
      <body>
        <div class="container">
    <img src="https://i.ibb.co/2k2YhLC/image-2-r.png" alt="OBAM-Logo" border="0" class="logo" />
    """
    body += f'<p>Dear {good_name},</p>' \
    f'<h1><strong>Password Reset Link OBAM AI!</strong></h1>' \
    f'<p>Your password reset Link  is placed below:</p>' \
    f'<h4><b><a href="{BASE_URL}reset-password?token={reset_token}" class="verify-button" style="color:#b3daff;">Click here to Reset your password</a></b></h4>'
    body+="""
          <p><b>Sincerely,</b><br />The OBAM AI Team</p>
          <div class="footer-like">
            <p>
              Powered by OBAM AI
            </p>
          </div>
        </div>
      </body>
    </html>"""

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Add body to email
    message.attach(MIMEText(body, "html"))

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Try to log in to server and send email
    try:
        # context = ssl.create_default_context()

        server = smtplib.SMTP_SSL(smtp_server, port,context)
        # server.starttls(context=context)  # Secure the connection
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()
#############################################################################




def generate_verification_token():
    return secrets.token_urlsafe(16)

############################################################################
def generate_verification_code():
    # Generate a random 6-digit hexadecimal code
    verification_code = secrets.token_hex(3).upper()
    return verification_code

def generate_unique_id_for_user(db: Session):
    unique_id = str(shortuuid.uuid())
    while db.query(Users).filter(Users.user_id == unique_id).first():
        unique_id = str(shortuuid.uuid())
    return unique_id

def get_unique_id():
    return str(shortuuid.uuid())


class Hasher():
    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return pwd_context.hash(password)
    
