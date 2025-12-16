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
<<<<<<< HEAD
from email_sender import send_ehi_email
from datetime import datetime, timedelta
import random
import string

# Criar tabelas no banco
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(payment_router)
=======
from email_sender import send_email

from payment_routes import router as payment_router
>>>>>>> 3e4097c57893cccff009cf91df1a0e3c187d1013

# ------------------------------------------------------
# CONFIG JWT
# ------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "TEST-2636876912816804-120619-ecc30317c9b6194ef03217949a8bde44-149920841")
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
<<<<<<< HEAD
@app.post("/create-plan")
def create_plan(data: CreatePlan, db: Session = Depends(db)):

    plan_days = 30 if data.plan == "30" else 15

    # Gera username único
    username = f"user{data.user_id}{random.randint(100,999)}"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    # Cria usuário SSH no SSHPLUS
    ssh_result = create_ssh_user(username, password, plan_days)

    expires = datetime.now() + timedelta(days=plan_days)

    # Gera o arquivo EHI
    ehi_file = generate_ehi(username, password, data.plan)

    # Salva no banco
    new_acc = VPNAccount(
        owner_id=data.user_id,
        username=username,
        password=password,
        plan=data.plan,
        expires_at=expires.isoformat(),
        ehi_file=ehi_file,
        notified_expire=0
    )

    db.add(new_acc)
    db.commit()

    # Envia ehi para o email do cliente
    user = db.query(User).filter(User.id == data.user_id).first()
    if user:
        send_email(
            user.email,
            "Sua VPN está pronta!",
            f"""
Seu acesso VPN foi criado!

Usuário SSH: {username}
Senha SSH: {password}
Validade: {expires}

Anexo segue seu arquivo .EHI para uso.
            """,
            attachment=ehi_file,
            filename=f"{username}.ehi"
        )

    return {
        "message": "Plano criado com sucesso!",
        "username": username,
        "password": password,
        "expires": expires,
        "ehi": ehi_file,
        "ssh_result": ssh_result
=======
def create_token(user_id: int):
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
>>>>>>> 3e4097c57893cccff009cf91df1a0e3c187d1013
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

<<<<<<< HEAD
    new_expires = datetime.now() + timedelta(days=data.days)
    new_ehi = generate_ehi(acc.username, acc.password, acc.plan)
    acc.expires_at = new_expires.isoformat()
    acc.ehi_file = new_ehi
=======
    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password),
        trial_used=False
    )
>>>>>>> 3e4097c57893cccff009cf91df1a0e3c187d1013

    db.add(new_user)
    db.commit()

    return {"message": "Conta criada com sucesso"}

# ------------------------------------------------------
# LOGIN
# ------------------------------------------------------
@app.post("/api/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

<<<<<<< HEAD
    accounts = db.query(VPNAccount).all()

    notified_count = 0

    for acc in accounts:
        expires = datetime.fromisoformat(acc.expires_at)

        if today < expires <= limit and acc.notified_expire == 0:

            user = db.query(User).filter(User.id == acc.owner_id).first()
            if user:
                send_email(
                    user.email,
                    "⚠️ Sua VPN expira em 2 dias",
                    f"Sua VPN expira em: {acc.expires_at}"
                )

            acc.notified_expire = 1
            db.commit()
            notified_count += 1

    return {
        "message": "Checagem concluída",
        "emails_enviados": notified_count
    }


# ------------------------------------------------------
# RETORNAR PLANOS DO USUÁRIO
# ------------------------------------------------------
@app.get("/get-plans/{user_id}")
def get_plans(user_id: int, db: Session = Depends(db)):
    accounts = db.query(VPNAccount).filter(VPNAccount.owner_id == user_id).all()

    return [
        {
            "id": acc.id,
            "username": acc.username,
            "password": acc.password,
            "plan": acc.plan,
            "expires": acc.expires_at,
            "ehi_file": acc.ehi_file
        }
        for acc in accounts
    ]

=======
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(401, "Credenciais inválidas")

    token = create_token
>>>>>>> 3e4097c57893cccff009cf91df1a0e3c187d1013
