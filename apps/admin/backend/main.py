from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from shared.config.database import get_db
from shared.config.settings import settings

# Import routers with absolute path to work in both dev and Docker
try:
    from .routers import settings_router, users_router, analytics_router, system_router, prompt_router, payments_router
except ImportError:
    # Fallback for Docker environment
    from apps.admin.backend.routers import settings_router, users_router, analytics_router, system_router, prompt_router, payments_router

app = FastAPI(
    title="Veloxe Admin Panel API",
    description="Beautiful admin panel for Veloxe chatbot management",
    version="1.0.0"
)

# Get allowed origins from environment variable or use defaults
allowed_origins = os.getenv("ADMIN_CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:5173").split(",")
# Add the server IP if accessing directly via IP
server_ip = os.getenv("SERVER_IP")
if server_ip:
    allowed_origins.append(f"http://{server_ip}:3000")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple admin authentication"""
    if credentials.credentials != settings.admin_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )
    return credentials.credentials

# Include routers with admin auth
app.include_router(
    settings_router.router,
    prefix="/api/settings",
    tags=["Settings"],
    dependencies=[Depends(verify_admin_token)]
)

app.include_router(
    users_router.router,
    prefix="/api/users",
    tags=["Users"],
    dependencies=[Depends(verify_admin_token)]
)

app.include_router(
    analytics_router.router,
    prefix="/api/analytics",
    tags=["Analytics"],
    dependencies=[Depends(verify_admin_token)]
)

app.include_router(
    system_router.router,
    prefix="/api/system",
    tags=["System"]
)

app.include_router(
    prompt_router.router,
    prefix="/api/prompt",
    tags=["Prompt Testing"],
    dependencies=[Depends(verify_admin_token)]
)

# Payment webhooks (no auth required for external webhooks)
app.include_router(
    payments_router.router,
    prefix="/api/payments",
    tags=["Payments"]
)

@app.get("/")
async def root():
    return {
        "message": "Veloxe Admin Panel API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "admin-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="145.223.117.108", port=8000)