import smtplib
from email.message import EmailMessage

def send_ehi_email(to_email, username):
    filepath = f"generated/ehi/{username}.ehi"

    msg = EmailMessage()
    msg["Subject"] = "Seu arquivo EHI - Maritima VPN"
    msg["From"] = "suporte@maritimavpn.shop"
    msg["To"] = to_email

    msg.set_content(f"""
Olá!

Seu arquivo EHI já está pronto.

Faça download e importe no HTTP Injector.

Obrigado por usar a Maritima VPN!
""")

    with open(filepath, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="octet-stream",
            filename=f"{username}.ehi"
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("seuemail@gmail.com", "SUASENHA_APLICATIVO")
        smtp.send_message(msg)
