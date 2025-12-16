from pydantic import BaseModel, EmailStr
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str

class CreatePlan(BaseModel):
    plan_days: int  # "30" , "15 ou 7"
    
    

class TrialRequest(BaseModel):
    user_id: int
    
    

class RenewPlan(BaseModel):
    account_id: int
    days: int  # 7, 15 ou 30

#class CancelPlan(BaseModel):
 #   account_id: int


