from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func


from core.database import SessionLocal, get_db
from utils.auth_utils import (Hasher, generate_unique_id_for_user,
                              generate_verification_code,
                              generate_verification_token,
                              send_reset_code_on_email,
                              send_verifiaction_code_on_email)

from .models import Users
from .schemas import (Login, PasswordResetConfirm, PasswordResetRequest,
                      TotalAndAllUsersResponse, User)

router = APIRouter(tags=["AUTHENTICATIONS"])

################# REGISTER #################################


@router.post("/register/")
def register(request: User, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(Users).filter(
            Users.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400, detail="Email already registered. Please use another email address or login with the existing email address.")

        hashed_password = Hasher.get_password_hash(request.password)
        db_entry = Users(
            user_id=generate_unique_id_for_user(db),
            name=request.name,
            email=request.email,
            password=hashed_password,
            verification_token=generate_verification_token()
        )

        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)

        # send_verifiaction_code_on_email(
        #     db_entry.email, db_entry.name, db_entry.verification_token)

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
def login(credentials: Login):
    try:
        db = SessionLocal()
        user = db.query(Users).filter(Users.email == credentials.email).first()
        if user:
            
            if not user or not Hasher.verify_password(credentials.password, user.password):
                raise HTTPException(
                    status_code=401, detail="Invalid Credentials.")
            user_dict = {"user_id": user.user_id,
                            "name": user.name, "email": user.email}
            db.close()
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
        db.close()
        return {"status": "error", "message": str(e), "data": None}

# ################# VERIFICATION #################################


@router.get("/verify/")
def verify_account(token: str):
    try:
        db = SessionLocal()
        user = db.query(Users).filter(
            Users.verification_token == token).first()
        if user:
            if user.isVerified:
                db.close()
                # Redirect to the given page with a message
                return RedirectResponse(url="")
                # return {"status": "ok", "message": "Account is already Verified.", "data": None}
            else:
                user.isVerified = True
                db.commit()
                db.close()
                # Redirect to the given page with a message
                return RedirectResponse(url="https://build-for-ai-dkvc.vercel.app/aen+verified+login+to+access+Dashboard.")
                # return {"status": "ok", "message": "Account Verified successfully.", "data": None}
        else:
            return {"status": "error",
                    "message": "User not Found.",
                    "data": None}
    except Exception as e:
        db.close()
        return {"status": "error", "message": str(e), "data": None}

################# RESEND VERIFICATION TOKEN #################################


@router.get("/resendVerificationToken/")
def resendVerificationToken(email: str):
    try:
        db = SessionLocal()
        user = db.query(Users).filter(Users.email == email).first()
        if user:
            if user.isVerified:
                db.close()
                return {"status": "ok", "message": "Account is already Verified.", "data": None}
            else:
                send_verifiaction_code_on_email(
                    user.email, user.name, user.verification_token)
                return {"status": "ok", "message": "Verification Link has been Resent to your Email Address.", "data": None}
        else:
            return {"status": "error",
                    "message": "Provided Email Address does not points to any Registered account.",
                    "data": None}
    except Exception as e:
        db.close()
        return {"status": "error", "message": str(e), "data": None}


################# FORGOT PASSWORD REQUEST #################################

@router.post("/forgot-password/")
def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_code = generate_verification_code()
    user.verification_token = reset_code
    db.commit()

    # reset_url = f"{BASE_URL}/reset-password/?token={reset_token}"  # Update with your domain
    send_reset_code_on_email(user.email, user.name, reset_code)

    return {"status": "ok", "message": "Password reset instructions have been sent to your email"}


################# RESET PASSWORD CONFIRM #################################

@router.post("/reset-password/")
def reset_password(token: str, new_password: PasswordResetConfirm, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.verification_token == token).first()
    if not user:
        raise HTTPException(
            status_code=400, detail="Invalid or expired reset token")

    user.password = Hasher.get_password_hash(new_password.new_password)
    # user.verification_token = None  # Invalidate the token after use
    db.commit()

    return {"status": "ok", "message": "Password has been reset successfully"}


@router.get("/total-and-all-users/")
async def get_total_and_all_users(db: Session = Depends(get_db)):
    all_users = db.query(Users).all()
    total_users = db.query(func.count(Users.user_id)).scalar()
    return {"total_users": total_users, "all_users": all_users}


@router.get("/total-and-all-users/", response_model=TotalAndAllUsersResponse)
async def get_total_and_all_users(db: Session = Depends(get_db)):
    all_users = db.query(Users).all()
    total_users = db.query(func.count(Users.user_id)).scalar()
    return {"total_users": total_users, "all_users": all_users}


@router.put("/users/{user_id}/update-name")
def update_user_name(user_id: str, new_name: str, db: Session = Depends(get_db)):
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


