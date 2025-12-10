from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from payment_routes import router as payment_router

app = FastAPI(
    title="Maritima VPN API",
    description="Backend de pagamentos e utilidades da Maritima VPN",
    version="1.0.0"
)

# ================================
#   CONFIG CORS
# ================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # pode filtrar depois para seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================
#   ROTAS
# ================================
app.include_router(payment_router)

# ================================
#   HEALTHCHECK
# ================================
@app.get("/")
def root():
    return {"status": "Maritima VPN backend rodando!"}

