from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from jose import JWTError, jwt
import bcrypt
from file_handler import FileHandler
from recon_engine import ReconciliationEngine
from rollback_manager import RollbackManager, RollbackLevel
from exception_handler import ExceptionHandler, ExceptionType, RecoveryStrategy
import logging
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# AUTHENTICATION SETUP
# ============================================================================

SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Generate password hash using bcrypt directly
HASHED_PASSWORD = bcrypt.hashpw("Recon".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Fake user database (replace with real database in production)
fake_users_db = {
    "Verif.AI": {
        "username": "Verif.AI",
        "full_name": "UPI Reconciliation System",
        "email": "admin@verif.ai",
        "hashed_password": HASHED_PASSWORD,
        "disabled": False,
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def authenticate_user(fake_db: dict, username: str, password: str):
    """Authenticate a user"""
    user = fake_db.get(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(title="UPI Reconciliation API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# INITIALIZE COMPONENTS
# ============================================================================

file_handler = FileHandler()
recon_engine = ReconciliationEngine()
rollback_manager = RollbackManager(upload_dir=UPLOAD_DIR, output_dir=OUTPUT_DIR)
exception_handler = ExceptionHandler(upload_dir=UPLOAD_DIR, output_dir=OUTPUT_DIR)

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/v1/auth/login")
async def login(request: Request):
    """Authenticate user and return access token"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        logger.info(f"Login attempt for username: {username}")

        if not username or not password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required"
            )

        user = authenticate_user(fake_users_db, username, password)
        if not user:
            logger.warning(f"Failed login attempt for username: {username}")
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password"
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )

        logger.info(f"Successful login for username: {username}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user["username"],
                "full_name": user["full_name"],
                "email": user["email"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/auth/me")
async def get_current_user(request: Request):
    """Get current user information"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authentication")

        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")

        user = fake_users_db.get(username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return {
            "username": user["username"],
            "full_name": user["full_name"],
            "email": user["email"]
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "UPI Reconciliation API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)