from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from core.database import SessionLocal, get_db
from utils.auth_utils import AuthManager

from .dependencies import get_auth_manager

from .models import Users
from .schemas import (Login, PasswordResetConfirm, PasswordResetRequest,
                      TotalAndAllUsersResponse, User)

router = APIRouter(tags=["AUTHENTICATIONS"])

################# REGISTER #################################


@router.post("/register")
async def register(request: User, db: Session = Depends(get_db), auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    Register a new user account.

    Args:
    request (User): User registration data including name, email, and password.
    db (Session, optional): Database session dependency.

    Returns:
    dict: A dictionary containing the status of the registration process and
          user data if successful, or an error message if registration failed.

    Raises:
    HTTPException: If the email is already registered.

    This function creates a new user account by hashing the provided password,
    generating a unique user ID and a verification token, and storing the user
    data in the database. It also sends a verification email to the user.
    """

    try:
        existing_user = db.query(Users).filter(
            Users.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Email already registered. Please use another email address or login with the existing email address.")

        hashed_password = auth_manager.get_password_hash(request.password)
        db_entry = Users(
            user_id=auth_manager.generate_unique_user_id(db),
            name=request.name,
            email=request.email,
            password=hashed_password,
            verification_token=auth_manager.generate_verification_token()
        )

        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
        print(db_entry.verification_token)
        auth_manager.send_verification_email(
            db_entry.email, db_entry.name, db_entry.verification_token)

        return {
            "status": "ok",
            "message": "User registered successfully. Check your email for verification instructions.",
            "data": db_entry
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e), "data": None}
    finally:
        db.close()

################# LOGIN #################################


@router.post("/login/")
async def login(credentials: Login, auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    Verify user credentials and return user data if authenticated.

    Args:
    credentials (Login): User credentials.

    Returns:
    dict: A dictionary containing the user data if authenticated, else an error message.
    """
    try:
        db = SessionLocal()
        user = db.query(Users).filter(Users.email == credentials.email).first()
        if user:
            
            if not auth_manager.verify_password(credentials.password, user.password):
                raise HTTPException(
                    status_code=401, detail="Invalid Credentials.")
            user_dict = {"user_id": user.user_id,
                            "name": user.name, 
                            "email": user.email,
                            "verification_token":user.verification_token
                            }
            return {"status": "ok", "message": "Account has been Authenticated.", "data": user_dict}
            # else:
            #     # send_verifiaction_code_on_email(
            #     #     user.email, user.name, user.verification_token)
            #     return {"status": "ok", "message": "Your account is not Verified Please Check Your Email Address for Verification Link.", "data": None}
        else:
            return {"status": "error",
                    "message": "User not Found.",
                    "data": None}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
    finally:
        db.close()

# ################# VERIFICATION #################################


@router.get("/verify/")
def verify_account(token: str):
    """
    Verify user account using the verification token sent to their email.

    Args:
    token (str): The verification token sent to the user's email.

    Returns:
    dict: A dictionary containing the status of the verification, a message, and user data if verified.
    """
    
    try:
        db = SessionLocal()
        user = db.query(Users).filter(
            Users.verification_token == token).first()
        if user:
            if user.isVerified:
                db.close()
                # Redirect to the given page with a message
                return RedirectResponse(url="https://web-app-llm-observability-bre1.vercel.app/login")
                # return {"status": "ok", "message": "Account is already Verified.", "data": None}
            else:
                user.isVerified = True
                db.commit()
                # Redirect to the given page with a message
                return RedirectResponse(url="https://web-app-llm-observability-bre1.vercel.app/login")
                # return {"status": "ok", "message": "Account Verified successfully.", "data": None}
        else:
            return {"status": "error",
                    "message": "User not Found.",
                    "data": None}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
    finally:
        db.close()

################# RESEND VERIFICATION TOKEN #################################


@router.get("/resendVerificationToken/")
def resendVerificationToken(email: str, auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    Resend the account verification token to the user's email address.

    Args:
    email (str): The email address of the user requesting the verification token resend.

    Returns:
    dict: A dictionary containing the status of the request, a message, and additional data if relevant.

    Raises:
    HTTPException: If an error occurs during the process.

    This function checks if the user associated with the provided email is already verified.
    If not verified, it resends the verification token to the user's email. If the email does
    not correspond to any registered account, it returns an error message.
    """

    try:
        db = SessionLocal()
        user = db.query(Users).filter(Users.email == email).first()
        if user:
            if user.isVerified:
                return {"status": "ok", "message": "Account is already Verified.", "data": None}
            else:
                auth_manager.send_verification_email(
                    user.email, user.name, user.verification_token)
                return {"status": "ok", "message": "Verification Link has been Resent to your Email Address.", "data": None}
        else:
            return {"status": "error",
                    "message": "Provided Email Address does not points to any Registered account.",
                    "data": None}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
    finally:
        db.close()


################# FORGOT PASSWORD REQUEST #################################

@router.post("/forgot-password/")
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db), auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    Handle forgot password requests by generating a reset code and sending it to the user's email.

    Args:
    request (PasswordResetRequest): The request object containing the user's email.
    db (Session, optional): Database session dependency.

    Returns:
    dict: A dictionary with the status and message indicating the password reset instructions have been sent.

    Raises:
    HTTPException: If the user's email is not found in the database.

    This function checks if a user with the given email exists in the database. If the user is found,
    a verification code is generated and stored as the user's verification token. The reset code is then
    sent to the user's email address, allowing them to reset their password.
    """
    try:

        user = db.query(Users).filter(Users.email == request.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        reset_code = auth_manager.generate_verification_code()
        user.verification_token = reset_code
        db.commit()

        # reset_url = f"{BASE_URL}/reset-password/?token={reset_token}"  # Update with your domain
        auth_manager.send_reset_password_email(user.email, user.name, reset_code)

        return {"status": "ok", "message": "Password reset instructions have been sent to your email"}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": None}
    finally:
        db.close()


################# RESET PASSWORD CONFIRM #################################

@router.post("/reset-password/")
async def reset_password(token: str, new_password: PasswordResetConfirm, db: Session = Depends(get_db), auth_manager: AuthManager = Depends(get_auth_manager)):
    """
    Handle password reset requests by verifying the reset token and updating the user's password.

    Args:
    token (str): The reset token sent to the user's email.
    new_password (PasswordResetConfirm): The new password to set for the user.
    db (Session, optional): Database session dependency.

    Returns:
    dict: A dictionary with the status and message indicating the password reset was successful.

    Raises:
    HTTPException: If the reset token is invalid or expired.

    This function verifies the reset token by checking if a user with the given token exists in the database.
    If the user is found, it updates the user's password with the new password provided and invalidates the
    reset token. If the token is invalid or expired, it raises an HTTPException with a 400 status code.
    """
    
    user = db.query(Users).filter(Users.verification_token == token).first()
    if not user:
        raise HTTPException(
            status_code=400, detail="Invalid or expired reset token")

    user.password = auth_manager.get_password_hash(new_password.new_password)
    # user.verification_token = None  # Invalidate the token after use
    db.commit()

    return {"status": "ok", "message": "Password has been reset successfully"}



@router.get("/total-and-all-users/", response_model=TotalAndAllUsersResponse)
async def get_total_and_all_users(db: Session = Depends(get_db)):
    """
    Get total number of users and all users from the database.

    Returns:
    TotalAndAllUsersResponse: A response object containing the total number of users and a list of all users.
    """
    all_users = db.query(Users).all()
    total_users = db.query(func.count(Users.user_id)).scalar()
    return {"total_users": total_users, "all_users": all_users}


@router.put("/users/{user_id}/update-name")
def update_user_name(user_id: str, new_name: str, db: Session = Depends(get_db)):
    """
    Update the name of a user in the database.

    Args:
    user_id (str): The user ID of the user to update.
    new_name (str): The new name of the user.

    Returns:
    dict: A dictionary with a message indicating whether the update was successful.

    Raises:
    HTTPException: If the user is not found, or if there is an unexpected error.
    """
    try:
        user = db.query(Users).filter(Users.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.name = new_name
        db.commit()
        return {"message": "User name updated successfully"}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred")
    finally:
        db.close()


