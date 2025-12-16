from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import User, VPNAccount, Trial
from payment_routes import router as payment_router

from schemas import (
    UserCreate,
    UserLogin,
    CreatePlan,
    TrialRequest,
    RenewPlan
)
from auth import hash_password, verify_password
from ssh_connector import create_ssh_user, delete_ssh_user
from ehi_generator import generate_ehi
from email_sender import send_ehi_email
from datetime import datetime, timedelta
import random
import string

# Criar tabelas no banco
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(payment_router)

# ------------------------------------------------------
# Função para obter sessão do banco
# ------------------------------------------------------
def db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


# ------------------------------------------------------
# CADASTRO
# ------------------------------------------------------
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(db)):
    hashed = hash_password(user.password)

    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed,
        trial_used=False
    )

    db.add(new_user)
    db.commit()

    return {"message": "Usuário criado com sucesso"}


# ------------------------------------------------------
# LOGIN
# ------------------------------------------------------
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or not verify_password(user.password, db_user.password):
        return {"error": "Credenciais inválidas"}

    return {
        "message": "Login autorizado",
        "user_id": db_user.id
    }


# ------------------------------------------------------
# CRIAR PLANO (15 OU 30 DIAS)
# ------------------------------------------------------
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
    }


# ------------------------------------------------------
# CRIAR TRIAL – 3H
# ------------------------------------------------------
@app.post("/trial")
def create_trial(data: TrialRequest, db: Session = Depends(db)):

    user = db.query(User).filter(User.id == data.user_id).first()

    if not user:
        return {"error": "Usuário não encontrado"}

    if user.trial_used:
        return {"error": "O usuário já utilizou o teste grátis"}

    username = f"trial{user.id}"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    ssh_result = create_ssh_user(username, password, 0.125)  # 3 horas

    now = datetime.now()
    expires = now + timedelta(hours=3)

    new_trial = Trial(
        user_id=user.id,
        ssh_user=username,
        ssh_pass=password,
        created_at=now.isoformat(),
        expires_at=expires.isoformat(),
        active=True
    )

    db.add(new_trial)
    user.trial_used = True
    db.commit()

    send_email(
        user.email,
        "Seu Teste Grátis Está Ativo!",
        f"""
Usuário SSH: {username}
Senha SSH: {password}
Expira em: {expires}
        """
    )

    return {
        "message": "Teste de 3 horas criado com sucesso!",
        "username": username,
        "password": password,
        "expires": expires,
        "ssh_result": ssh_result
    }


# ------------------------------------------------------
# CANCELAR PLANO
# ------------------------------------------------------
@app.post("/cancel-plan")
def cancel_plan(account_id: int, db: Session = Depends(db)):

    acc = db.query(VPNAccount).filter(VPNAccount.id == account_id).first()

    if not acc:
        return {"error": "Conta não encontrada"}

    delete_ssh_user(acc.username)

    db.delete(acc)
    db.commit()

    return {"message": "Plano cancelado com sucesso"}


# ------------------------------------------------------
# RENOVAR PLANO – N DIAS
# ------------------------------------------------------
@app.post("/renew-plan")
def renew_plan(data: RenewPlan, db: Session = Depends(db)):

    acc = db.query(VPNAccount).filter(VPNAccount.id == data.account_id).first()

    if not acc:
        return {"error": "Plano não encontrado"}

    new_expires = datetime.now() + timedelta(days=data.days)
    new_ehi = generate_ehi(acc.username, acc.password, acc.plan)
    acc.expires_at = new_expires.isoformat()
    acc.ehi_file = new_ehi

    db.commit()

    return {
        "message": "Plano renovado com sucesso!",
        "expires": new_expires,
        "ehi": new_ehi
    }


# ------------------------------------------------------
# VERIFICAR PLANOS QUE EXPIRAM EM 2 DIAS
# ------------------------------------------------------
@app.get("/check-expirations")
def check_expirations(db: Session = Depends(db)):

    today = datetime.now()
    limit = today + timedelta(days=2)

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

