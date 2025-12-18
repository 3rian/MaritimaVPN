import os
import mercadopago
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Payment, User, VPNAccount
from .schemas import CreatePlan
from .ssh_connector import create_ssh_user
from .ehi_generator import generate_ehi
from .email_sender import send_email
from .auth import get_current_user


# ------------------------------------------------------
# CONFIG
# ------------------------------------------------------
router = APIRouter(prefix="/api")
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

PLAN_PRICES = {
    7: 5.00,
    15: 7.00,
    30: 12.00
}


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
# CRIAR PIX (NÃO CRIA PLANO)
# ------------------------------------------------------
@router.post("/create-pix")
def create_pix(
    data: CreatePlan,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan_days = int(data.plan_days)
    price = PLAN_PRICES.get(plan_days)

    if not price:
        raise HTTPException(400, "Plano inválido")

    payment_data = {
        "transaction_amount": float(price),
        "description": f"Plano Marítima VPN - {plan_days} dias",
        "payment_method_id": "pix",
        "payer": {"email": user.email},
        "notification_url": "https://maritimavpn.shop/api/webhook/mercadopago"
    }

    payment = sdk.payment().create(payment_data)
    response = payment.get("response")

    if not response or "id" not in response:
        raise HTTPException(500, "Erro ao criar pagamento")

    new_payment = Payment(
        user_id=user.id,
        plan_days=plan_days,
        mp_payment_id=str(response["id"]),
        status=response["status"],
        created_at=datetime.utcnow().isoformat()
    )

    db.add(new_payment)
    db.commit()

    return {
        "payment_id": response["id"],
        "status": response["status"],
        "qr_code": response["point_of_interaction"]["transaction_data"]["qr_code"],
        "qr_code_base64": response["point_of_interaction"]["transaction_data"]["qr_code_base64"],
        "copy_paste": response["point_of_interaction"]["transaction_data"]["qr_code"]
    }


# ------------------------------------------------------
# WEBHOOK MERCADO PAGO (CRIA PLANO AQUI)
# ------------------------------------------------------
@router.post("/webhook/mercadopago")
async def mercadopago_webhook(request: Request, db: Session = Depends(get_db)):

    body = await request.json()

    if body.get("type") != "payment":
        return {"status": "ignored"}

    payment_id = body.get("data", {}).get("id")
    if not payment_id:
        return {"status": "invalid"}

    mp_payment = sdk.payment().get(payment_id)
    response = mp_payment.get("response")

    if not response or response["status"] != "approved":
        return {"status": "not_approved"}

    payment_db = db.query(Payment).filter(
        Payment.mp_payment_id == str(payment_id)
    ).first()

    if not payment_db or payment_db.status == "approved":
        return {"status": "already_processed"}

    # Marca pagamento como aprovado
    payment_db.status = "approved"
    db.commit()

    user = db.query(User).filter(User.id == payment_db.user_id).first()
    if not user:
        return {"status": "user_not_found"}

    # CRIA PLANO
    plan_days = payment_db.plan_days
    expires = datetime.utcnow() + timedelta(days=plan_days)

    username = f"user{user.id}{payment_id[-4:]}"
    password = os.urandom(4).hex()

    create_ssh_user(username, password, plan_days)
    ehi_path = generate_ehi(username, password, str(plan_days))

    vpn = VPNAccount(
        owner_id=user.id,
        username=username,
        password=password,
        plan=str(plan_days),
        expires_at=expires.isoformat(),
        ehi_file=ehi_path,
        notified_expire=0
    )

    db.add(vpn)
    db.commit()

    # ENVIA EMAIL COM EHI
    send_email(
        to=user.email,
        subject="Seu acesso Marítima VPN",
        body=f"""
Seu plano foi ativado com sucesso!

Usuário: {username}
Senha: {password}
Validade: {expires.strftime('%d/%m/%Y')}

O arquivo EHI está anexado.
""",
        attachment_path=ehi_path
    )

    return {"status": "plan_created"}


# ------------------------------------------------------
# TESTE GRÁTIS (LOGADO)
# ------------------------------------------------------
@router.post("/trial")
def create_trial(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.trial_used:
        raise HTTPException(400, "Teste grátis já utilizado")

    plan_days = 3
    expires = datetime.utcnow() + timedelta(days=plan_days)

    username = f"trial{user.id}{int(datetime.utcnow().timestamp())%1000}"
    password = os.urandom(4).hex()

    create_ssh_user(username, password, plan_days)
    ehi_path = generate_ehi(username, password, str(plan_days))

    vpn = VPNAccount(
        owner_id=user.id,
        username=username,
        password=password,
        plan="trial",
        expires_at=expires.isoformat(),
        ehi_file=ehi_path,
        notified_expire=0
    )

    user.trial_used = True

    db.add(vpn)
    db.commit()

    send_email(
        to=user.email,
        subject="Teste grátis Marítima VPN",
        body=f"""
Seu teste grátis foi ativado!

Usuário: {username}
Senha: {password}
Validade: {expires.strftime('%d/%m/%Y')}
""",
        attachment_path=ehi_path
    )

    return {"message": "Teste grátis criado"}


# ------------------------------------------------------
# MEUS PLANOS
# ------------------------------------------------------
@router.get("/get-plans")
def get_plans(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plans = db.query(VPNAccount).filter(
        VPNAccount.owner_id == user.id
    ).all()

    return [
        {
            "id": p.id,
            "plan": p.plan,
            "username": p.username,
            "expires": p.expires_at
        }
        for p in plans
    ]
