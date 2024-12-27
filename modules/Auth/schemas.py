from pydantic import BaseModel
from typing import List,Dict,Optional,Tuple
    
# correct and alling with previous
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


#####################Plans#####################
class SubscribePlan(BaseModel):
    plan_id:str
    user_id:str
    transaction_id:str
    paymentMethodId:str
    payment_amount:int


class PaymentIntentResult(BaseModel):
    clientSecret: str

class PaymentIntent(BaseModel):
    amount:int


class CheckPlanExistance(BaseModel):
    plan_id: str
    user_id: str

class RenewPlan(BaseModel):
    Selected_Plan_ID:str
    transaction_id:str 
    paymentMethodId:str
    payment_amount:int

class PlansPydnaticModel(BaseModel):
    plan_Name:str
    total_chatbots_allowed:int
    total_knowldegStores_Allowed_Tokens:int
    Total_Responce_Tokens_allowed:int
    price:int

#####################################################################
class ChatRequest(BaseModel):
    chatbotId: str
    question: str
    visitorID:str
    chat_history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    answer: str
    # reference_context: List[dict]

class EditChatBots(BaseModel):
    descriptive_name:str
    temperature:str
    llm:str
    base_prompt:Optional[str]=""


class ChatBots(BaseModel):
    user_id :str
    descriptive_name:str
    temperature:str
    llm:str
    urls: str
    base_prompt:Optional[str]=""
    sync_status:bool
    sync_interval:int   #in hours

class EditAppeanceChatBots(BaseModel):
    ThemeColor:str
    InitialMessage:str
    DisplayName:str


class AddLeadsPydanticModel(BaseModel):
    chatbot_id:str
    name: Optional[str]=""
    email: Optional[str]=""
    phone: Optional[str]=""


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


# class SyncConfigSchema(BaseModel):
#     chatbot_id: str
#     sync_duration: int
#     is_sync: bool

#     class Config:
#         orm_mode = True


class SyncConfigUpdateSchema(BaseModel):
    sync_interval: int
    sync_status: bool

    class Config:
        orm_mode = True