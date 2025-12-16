from fastapi import FastAPI, Depends, HTTPException, Response, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
import random, string, base64

from database import Base, engine, SessionLocal
from models import User, VPNAccount
from schemas import UserCreate, UserLogin, CreatePlan, RenewPlan
from auth import hash_password, verify_password
from ssh_connector import create_ssh_user, delete_ssh_user
from ehi_generator import generate_ehi
from email_sender import send_email

# ------------------------------------------------------
# CONFIG JWT
# ------------------------------------------------------
SECRET_KEY = "MUDE-ISSO-PARA-ALGO-GIGANTE-E-SECRETO"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# ------------------------------------------------------
# APP
# ------------------------------------------------------
Base.metadata.create_all(bind=engine)
app = FastAPI()

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
        raise HTTPException(401, "Usuário não existe")

    return user

# ------------------------------------------------------
# REGISTER
# ------------------------------------------------------
@app.post("/register")
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
@app.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(401, "Credenciais inválidas")

    token = create_token(user.id)

    return {
        "token": token,
        "name": user.name
    }

# ------------------------------------------------------
# CREATE PLAN
# ------------------------------------------------------
@app.post("/create-plan")
def create_plan(data: CreatePlan, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    days = int(data.plan_days)
    if days not in [7, 15, 30]:
        raise HTTPException(400, "Plano inválido")

    username = f"user{user.id}{random.randint(100,999)}"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    create_ssh_user(username, password, days)

    expires = datetime.now() + timedelta(days=days)
    ehi = generate_ehi(username, password, str(days))

    acc = VPNAccount(
        owner_id=user.id,
        username=username,
        password=password,
        plan=str(days),
        expires_at=expires.isoformat(),
        ehi_file=ehi,
        notified_expire=0
    )

    db.add(acc)
    db.commit()

    send_email(
        user.email,
        "VPN Criada",
        f"Usuário: {username}\nValidade: {expires.strftime('%d/%m/%Y')}"
    )

    return {"message": "Plano criado com sucesso"}

# ------------------------------------------------------
# GET PLANS
# ------------------------------------------------------
@app.get("/get-plans")
def get_plans(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id": acc.id,
            "username": acc.username,
            "plan": acc.plan,
            "expires": acc.expires_at
        }
        for acc in db.query(VPNAccount).filter(VPNAccount.owner_id == user.id)
    ]

# ------------------------------------------------------
# DOWNLOAD EHI
# ------------------------------------------------------
@app.get("/download-ehi/{account_id}")
def download_ehi(account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    acc = db.query(VPNAccount).filter(
        VPNAccount.id == account_id,
        VPNAccount.owner_id == user.id
    ).first()

    if not acc:
        raise HTTPException(404, "Plano não encontrado")

    return Response(
        content=base64.b64decode(acc.ehi_file),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{acc.username}.ehi"'}
    )
