import uuid
from fastapi import APIRouter, Request
import mercadopago
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

router = APIRouter()

# ================================
#  CONFIG MERCADO PAGO
# ================================
mp = mercadopago.SDK("TEST-2636876912816804-120619-ecc30317c9b6194ef03217949a8bde44-149920841")

# ================================
#  CONFIG EMAIL
# ================================
EMAIL_USER = "maritimavpn@gmail.com"
EMAIL_PASS = "mbaq wsgk otax eyfz"  # senha de app
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


# ================================
#  FUNÇÃO ENVIAR E-MAIL
# ================================
def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print("Email enviado com sucesso!")
    except Exception as e:
        print("Erro ao enviar email:", e)


# ================================
#  CRIAR ORDEM DE PAGAMENTO
# ================================
@router.post("/create_payment")
async def create_payment(data: dict):

    plan = data.get("plan")
    user_email = data.get("email")

    if plan == "30":
        price = 12
        days = 30
    elif plan == "15":
        price = 7
        days = 15
    else:
        return {"error": "Plano inválido"}

    preference_data = {
        "items": [
            {
                "title": f"Plano {days} dias – Maritima VPN",
                "quantity": 1,
                "unit_price": float(price)
            }
        ],
        "payer": {"email": user_email},
        "notification_url": "https://maritivavpn.shop/webhook",

        "back_urls": {
            "success": "https://seusite.com/sucesso",
            "failure": "https://seusite.com/erro"
        }
    }

    preference = mp.preference().create(preference_data)
    return {"init_point": preference["response"]["init_point"]}


# ================================
#  WEBHOOK MERCADO PAGO
# ================================
@router.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("Webhook recebido:", body)

    if body.get("topic") == "payment":

        payment_id = body["data"]["id"]
        info = mp.payment().get(payment_id)

        status = info["response"]["status"]
        email = info["response"]["payer"]["email"]

        if status == "approved":
            # Exemplo de e-mail enviado ao cliente
            send_email(
                email,
                "Pagamento Aprovado - Maritima VPN",
                f"""
                <h2>Pagamento aprovado!</h2>
                <p>Obrigado por comprar seu plano Maritima VPN.</p>
                <p>Seu acesso será liberado em instantes.</p>
                """
            )

    return {"status": "ok"}
