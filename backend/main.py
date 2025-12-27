import os
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from .database import Base, engine, SessionLocal
from .models import User, VPNAccount, LoginLog
from .schemas import UserCreate, UserLogin
from .auth import hash_password, verify_password
from .payment_routes import router as payment_router

# ------------------------------------------------------
# CONFIG JWT
# ------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "MUDE-ISSO-PARA-UM-SEGREDO-GIGANTE")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EHI_DIR = os.path.join(BASE_DIR, "ehis")

os.makedirs(EHI_DIR, exist_ok=True)

# ------------------------------------------------------
# APP
# ------------------------------------------------------
app = FastAPI()

app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/imagens", StaticFiles(directory="imagens"), name="imagens")

app.include_router(payment_router)

# ------------------------------------------------------
# DB
# ------------------------------------------------------
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------
# JWT
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
        raise HTTPException(status_code=401, detail="Token inválido")

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    return user

# ------------------------------------------------------
# REGISTER
# ------------------------------------------------------
@app.post("/api/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

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
@app.post("/api/login")
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    log = LoginLog(
        email=user.email,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", "unknown"),
        created_at=datetime.utcnow()
    )

    db.add(log)
    db.commit()

    token = create_token(user.id)
    return {"token": token}

# ------------------------------------------------------
# MEUS PLANOS
# ------------------------------------------------------
@app.get("/api/get-plans")
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

# ------------------------------------------------------
# DOWNLOAD EHI (CORRETO)
# ------------------------------------------------------
@app.get("/api/download-ehi/{plan_id}")
def download_ehi(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(VPNAccount).filter(
        VPNAccount.id == plan_id,
        VPNAccount.owner_id == user.id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")

    if not plan.ehi_file:
        raise HTTPException(
            status_code=400,
            detail="EHI ainda não gerado. Aguarde a confirmação do pagamento."
        )

    file_path = os.path.join(EHI_DIR, plan.ehi_file)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo EHI não encontrado")

    return FileResponse(
        path=file_path,
        filename=plan.ehi_file,
        media_type="application/octet-stream"
    )
