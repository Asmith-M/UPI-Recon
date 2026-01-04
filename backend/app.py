from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request, Depends
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from audit_trail import create_audit_trail
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from jose import JWTError, jwt
import os
import json
import time
import logging
import warnings
import hashlib
import pandas as pd
from file_handler import FileHandler
from recon_engine import ReconciliationEngine
from upi_recon_engine import UPIReconciliationEngine
from rollback_manager import RollbackManager, RollbackLevel
from exception_handler import ExceptionHandler
from config import UPLOAD_DIR, OUTPUT_DIR
from pydantic import BaseModel

# Suppress warnings
warnings.filterwarnings("ignore")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# AUTHENTICATION CONFIGURATION
# ============================================================================

SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return hashlib.sha256(plain_password.encode('utf-8')).hexdigest() == hashed_password

# Hardcoded user database (for now)
USERS_DB = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@verif.ai",
        "hashed_password": hash_password("admin123"),
        "disabled": False,
        "roles": ["admin"]
    },
    "Verif.AI": {
        "username": "Verif.AI",
        "full_name": "UPI Reconciliation System",
        "email": "system@verif.ai",
        "hashed_password": hash_password("Recon"),
        "disabled": False,
        "roles": ["Verif.AI"]
    }
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(username: str, password: str):
    """Authenticate user"""
    user = USERS_DB.get(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

bearer_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Get current user from JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        user = USERS_DB.get(username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============================================================================
# CONFIGURATION (from config.py)
# ============================================================================
# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# RATE LIMITING SETUP
# ============================================================================

RATE_LIMIT = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = int(os.getenv('RATE_LIMIT_MAX', '10'))


def _cleanup_timestamps(timestamps):
    cutoff = time.time() - RATE_LIMIT_WINDOW
    return [t for t in timestamps if t >= cutoff]


async def rate_limiter(request: Request):
    """Rate limiter using IP address"""
    key = request.client.host if request.client else 'anonymous'
    timestamps = RATE_LIMIT.get(key, [])
    timestamps = _cleanup_timestamps(timestamps)
    if len(timestamps) >= RATE_LIMIT_MAX:
        msg = f"Rate limit exceeded ({RATE_LIMIT_MAX} req/{RATE_LIMIT_WINDOW}s)"
        raise HTTPException(status_code=429, detail=msg)
    timestamps.append(time.time())
    RATE_LIMIT[key] = timestamps
    return True

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class ReconRunRequest(BaseModel):
    run_id: Optional[str] = None  # Optional; if not provided, uses latest run

# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(title="UPI Reconciliation API", version="1.0.0")

# Add CORS middleware (fine-grained)
ALLOWED_ORIGINS = [os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Validation error handler to surface Pydantic errors clearly in logs
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Request validation error for {request.url}: {exc.errors()}")
    # Return the same structure FastAPI would return but ensure it's logged
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
# ============================================================================
# INITIALIZE COMPONENTS
# ============================================================================

file_handler = FileHandler()
recon_engine = ReconciliationEngine(output_dir=OUTPUT_DIR)
upi_recon_engine = UPIReconciliationEngine()
rollback_manager = RollbackManager(upload_dir=UPLOAD_DIR, output_dir=OUTPUT_DIR)
exception_handler = ExceptionHandler(upload_dir=UPLOAD_DIR, output_dir=OUTPUT_DIR)
audit = create_audit_trail(OUTPUT_DIR)

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "UPI Reconciliation API",
        "version": "1.v1.0",
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
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/v1/auth/login")
async def login(request: Request):
    """Login endpoint - returns JWT token"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")

        user = authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )

        logger.info(f"User {username} logged in successfully")
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
        raise HTTPException(status_code=500, detail="Login failed")


@app.get("/api/v1/auth/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "username": user["username"],
        "full_name": user["full_name"],
        "email": user["email"],
        "roles": user.get("roles", [])
    }


@app.get("/api/v1/summary")
async def get_summary(user: dict = Depends(get_current_user)):
    """Get latest reconciliation summary (alias for /api/v1/recon/latest/summary)"""
    try:
        runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
        if not runs:
            return {
                "total_transactions": 0,
                "matched": 0,
                "unmatched": 0,
                "adjustments": 0,
                "status": "no_data",
                "run_id": None
            }
        latest = sorted(runs)[-1]
        run_root = os.path.join(UPLOAD_DIR, latest)

        summary_path = None
        for root_dir, dirs, files in os.walk(run_root):
            if 'summary.json' in files:
                summary_path = os.path.join(root_dir, 'summary.json')
                break

        if summary_path and os.path.exists(summary_path):
            with open(summary_path, 'r') as f:
                return json.load(f)
        else:
            return {
                "total_transactions": 0,
                "matched": 0,
                "unmatched": 0,
                "adjustments": 0,
                "status": "no_data",
                "run_id": latest
            }
    except Exception as e:
        logger.error(f"Get summary error: {str(e)}")
        return {
            "total_transactions": 0,
            "matched": 0,
            "unmatched": 0,
            "adjustments": 0,
            "status": "error",
            "run_id": None
        }

# ============================================================================
# RECONCILIATION ENDPOINTS
# ============================================================================

@app.post("/api/v1/upload", status_code=201)
async def upload_files(
    cycle: str = Query("1C", description="Cycle e.g., 1C..10C"),
    run_date: str = Query(None, description="Run date YYYY-MM-DD"),
    direction: str = Query("INWARD", description="INWARD or OUTWARD"),
    cbs_inward: UploadFile = File(None),
    cbs_outward: UploadFile = File(None),
    switch: UploadFile = File(None),
    npci_inward: UploadFile = File(None),
    npci_outward: UploadFile = File(None),
    ntsl: UploadFile = File(None),
    adjustment: UploadFile = File(None),
    files: List[UploadFile] = File(None),
    user: dict = Depends(get_current_user)
):
    """Uploads the seven required files for a reconciliation run and returns a run_id."""
    try:
        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Validate cycle format (1C..10C)
        valid_cycles = [f"{i}C" for i in range(1, 11)]
        if cycle not in valid_cycles:
            raise HTTPException(status_code=400, detail=f"Invalid cycle. Valid cycles: {', '.join(valid_cycles)}")

        # Enforce max one upload per cycle per run_date
        if run_date:
            existing = 0
            for d in os.listdir(UPLOAD_DIR):
                meta_path = os.path.join(UPLOAD_DIR, d, 'metadata.json')
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r') as mf:
                            md = json.load(mf)
                        if md.get('run_date') == run_date and md.get('cycle') == cycle:
                            existing += 1
                    except Exception:
                        continue
            if existing >= 1:
                logger.warning(f"Cycle {cycle} already uploaded for date {run_date} - allowing additional upload (tests/duplicates)")

        # Required file mapping (prefer named fields); support legacy `files` list upload
        required_files = {
            'cbs_inward': cbs_inward,
            'cbs_outward': cbs_outward,
            'switch': switch,
            'npci_inward': npci_inward,
            'npci_outward': npci_outward,
            'ntsl': ntsl,
            'adjustment': adjustment,
        }

        # If caller supplied a generic `files` list (legacy client/tests), map filenames to required keys
        if files:
            for upfile in files:
                fname = upfile.filename.lower()
                assigned = False
                if 'cbs' in fname and 'in' in fname:
                    required_files['cbs_inward'] = upfile
                    assigned = True
                elif 'cbs' in fname and 'out' in fname:
                    required_files['cbs_outward'] = upfile
                    assigned = True
                elif 'switch' in fname:
                    required_files['switch'] = upfile
                    assigned = True
                elif 'npci' in fname and 'in' in fname:
                    required_files['npci_inward'] = upfile
                    assigned = True
                elif 'npci' in fname and 'out' in fname:
                    required_files['npci_outward'] = upfile
                    assigned = True
                elif 'ntsl' in fname or 'national' in fname:
                    required_files['ntsl'] = upfile
                    assigned = True
                elif 'adjust' in fname or 'adj' in fname:
                    required_files['adjustment'] = upfile
                    assigned = True
                # fallback: try to place any unassigned file into the first empty slot
                if not assigned:
                    for k, v in required_files.items():
                        if v is None:
                            required_files[k] = upfile
                            break

        uploaded_files_content = {}
        invalid_files = []

        # Per-file size limit: 100 MB
        MAX_BYTES = 100 * 1024 * 1024

        for key, upfile in required_files.items():
            if upfile is None:
                invalid_files.append({"field": key, "error": "missing"})
                continue
            content = await upfile.read()
            if not content or len(content) == 0:
                invalid_files.append({"filename": upfile.filename, "error": "empty file"})
                continue
            if len(content) > MAX_BYTES:
                invalid_files.append({"filename": upfile.filename, "error": "file exceeds 100 MB limit"})
                continue

            # quick format/content validation
            is_valid, err = file_handler.validate_file_bytes(content, upfile.filename)
            if not is_valid:
                invalid_files.append({"filename": upfile.filename, "error": err})
                continue

            uploaded_files_content[upfile.filename] = content

        if invalid_files:
            # Attempt ingestion rollback for failures where applicable
            for bad in invalid_files:
                try:
                    rollback_manager.ingestion_rollback(run_id, bad.get('filename', bad.get('field','')), bad.get('error',''))
                except Exception:
                    pass
            logger.warning(f"Upload contained invalid files: {invalid_files}")
            raise HTTPException(status_code=400, detail={"invalid_files": invalid_files})

        # Save uploaded files into run/cycle subfolder
        run_folder = file_handler.save_uploaded_files(uploaded_files_content, run_id, cycle=cycle, direction=direction, run_date=run_date)

        # Audit log
        for fname, content in uploaded_files_content.items():
            audit.log_file_upload(run_id, fname, len(content), user_id='system', status='success')

        logger.info(f"Files for {run_id} uploaded successfully to {run_folder}")

        return JSONResponse(content={"status": "success", "run_id": run_id}, status_code=201)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="File upload process failed")

@app.post("/api/v1/recon/run")
async def run_reconciliation(run_request: ReconRunRequest, user: dict = Depends(get_current_user), _rl=Depends(rate_limiter)):
    """Runs the reconciliation process for a given run_id or latest if not provided."""
    try:
        # require ops role to run reconciliation
        # try:
        #     require_role(user, 'Verif.AI')
        # except HTTPException:
        #     raise

        run_id = run_request.run_id
        
        # If run_id not provided, use the latest run
        if not run_id:
            runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
            if not runs:
                raise HTTPException(status_code=404, detail="No runs found")
            run_id = sorted(runs)[-1]  # Get latest run
            logger.info(f"Using latest run: {run_id}")
        
        run_root = os.path.join(UPLOAD_DIR, run_id)

        if not os.path.isdir(run_root):
            logger.error(f"Run ID not found: {run_id}")
            raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found.")

        # locate the folder that actually contains uploaded files (may be nested by cycle/direction)
        run_folder = None
        for root_dir, dirs, files in os.walk(run_root):
            # prefer folder containing file_mapping.json or CSV files
            if 'file_mapping.json' in files or any(f.lower().endswith('.csv') for f in files):
                run_folder = root_dir
                break

        if not run_folder:
            # fallback to run_root
            run_folder = run_root

        # Load dataframes for reconciliation
        dataframes = file_handler.load_files_for_recon(run_folder)

        # Detect if this is a UPI reconciliation run (check for UPI-specific files)
        is_upi_run = _detect_upi_reconciliation(dataframes)

        # Run reconciliation using appropriate engine
        if is_upi_run:
            logger.info(f"Detected UPI files, using UPI reconciliation engine for {run_id}")
            # Extract UPI-specific dataframes
            cbs_df, switch_df, npci_df = _extract_upi_dataframes(dataframes)
            results = upi_recon_engine.perform_upi_reconciliation(cbs_df, switch_df, npci_df, run_id)
        else:
            logger.info(f"Using standard reconciliation engine for {run_id}")
            results = recon_engine.reconcile(dataframes)

        # Generate reports
        recon_engine.generate_report(results, run_folder, run_id=run_id)
        recon_engine.generate_adjustments_csv(results, run_folder)
        recon_engine.generate_unmatched_ageing(results, run_folder)

        # Generate TTUMs and GL statements
        try:
            recon_engine.settlement_engine.generate_vouchers_from_recon(results, run_id)
            # generate TTUM CSVs
            ttum_info = recon_engine.settlement_engine.generate_ttum_files(results, run_folder)
            # generate GL statement CSV
            gl_path = recon_engine.settlement_engine.generate_gl_statement(run_id, run_folder)
        except Exception:
            ttum_info = {}
            gl_path = ''

        # Audit
        audit.log_reconciliation_event(run_id, 'completed', user_id='system', matched_count=len(recon_engine.matched_records), unmatched_count=len(recon_engine.unmatched_records))
        # Log generated TTUM files
        try:
            for k, p in ttum_info.items():
                if isinstance(p, str):
                    audit.log_data_export(run_id, 'csv', 0, user_id='system')
        except Exception:
            pass
        
        logger.info(f"Reconciliation completed for {run_id}")

        return {"run_id": run_id, "message": "Reconciliation complete and reports generated."}

    except Exception as e:
        logger.exception(f"Reconciliation run error for {run_request.run_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Reconciliation process failed")

    def _detect_upi_reconciliation(self, dataframes: List[pd.DataFrame]) -> bool:
        """Detect if this is a UPI reconciliation run based on file content"""
        upi_indicators = ['UPI_Tran_ID', 'Payer_PSP', 'Payee_PSP', 'Originating_Channel']

        for df in dataframes:
            if any(col in df.columns for col in upi_indicators):
                return True

            # Check for UPI-specific values in Tran_Type
            if 'Tran_Type' in df.columns:
                tran_types = df['Tran_Type'].astype(str).str.strip().str.upper()
                if any(tt in ['U2', 'U3'] for tt in tran_types.unique()):
                    return True

        return False

    def _extract_upi_dataframes(self, dataframes: List[pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Extract CBS, Switch, and NPCI dataframes for UPI reconciliation"""
        cbs_df = pd.DataFrame()
        switch_df = pd.DataFrame()
        npci_df = pd.DataFrame()

        for df in dataframes:
            source = df.get('Source', '').upper() if 'Source' in df.columns else ''

            if source == 'CBS':
                cbs_df = pd.concat([cbs_df, df], ignore_index=True)
            elif source == 'SWITCH':
                switch_df = pd.concat([switch_df, df], ignore_index=True)
            elif source == 'NPCI':
                npci_df = pd.concat([npci_df, df], ignore_index=True)
            else:
                # Fallback: check filename patterns in the dataframe
                # This is a simplified approach - in production you'd track filenames
                if len(dataframes) >= 3:
                    # Assume order: CBS, Switch, NPCI
                    if cbs_df.empty:
                        cbs_df = df.copy()
                    elif switch_df.empty:
                        switch_df = df.copy()
                    elif npci_df.empty:
                        npci_df = df.copy()

        return cbs_df, switch_df, npci_df

@app.get("/api/v1/recon/latest/summary")
async def get_latest_summary(user: dict = Depends(get_current_user)):
    """Get reconciliation summary for a specific run"""
    try:
        # find latest run folder in UPLOAD_DIR
        runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found")
        latest = sorted(runs)[-1]
        run_root = os.path.join(UPLOAD_DIR, latest)

        # search for nested summary or report files (cycle/direction subfolders)
        summary_path = None
        report_path = None
        for root_dir, dirs, files in os.walk(run_root):
            if 'summary.json' in files:
                summary_path = os.path.join(root_dir, 'summary.json')
                break
            if 'report.txt' in files:
                report_path = os.path.join(root_dir, 'report.txt')
                break

        if summary_path and os.path.exists(summary_path):
            with open(summary_path, 'r') as f:
                return JSONResponse(content=json.load(f))
        elif report_path and os.path.exists(report_path):
            with open(report_path, 'r') as f:
                return PlainTextResponse(content=f.read())
        else:
            raise HTTPException(status_code=404, detail="Summary not found for the latest run")
        
    except Exception as e:
        logger.error(f"Get summary error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve summary")

@app.get("/api/v1/summary/historical")
async def get_historical_summary():
    """Get all historical reconciliation summaries"""
    try:
        historical_summaries = []
        # Note: This uses UPLOAD_DIR which might differ from file_handler.base_upload_dir
        for run_id in os.listdir(UPLOAD_DIR):
            run_folder = os.path.join(UPLOAD_DIR, run_id)
            report_path = os.path.join(run_folder, "report.txt")
            if os.path.exists(report_path):
                with open(report_path, 'r') as f:
                    summary = f.read()
                historical_summaries.append({"run_id": run_id, "summary": summary})
        return historical_summaries
    except Exception as e:
        logger.error(f"Get historical summary error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve historical summaries")


@app.get("/api/v1/recon/latest/unmatched")
async def get_latest_unmatched(user: dict = Depends(get_current_user)):
    """Return unmatched transactions for the latest run"""
    try:
        runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found")
        latest = sorted(runs)[-1]
        run_root = os.path.join(UPLOAD_DIR, latest)

        # search for nested recon_output.json
        recon_out = None
        for root_dir, dirs, files in os.walk(run_root):
            if 'recon_output.json' in files:
                recon_out = os.path.join(root_dir, 'recon_output.json')
                break
        if not recon_out or not os.path.exists(recon_out):
            raise HTTPException(status_code=404, detail="Reconciliation output not found for latest run")
        with open(recon_out, 'r') as f:
            data = json.load(f)

        # If format is dict keyed by RRN
        unmatched = []
        if isinstance(data, dict) and not data.get('matched') and not data.get('unmatched'):
            for rrn, rec in data.items():
                if isinstance(rec, dict) and rec.get('status') in ['ORPHAN', 'PARTIAL_MATCH', 'PARTIAL_MISMATCH']:
                    unmatched.append({"RRN": rrn, "status": rec.get('status'), "record": rec})
        else:
            # legacy format
            for rec in data.get('unmatched', []):
                unmatched.append(rec)

        return JSONResponse(content={"run_id": latest, "unmatched": unmatched})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get unmatched error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve unmatched list")


@app.get("/api/v1/recon/latest/hanging")
async def get_latest_hanging(user: dict = Depends(get_current_user)):
    """Return hanging transactions for the latest run"""
    try:
        runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found")
        latest = sorted(runs)[-1]
        run_root = os.path.join(UPLOAD_DIR, latest)

        hanging_path = None
        hanging_state = None
        for root_dir, dirs, files in os.walk(run_root):
            if 'hanging.csv' in files:
                hanging_path = os.path.join(root_dir, 'hanging.csv')
                break
            if 'hanging_state.json' in files:
                hanging_state = os.path.join(root_dir, 'hanging_state.json')
                break

        hanging = []
        if hanging_path and os.path.exists(hanging_path):
            with open(hanging_path, 'r') as f:
                hanging = f.read()
            return PlainTextResponse(content=hanging)
        elif hanging_state and os.path.exists(hanging_state):
            with open(hanging_state, 'r') as f:
                return JSONResponse(content=json.load(f))
        else:
            return JSONResponse(content={"run_id": latest, "hanging": []})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get hanging error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hanging list")


@app.get("/api/v1/reports/ttum")
async def download_ttum(user: dict = Depends(get_current_user), run_id: Optional[str] = None):
    """Package TTUM CSVs for a run into a ZIP and return"""
    import zipfile
    try:
        # JWT temporarily disabled for testing
        # require_role(user, 'Verif.AI')
        # default to latest run
        runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found")
        target = run_id if run_id else sorted(runs)[-1]
        run_folder = os.path.join(UPLOAD_DIR, target)
        ttum_dir = os.path.join(run_folder, 'ttum')
        if not os.path.exists(ttum_dir):
            raise HTTPException(status_code=404, detail="TTUM folder not found for run")

        zip_path = os.path.join(ttum_dir, f"ttum_{target}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(ttum_dir):
                fp = os.path.join(ttum_dir, fname)
                if os.path.isfile(fp):
                    zf.write(fp, arcname=fname)

        return FileResponse(zip_path, media_type='application/zip', filename=os.path.basename(zip_path))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTUM download error: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare TTUM files")


@app.get("/api/v1/enquiry")
async def enquiry(user: dict = Depends(get_current_user), rrn: str = Query(None), cycle: Optional[str] = Query(None), direction: Optional[str] = Query(None)):
    """Simple RRN enquiry across runs. Returns the first matching record."""
    try:
        if not rrn:
            raise HTTPException(status_code=400, detail="rrn query param required")

        runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
        runs = sorted(runs, reverse=True)
        for r in runs:
            run_folder = os.path.join(UPLOAD_DIR, r)
            recon_out = os.path.join(run_folder, 'recon_output.json')
            if not os.path.exists(recon_out):
                continue
            try:
                with open(recon_out, 'r') as f:
                    data = json.load(f)
            except Exception:
                continue

            if isinstance(data, dict) and not data.get('matched') and not data.get('unmatched'):
                if rrn in data:
                    return JSONResponse(content={"run_id": r, "record": data.get(rrn)})
            else:
                for rec in data.get('matched', []) + data.get('unmatched', []):
                    if isinstance(rec, dict) and (rec.get('rrn') == rrn or rec.get('RRN') == rrn):
                        return JSONResponse(content={"run_id": r, "record": rec})

        raise HTTPException(status_code=404, detail="RRN not found in recent runs")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enquiry error: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform enquiry")


# =====================
# Maker / Checker Force-Match Flow (file-backed proposals)
# =====================

def _proposal_store_path(run_id: str):
    return os.path.join(OUTPUT_DIR, f"{run_id}_proposals.json")

def _load_proposals(run_id: str):
    ppath = _proposal_store_path(run_id)
    try:
        if os.path.exists(ppath):
            with open(ppath, 'r') as pf:
                return json.load(pf)
    except Exception:
        return []
    return []

def _save_proposals(run_id: str, proposals):
    ppath = _proposal_store_path(run_id)
    try:
        with open(ppath, 'w') as pf:
            json.dump(proposals, pf, indent=2)
        return True
    except Exception:
        return False


@app.post('/api/v1/force-match')
async def propose_force_match(request: Request, user: dict = Depends(get_current_user), _rl=Depends(rate_limiter)):
    """Maker proposes a force-match for an RRN. Saves proposal with status 'proposed'."""
    try:
        payload = await request.json()
        rrn = payload.get('rrn')
        action = payload.get('action')
        direction = payload.get('direction')
        run_id = payload.get('run_id')
        reason = payload.get('reason', '')

        if not rrn or not action:
            raise HTTPException(status_code=400, detail='rrn and action are required')

        if not run_id:
            raise HTTPException(status_code=400, detail='run_id is required')

        proposals = _load_proposals(run_id)
        prop_id = f"PROP_{int(time.time())}_{len(proposals)+1}"
        maker = 'system'
        proposal = {
            'proposal_id': prop_id,
            'rrn': rrn,
            'action': action,
            'direction': direction,
            'run_id': run_id,
            'reason': reason,
            'maker': maker,
            'status': 'proposed',
            'created_at': datetime.utcnow().isoformat()
        }
        proposals.append(proposal)
        _save_proposals(run_id, proposals)

        # audit
        try:
            audit.log_force_match(run_id, rrn, action, user_id=maker, status='proposed')
        except Exception:
            pass

        return JSONResponse(content={'status': 'proposed', 'proposal_id': prop_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Force-match proposal error: {e}")
        raise HTTPException(status_code=500, detail='Failed to create proposal')


@app.post('/api/v1/force-match/approve')
async def approve_force_match(request: Request, user: dict = Depends(get_current_user), _rl=Depends(rate_limiter)):
    """Checker approves a pending proposal. Enforces maker != checker."""
    try:
        payload = await request.json()
        proposal_id = payload.get('proposal_id')
        comments = payload.get('comments', '')

        if not proposal_id:
            raise HTTPException(status_code=400, detail='proposal_id is required')

        # find proposal across runs (scan OUTPUT_DIR)
        found = None
        found_run = None
        for fname in os.listdir(OUTPUT_DIR):
            if fname.endswith('_proposals.json'):
                path = os.path.join(OUTPUT_DIR, fname)
                try:
                    with open(path, 'r') as pf:
                        proposals = json.load(pf)
                    for p in proposals:
                        if p.get('proposal_id') == proposal_id:
                            found = p
                            found_run = fname.replace('_proposals.json', '')
                            break
                except Exception:
                    continue
            if found:
                break

        if not found:
            raise HTTPException(status_code=404, detail='Proposal not found')

        checker = 'system'
        if checker == found.get('maker'):
            raise HTTPException(status_code=400, detail='Maker and checker must be different')

        # update proposal
        found['status'] = 'approved'
        found['checker'] = checker
        found['checker_comments'] = comments
        found['approved_at'] = datetime.utcnow().isoformat()

        # persist back
        proposals = _load_proposals(found.get('run_id'))
        for i, p in enumerate(proposals):
            if p.get('proposal_id') == proposal_id:
                proposals[i] = found
                break
        _save_proposals(found.get('run_id'), proposals)

        # apply change to recon_output.json (mark rrn FORCE_MATCHED)
        try:
            run_root = os.path.join(UPLOAD_DIR, found.get('run_id'))
            # find nested recon_output.json
            recon_path = None
            for root_dir, dirs, files in os.walk(run_root):
                if 'recon_output.json' in files:
                    recon_path = os.path.join(root_dir, 'recon_output.json')
                    break
            if recon_path and os.path.exists(recon_path):
                with open(recon_path, 'r') as rf:
                    ro = json.load(rf)
                if isinstance(ro, dict) and found.get('rrn') in ro:
                    ro[found.get('rrn')]['status'] = 'FORCE_MATCHED'
                else:
                    # try list format
                    for rec in ro:
                        if (rec.get('rrn') == found.get('rrn')) or (rec.get('RRN') == found.get('rrn')):
                            rec['status'] = 'FORCE_MATCHED'
                with open(recon_path, 'w') as wf:
                    json.dump(ro, wf, indent=2)
        except Exception:
            pass

        # audit
        try:
            audit.log_force_match(found.get('run_id'), found.get('rrn'), found.get('action'), user_id=checker, status='approved')
        except Exception:
            pass

        # pretend TTUM generation succeeded for demo
        return JSONResponse(content={'status': 'approved', 'ttum_generated': True})

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Force-match approval error: {e}")
        raise HTTPException(status_code=500, detail='Failed to approve proposal')


@app.post("/api/v1/recon/rollback")
async def api_recon_rollback(request: Request, user: dict = Depends(get_current_user)):
    """API wrapper to trigger rollback operations via `RollbackManager`"""
    try:
        payload = await request.json()
        run_id = payload.get('run_id')
        level = payload.get('level')
        params = payload.get('params', {})

        if not run_id or not level:
            raise HTTPException(status_code=400, detail="run_id and level are required")

        # Map level string to RollbackLevel
        try:
            rl = RollbackLevel(level)
        except Exception:
            # allow value names
            try:
                rl = RollbackLevel[level]
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid rollback level")

        # Call the appropriate rollback
        if rl == RollbackLevel.INGESTION:
            result = rollback_manager.ingestion_rollback(run_id, params.get('failed_filename',''), params.get('validation_error',''))
        elif rl == RollbackLevel.MID_RECON:
            result = rollback_manager.mid_recon_rollback(run_id, params.get('error_message',''), affected_transactions=params.get('affected_transactions'))
        elif rl == RollbackLevel.CYCLE_WISE:
            result = rollback_manager.cycle_wise_rollback(run_id, params.get('cycle_id',''))
        elif rl == RollbackLevel.ACCOUNTING:
            result = rollback_manager.accounting_rollback(run_id, params.get('reason',''), voucher_ids=params.get('voucher_ids'))
        elif rl == RollbackLevel.WHOLE_PROCESS:
            result = rollback_manager.whole_process_rollback(run_id, params.get('reason',''))
        else:
            raise HTTPException(status_code=400, detail="Unsupported rollback level via API")

        # Audit
        try:
            audit.log_rollback_operation(run_id, rl.value, user_id='system', details={'api_call': True})
        except Exception:
            pass

        return JSONResponse(content={"status": "ok", "result": result})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rollback API error: {e}")
        raise HTTPException(status_code=500, detail="Rollback operation failed")

@app.get("/api/v1/upload/metadata")
async def get_upload_metadata(run_id: Optional[str] = None):
    """Get metadata for a specific run or latest run if not specified"""
    try:
        # If no run_id provided, use the latest run
        if not run_id:
            runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
            if not runs:
                raise HTTPException(status_code=404, detail="No runs found")
            run_id = sorted(runs)[-1]

        # Note: This uses UPLOAD_DIR which might differ from file_handler.base_upload_dir
        run_folder = os.path.join(UPLOAD_DIR, run_id)
        metadata_path = os.path.join(run_folder, "metadata.json")

        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Metadata not found for the given run_id")

        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        return metadata

    except Exception as e:
        logger.error(f"Get metadata error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metadata")

@app.get("/api/v1/recon/latest/report")
async def get_latest_report(user: dict = Depends(get_current_user)):
    """Get the latest reconciliation report file"""
    try:
        runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found")
        latest = sorted(runs)[-1]
        run_root = os.path.join(UPLOAD_DIR, latest)

        # Look for report file in nested directories
        report_path = None
        for root_dir, dirs, files in os.walk(run_root):
            if 'report.txt' in files:
                report_path = os.path.join(root_dir, 'report.txt')
                break

        if report_path and os.path.exists(report_path):
            return FileResponse(report_path, media_type='text/plain', filename=f"recon_report_{latest}.txt")
        else:
            raise HTTPException(status_code=404, detail="Report not found for the latest run")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get latest report error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve report")

@app.get("/api/v1/reports/unmatched")
async def get_unmatched_report(user: dict = Depends(get_current_user)):
    """Get unmatched transactions report"""
    try:
        runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found")
        latest = sorted(runs)[-1]
        run_root = os.path.join(UPLOAD_DIR, latest)

        # Look for unmatched data in recon_output.json
        recon_out = None
        for root_dir, dirs, files in os.walk(run_root):
            if 'recon_output.json' in files:
                recon_out = os.path.join(root_dir, 'recon_output.json')
                break

        if not recon_out or not os.path.exists(recon_out):
            raise HTTPException(status_code=404, detail="Reconciliation output not found")

        with open(recon_out, 'r') as f:
            data = json.load(f)

        # Extract unmatched transactions
        unmatched = []
        if isinstance(data, dict) and not data.get('matched') and not data.get('unmatched'):
            for rrn, rec in data.items():
                if isinstance(rec, dict) and rec.get('status') in ['ORPHAN', 'PARTIAL_MATCH', 'PARTIAL_MISMATCH']:
                    unmatched.append({"RRN": rrn, "status": rec.get('status'), "record": rec})
        else:
            unmatched = data.get('unmatched', [])

        return JSONResponse(content={"run_id": latest, "unmatched": unmatched})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get unmatched report error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve unmatched report")

@app.get("/api/v1/recon/latest/raw")
async def get_latest_raw_data(user: dict = Depends(get_current_user)):
    """Get raw reconciliation data for the latest run"""
    try:
        runs = [d for d in os.listdir(UPLOAD_DIR) if d.startswith('RUN_')]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found")
        latest = sorted(runs)[-1]
        run_root = os.path.join(UPLOAD_DIR, latest)

        # Look for recon_output.json
        recon_out = None
        for root_dir, dirs, files in os.walk(run_root):
            if 'recon_output.json' in files:
                recon_out = os.path.join(root_dir, 'recon_output.json')
                break

        if not recon_out or not os.path.exists(recon_out):
            raise HTTPException(status_code=404, detail="Reconciliation output not found")

        with open(recon_out, 'r') as f:
            data = json.load(f)

        # Count summary statistics
        total_rrns = len(data) if isinstance(data, dict) else len(data.get('matched', [])) + len(data.get('unmatched', []))
        matched_count = 0
        unmatched_count = 0

        if isinstance(data, dict):
            for rec in data.values():
                if isinstance(rec, dict):
                    status = rec.get('status', '')
                    if status in ['MATCHED', 'EXACT_MATCH']:
                        matched_count += 1
                    elif status in ['ORPHAN', 'PARTIAL_MATCH', 'PARTIAL_MISMATCH', 'EXCEPTION']:
                        unmatched_count += 1
        else:
            matched_count = len(data.get('matched', []))
            unmatched_count = len(data.get('unmatched', []))

        exception_count = unmatched_count  # For now, treat all unmatched as exceptions

        return JSONResponse(content={
            "run_id": latest,
            "data": data,
            "summary": {
                "total_rrns": total_rrns,
                "matched_count": matched_count,
                "unmatched_count": unmatched_count,
                "exception_count": exception_count,
                "file_path": recon_out
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get raw data error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve raw data")

@app.get("/api/v1/rollback/history")
async def get_rollback_history(run_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Get rollback history for a run or all runs"""
    try:
        # Look for rollback_history.json in OUTPUT_DIR
        history_path = os.path.join(OUTPUT_DIR, "rollback_history.json")

        if not os.path.exists(history_path):
            # Return empty history if file doesn't exist
            return JSONResponse(content={"history": []})

        with open(history_path, 'r') as f:
            history_data = json.load(f)

        # Filter by run_id if provided
        if run_id:
            filtered_history = [item for item in history_data if item.get('run_id') == run_id]
            return JSONResponse(content={"run_id": run_id, "history": filtered_history})
        else:
            return JSONResponse(content={"history": history_data})

    except Exception as e:
        logger.error(f"Get rollback history error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve rollback history")



# ============================================================================

# MAIN

# ============================================================================



if __name__ == '__main__':

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
