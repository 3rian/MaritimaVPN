from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from database import SessionLocal
from models import VPNAccount, User
from email_sender import send_email
from datetime import datetime
from scheduler import start_scheduler

def check_expirations():
    db: Session = SessionLocal()
    now = datetime.now()

    accounts = db.query(VPNAccount).all()

    for acc in accounts:
        expires = datetime.fromisoformat(acc.expires_at)

        days_left = (expires - now).days

        user = db.query(User).filter(User.id == acc.owner_id).first()

        if not user:
            continue

        # Notificar 3 dias antes
        if days_left == 3:
            send_email(
                user.email,
                "Sua VPN expira em 3 dias",
                f"Olá {user.name}, sua VPN ({acc.username}) expira no dia {expires}. Renove para evitar interrupções."
            )

        # Notificar 1 dia
        elif days_left == 1:
            send_email(
                user.email,
                "Sua VPN expira amanhã",
                f"Olá {user.name}, sua VPN ({acc.username}) expira amanhã ({expires}). Recomendamos renovar hoje."
            )

        # Notificar expiração
        elif days_left <= 0:
            send_email(
                user.email,
                "Sua VPN expirou",
                f"Olá {user.name}, sua VPN ({acc.username}) expirou. Faça a renovação para continuar utilizando."
            )

    db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_expirations, "interval", hours=12)  # roda a cada 12h
    scheduler.start()



@app.on_event("startup")
def start():
    start_scheduler()
