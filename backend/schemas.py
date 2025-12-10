from pydantic import BaseModel, EmailStr
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class CreatePlan(BaseModel):
    user_id: int
    plan: str  # "30" ou "15"
    
    

class TrialRequest(BaseModel):
    user_id: int
    
    

class RenewPlan(BaseModel):
    account_id: int
    days: int  # 15 ou 30

class CancelPlan(BaseModel):
    account_id: int


