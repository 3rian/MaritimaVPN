from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import uuid
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

router = APIRouter()

# ==========================
# CONFIG MERCADO PAGO
# ==========================
ACCESS_TOKEN = "TEST-2636876912816804-120619-ecc30317c9b6194ef03217949a8bde44-149920841"

HEADERS_MP = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# ==========================
#  PLANOS
# ==========================
PLANOS = {
    "30_dias": {
        "nome": "Plano 30 dias",
        "valor": 12.00
    },
    "15_dias": {
        "nome": "Plano 15 dias",
        "valor": 7.00
    }
}

# ==========================
#  MODELO DE REQUISIÇÃO
# ==========================
class CriarPagamento(BaseModel):
    email: str
    plano: str  # 30_dias ou 15_dias

# ==========================
#  ENDPOINT PARA CRIAR PAGAMENTO PIX (QR CODE + COPIA E COLA)
# ==========================
@router.post("/pagamento")
def criar_pagamento(dados: CriarPagamento):

    if dados.plano not in PLANOS:
        raise HTTPException(status_code=400, detail="Plano inválido")

    plano = PLANOS[dados.plano]

    payload = {
        "transaction_amount": plano["valor"],
        "description": plano["nome"],
        "payment_method_id": "pix",
        "payer": {
            "email": dados.email
        },
        "notification_url": "https://api.maritimavpn.shop/webhook/mp"
    }

    # Header com idempotência obrigatória
    headers = HEADERS_MP.copy()
    headers["X-Idempotency-Key"] = str(uuid.uuid4())

    url = "https://api.mercadopago.com/v1/payments"
    resposta = requests.post(url, json=payload, headers=headers)

    if resposta.status_code not in [200, 201]:
        print("ERRO MP:", resposta.text)
        raise HTTPException(status_code=500, detail="Erro ao criar pagamento no Mercado Pago")

    data = resposta.json()

    return {
        "id": data["id"],
        "qr_code": data["point_of_interaction"]["transaction_data"]["qr_code"],          # COPIA E COLA
        "qr_code_base64": data["point_of_interaction"]["transaction_data"]["qr_code_base64"],  # QR EM IMAGEM
        "status": data["status"]
    }

# ==========================
#  WEBHOOK MERCADO PAGO
# ==========================
@router.post("/webhook/mp")
async def webhook_mp(request: Request):
    evento = await request.json()

    print("\n📌 WEBHOOK RECEBIDO ======================")
    print(evento)
    print("==========================================\n")

    # Mercado Pago envia "type" ou "topic"
    evento_tipo = evento.get("type") or evento.get("topic")

    if evento_tipo == "payment":
        pagamento_id = evento["data"]["id"]

        # Buscar detalhes do pagamento
        url = f"https://api.mercadopago.com/v1/payments/{pagamento_id}"
        resp = requests.get(url, headers=HEADERS_MP).json()

        status = resp.get("status")
        email = resp["payer"].get("email")

        print(f"🔎 Pagamento {pagamento_id} status: {status}")

        if status == "approved":
            enviar_email_confirmacao(email)

    return {"status": "ok"}

# ==========================
# FUNÇÃO PARA ENVIAR E-MAIL
# ==========================
def enviar_email_confirmacao(email_destino):

    email_origem = "maritimavpn@gmail.com"
    senha_app = "mbaq wsgk otax eyfz"  # sua senha de app

    assunto = "Pagamento confirmado - Maritima VPN"
    mensagem = """
    Olá! Seu pagamento foi confirmado com sucesso.

    Obrigado por usar a Maritima VPN!
    """

    msg = MIMEMultipart()
    msg["From"] = email_origem
    msg["To"] = email_destino
    msg["Subject"] = assunto

    msg.attach(MIMEText(mensagem, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
            servidor.starttls()
            servidor.login(email_origem, senha_app)
            servidor.sendmail(email_origem, email_destino, msg.as_string())
            print(f"✅ Email enviado para {email_destino}")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")

