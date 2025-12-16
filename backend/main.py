from fastapi import FastAPI, Depends, HTTPException, Response, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
import random, string, base64, os

from database import Base, engine, SessionLocal
from models import User, VPNAccount
from schemas import UserCreate, UserLogin, CreatePlan
from auth import hash_password, verify_password
from ssh_connector import create_ssh_user, delete_ssh_user
from ehi_generator import generate_ehi
from email_sender import send_email

from payment_routes import router as payment_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles



app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/imagens", StaticFiles(directory="imagens"), name="imagens")

# ------------------------------------------------------
# CONFIG JWT
# ------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "MUDE-ISSO-PARA-UM-SEGREDO-GIGANTE")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# ------------------------------------------------------
# APP
# ------------------------------------------------------
Base.metadata.create_all(bind=engine)
app = FastAPI()

# 👉 inclui PIX / webhook aqui
app.include_router(payment_router)

# ------------------------------------------------------
# DB
# ------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------
# JWT UTILS
# ------------------------------------------------------
def create_token(user_id: int):
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token inválido")

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except JWTError:
        raise HTTPException(401, "Token expirado ou inválido")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(401, "Usuário não encontrado")

    return user

# ------------------------------------------------------
# REGISTER
# ------------------------------------------------------
@app.post("/api/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(400, "E-mail já cadastrado")

    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password),
        trial_used=False
    )

    db.add(new_user)
    db.commit()

    return {"message": "Conta criada com sucesso"}

# ------------------------------------------------------
# LOGIN
# ------------------------------------------------------
@app.post("/api/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(401, "Credenciais inválidas")

    token = create_token
