import os
import mercadopago
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Payment, User, VPNAccount
from schemas import CreatePlan
from ssh_connector import create_ssh_user
from ehi_generator import generate_ehi

# ------------------------------------------------------
# CONFIGURAÇÃO
# ------------------------------------------------------
router = APIRouter(prefix="/api")

sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

PLAN_PRICES = {
    7: 5.00,
    15: 7.00,
    30: 12.00
}

# ------------------------------------------------------
# DEPENDÊNCIA DB
# ------------------------------------------------------
def db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()

# ------------------------------------------------------
# CRIAR PIX
# ------------------------------------------------------
@router.post("/create-pix")
def create_pix(data: CreatePlan, db: Session = Depends(db)):

    plan_days = int(data.plan_days)
    price = PLAN_PRICES.get(plan_days)
    if not price:
        raise HTTPException(400, "Plano inválido")

    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    payment_data = {
        "transaction_amount": float(price),
        "description": f"Plano Marítima VPN - {plan_days} dias",
        "payment_method_id": "pix",
        "payer": {
            "email": user.email
        },
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
        "qr_code_base64": response["point_of_interaction"]["transaction_data"]["qr_code_base64"]
    }

# ------------------------------------------------------
# WEBHOOK MERCADO PAGO
# ------------------------------------------------------
@router.post("/webhook/mercadopago")
async def mercadopago_webhook(request: Request, db: Session = Depends(db)):

    body = await request.json()

    if body.get("type") != "payment":
        return {"status": "ignored"}

    payment_id = body.get("data", {}).get("id")
    if not payment_id:
        return {"status": "invalid"}

    mp_payment = sdk.payment().get(payment_id)
    response = mp_payment.get("response")

    if not response:
        return {"status": "mp_error"}

    if response["status"] != "approved":
        return {"status": "not_approved"}

    payment_db = db.query(Payment).filter(
        Payment.mp_payment_id == str(payment_id)
    ).first()

    if not payment_db or payment_db.status == "approved":
        return {"status": "already_processed"}

    # ATUALIZA PAGAMENTO
    payment_db.status = "approved"
    db.commit()

    # CRIA PLANO AUTOMATICAMENTE
    plan_days = payment_db.plan_days
    expires = datetime.utcnow() + timedelta(days=plan_days)

    username = f"user{payment_db.user_id}{payment_id[-4:]}"
    password = os.urandom(4).hex()

    create_ssh_user(username, password, plan_days)
    ehi = generate_ehi(username, password, str(plan_days))

    new_acc = VPNAccount(
        owner_id=payment_db.user_id,
        username=username,
        password=password,
        plan=str(plan_days),
        expires_at=expires.isoformat(),
        ehi_file=ehi,
        notified_expire=0
    )

    db.add(new_acc)
    db.commit()

    return {"status": "plan_created"}

# ------------------------------------------------------
# NOVA ROTA: CRIAR PLANO DIRETO (para botão "Comprar Plano")
# ------------------------------------------------------
@router.post("/create-plan")
def create_plan(data: CreatePlan, db: Session = Depends(db)):
    plan_days = int(data.plan_days)
    if plan_days not in PLAN_PRICES:
        raise HTTPException(400, "Plano inválido")

    # Para simplificar, pegamos o primeiro usuário (ou você pode passar user_id no frontend)
    user = db.query(User).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    expires = datetime.utcnow() + timedelta(days=plan_days)
    username = f"user{user.id}{int(datetime.utcnow().timestamp())%10000}"
    password = os.urandom(4).hex()

    create_ssh_user(username, password, plan_days)
    ehi = generate_ehi(username, password, str(plan_days))

    new_acc = VPNAccount(
        owner_id=user.id,
        username=username,
        password=password,
        plan=str(plan_days),
        expires_at=expires.isoformat(),
        ehi_file=ehi,
        notified_expire=0
    )

    db.add(new_acc)
    db.commit()

    return {"message": f"Plano de {plan_days} dias criado", "username": username, "password": password, "expires": expires.isoformat()}

# ------------------------------------------------------
# NOVA ROTA: CRIAR PLANO DE TESTE GRÁTIS
# ------------------------------------------------------
@router.post("/trial")
def create_trial(request_data: dict, db: Session = Depends(db)):
    user_id = request_data.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    plan_days = 3  # Duração do teste grátis
    expires = datetime.utcnow() + timedelta(days=plan_days)
    username = f"user{user.id}{int(datetime.utcnow().timestamp())%10000}"
    password = os.urandom(4).hex()

    create_ssh_user(username, password, plan_days)
    ehi = generate_ehi(username, password, str(plan_days))

    new_acc = VPNAccount(
        owner_id=user.id,
        username=username,
        password=password,
        plan=str(plan_days),
        expires_at=expires.isoformat(),
        ehi_file=ehi,
        notified_expire=0
    )

    db.add(new_acc)
    db.commit()

    return {
        "username": username,
        "password": password,
        "expires": expires.isoformat()
    }
