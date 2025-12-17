import smtplib
from email.message import EmailMessage
import os

def send_ehi_email(to_email, username):
    """
    Envia um e-mail com o arquivo .ehi gerado como anexo.
    """
    filepath = f"generated/ehi/{username}.ehi"

    # Verifica se o arquivo existe antes de tentar enviá-lo
    if not os.path.exists(filepath):
        print(f"Erro: O arquivo {filepath} não foi encontrado.")
        return

    msg = EmailMessage()
    msg["Subject"] = "Seu arquivo EHI - Maritima VPN"
    msg["From"] = os.getenv("EMAIL_SENDER")  # Melhor usar variáveis de ambiente para não deixar expostas as credenciais
    msg["To"] = to_email

    msg.set_content(f"""
Olá!

Seu arquivo EHI já está pronto.

Faça download e importe no HTTP Injector.

Obrigado por usar a Maritima VPN!
""")

    try:
        with open(filepath, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="octet-stream",
                filename=f"{username}.ehi"
            )

        # Configurações de SMTP usando Gmail (método de login com senha de aplicativo)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            email_sender = os.getenv("EMAIL_SENDER")  # E-mail de envio, que deve estar configurado como variável de ambiente
            app_password = os.getenv("EMAIL_APP_PASSWORD")  # Senha do aplicativo, que deve estar configurada como variável de ambiente
            smtp.login(email_sender, app_password)
            smtp.send_message(msg)
        
        print(f"E-mail enviado com sucesso para {to_email}.")

    except Exception as e:
        print(f"Erro ao enviar o e-mail: {e}")
        
def send_email(to_email, username):
        return send_ehi_email(to_email, username)

