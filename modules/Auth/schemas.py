from pydantic import BaseModel
from typing import List,Dict



#################################### AUTHENTICATIONS SCHEMAS ####################################
class User(BaseModel):
    name:str
    email:str
    password:str
    
class Login(BaseModel):
    email:str
    password:str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    new_password: str

class UserResponse(BaseModel):
    name: str
    email: str
    isVerified: bool

    class Config:
        from_attributes = True

class TotalAndAllUsersResponse(BaseModel):
    total_users: int
    all_users: List[UserResponse]


class TokensCalc(BaseModel):
    url:str

class AccessToken(BaseModel):
    access_token:str
    
