from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from datetime import datetime
from typing import Dict, Optional, List
from file_handler import FileHandler
from recon_engine import ReconciliationEngine
from rollback_manager import RollbackManager, RollbackLevel
from exception_handler import ExceptionHandler, ExceptionType, RecoveryStrategy
from gl_proofing_engine import GLJustificationEngine
from settlement_engine import SettlementEngine
from audit_trail import AuditTrail, AuditAction, AuditLevel
from config import RUN_ID_FORMAT, OUTPUT_DIR, UPLOAD_DIR
from logging_config import setup_logging, get_logger

# Initialize logging
setup_logging(log_level="INFO", enable_json=True)
logger = get_logger(__name__)

# Maximum file size for uploads (100 MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

app = FastAPI(
    title="NSTechX Bank Reconciliation API",
    description="Complete reconciliation system with integrated chatbot service",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"An unexpected error occurred: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred. Please try again later."},
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

file_handler = FileHandler()
recon_engine = ReconciliationEngine()
rollback_manager = RollbackManager(upload_dir=UPLOAD_DIR, output_dir=OUTPUT_DIR)
exception_handler = ExceptionHandler(upload_dir=UPLOAD_DIR, output_dir=OUTPUT_DIR)
gl_engine = GLJustificationEngine(output_dir=OUTPUT_DIR)
settlement_engine = SettlementEngine(output_dir=OUTPUT_DIR)
audit_trail = AuditTrail(output_dir=OUTPUT_DIR)

# ============================================================================
# CHATBOT INTEGRATION (EMBEDDED IN MAIN APP)
# ============================================================================

# Import chatbot modules
try:
    from chatbot_services import lookup
    from chatbot_services import nlp
    from chatbot_services import response_formatter
    CHATBOT_AVAILABLE = True
    logger.info("✅ Chatbot modules loaded successfully")
except ImportError as e:
    CHATBOT_AVAILABLE = False
    logger.warning(f"⚠️  Warning: Chatbot modules not available - {e}")

# ============================================================================
# ROOT & HEALTH ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "service": "NSTechX Bank Reconciliation API",
        "version": "1.0.0",
        "status": "running",
        "chatbot_available": CHATBOT_AVAILABLE,
        "endpoints": {
            "upload": "/api/v1/upload (POST)",
            "reconcile": "/api/v1/recon/run (POST)",
            "chatbot_by_rrn": "/api/v1/chatbot/{rrn} (GET)",
            "chatbot_by_txn": "/api/v1/chatbot?txn_id=X (GET)",
            "summary": "/api/v1/summary (GET)",
            "health": "/health (GET)",
            "docs": "/docs"
        }
    }

# ==================== EXCEPTION HANDLING ENDPOINTS (Phase 3 Task 3) ====================

@app.post("/api/v1/exception/sftp-connection")
async def handle_sftp_connection(
    run_id: str = Query(..., description="Run ID"),
    host: str = Query(..., description="SFTP host"),
    error: str = Query("", description="Error message")
):
    """Handle SFTP connection failure with retry logic"""
    recovery = exception_handler.handle_sftp_connection_failure(
        run_id=run_id,
        host=host,
        error_message=error
    )
    
    return {
        "status": "exception_logged",
        "run_id": run_id,
        "exception_type": "sftp_connection_failed",
        "recovery_strategy": recovery.value,
        "message": f"SFTP connection failure logged. Strategy: {recovery.value}"
    }

@app.post("/api/v1/exception/sftp-timeout")
async def handle_sftp_timeout(
    run_id: str = Query(..., description="Run ID"),
    filename: str = Query(..., description="Filename"),
    timeout_seconds: int = Query(30, description="Timeout in seconds")
):
    """Handle SFTP timeout during file transfer"""
    recovery = exception_handler.handle_sftp_timeout(
        run_id=run_id,
        filename=filename,
        timeout_seconds=timeout_seconds
    )
    
    return {
        "status": "timeout_handled",
        "run_id": run_id,
        "filename": filename,
        "recovery_strategy": recovery.value,
        "message": f"SFTP timeout handled. Strategy: {recovery.value}"
    }

@app.post("/api/v1/exception/duplicate-cycle")
async def handle_duplicate_cycle(
    run_id: str = Query(..., description="Run ID"),
    cycle_id: str = Query(..., description="Cycle ID (e.g., 1A)"),
    current_filename: str = Query(..., description="Current filename"),
    existing_filename: str = Query(..., description="Existing filename")
):
    """Handle duplicate cycle detection"""
    recovery = exception_handler.handle_duplicate_cycle(
        run_id=run_id,
        cycle_id=cycle_id,
        current_filename=current_filename,
        existing_filename=existing_filename
    )
    
    return {
        "status": "duplicate_detected",
        "run_id": run_id,
        "cycle_id": cycle_id,
        "existing_file": existing_filename,
        "conflicting_file": current_filename,
        "recovery_strategy": recovery.value,
        "message": f"Duplicate cycle detected and skipped. {existing_filename} will be used."
    }

@app.post("/api/v1/exception/network-timeout")
async def handle_network_timeout(
    run_id: str = Query(..., description="Run ID"),
    service: str = Query(..., description="Service name (DB, API, etc.)"),
    error: str = Query("", description="Error message")
):
    """Handle network timeout with retry logic"""
    recovery = exception_handler.handle_network_timeout(
        run_id=run_id,
        service=service,
        error_message=error
    )
    
    return {
        "status": "timeout_logged",
        "run_id": run_id,
        "service": service,
        "recovery_strategy": recovery.value,
        "message": f"Network timeout logged. Strategy: {recovery.value}"
    }

@app.post("/api/v1/exception/validation-error")
async def handle_validation_error(
    run_id: str = Query(..., description="Run ID"),
    filename: str = Query(..., description="Filename"),
    error_details: str = Query("{}", description="Error details JSON")
):
    """Handle file validation errors"""
    details = json.loads(error_details)
    recovery = exception_handler.handle_validation_error(
        run_id=run_id,
        filename=filename,
        error_details=details
    )
    
    return {
        "status": "validation_error_handled",
        "run_id": run_id,
        "filename": filename,
        "recovery_strategy": recovery.value,
        "message": f"Validation error logged. File will be skipped."
    }

@app.post("/api/v1/exception/insufficient-space")
async def handle_insufficient_space(
    run_id: str = Query(..., description="Run ID"),
    required_bytes: int = Query(..., description="Required space in bytes"),
    available_bytes: int = Query(..., description="Available space in bytes")
):
    """Handle insufficient disk space error"""
    recovery = exception_handler.handle_insufficient_disk_space(
        run_id=run_id,
        required_bytes=required_bytes,
        available_bytes=available_bytes
    )
    
    return {
        "status": "space_error_logged",
        "run_id": run_id,
        "required_gb": required_bytes / (1024**3),
        "available_gb": available_bytes / (1024**3),
        "recovery_strategy": recovery.value,
        "message": f"Insufficient disk space. Reconciliation aborted. Free up space and retry."
    }

@app.post("/api/v1/exception/database-error")
async def handle_database_error(
    run_id: str = Query(..., description="Run ID"),
    error: str = Query("", description="Error message")
):
    """Handle database errors with retry and rollback logic"""
    recovery = exception_handler.handle_database_error(
        run_id=run_id,
        error_message=error
    )
    
    return {
        "status": "database_error_logged",
        "run_id": run_id,
        "recovery_strategy": recovery.value,
        "message": f"Database error logged. Strategy: {recovery.value}"
    }

@app.get("/api/v1/exception/summary")
async def get_exception_summary(run_id: Optional[str] = Query(None, description="Optional run ID filter")):
    """Get exception summary and statistics"""
    summary = exception_handler.get_exception_summary(run_id)
    return {
        "status": "success",
        "data": summary
    }

@app.get("/api/v1/exception/run/{run_id}")
async def get_run_exceptions(run_id: str):
    """Get all exceptions for a specific run"""
    exceptions = exception_handler.get_run_exceptions(run_id)
    has_critical = exception_handler.check_run_has_critical_exceptions(run_id)
    duplicate_cycles = exception_handler.check_run_has_duplicate_cycles(run_id)
    
    return {
        "status": "success",
        "run_id": run_id,
        "total_exceptions": len(exceptions),
        "has_critical_exceptions": has_critical,
        "duplicate_cycles": duplicate_cycles,
        "exceptions": exceptions
    }

@app.post("/api/v1/exception/resolve/{exception_id}")
async def resolve_exception(exception_id: str):
    """Mark an exception as resolved"""
    exception_handler.resolve_exception(exception_id)
    
    return {
        "status": "success",
        "exception_id": exception_id,
        "message": "Exception marked as resolved"
    }

# ==================== GL JUSTIFICATION & PROOFING ENDPOINTS (Phase 3 Task 4) ====================

@app.post("/api/v1/gl/proofing/create")
async def create_gl_proofing_report(
    run_id: str = Query(..., description="Run ID"),
    report_date: str = Query(..., description="Report date (YYYY-MM-DD)"),
    gl_accounts: str = Query("[]", description="GL accounts JSON array"),
    variance_bridges: str = Query("[]", description="Variance bridges JSON array")
):
    """Create a GL proofing report with variance bridging"""
    gl_accounts_data = json.loads(gl_accounts)
    variance_bridges_data = json.loads(variance_bridges)
    
    report = gl_engine.create_proofing_report(
        run_id=run_id,
        report_date=report_date,
        gl_accounts_data=gl_accounts_data,
        variance_bridges_data=variance_bridges_data
    )
    
    return {
        "status": "success",
        "report_id": report.report_id,
        "run_id": run_id,
        "report_date": report_date,
        "summary": {
            "total_accounts": report.total_accounts,
            "reconciled_accounts": report.reconciled_accounts,
            "unreconciled_accounts": report.unreconciled_accounts,
            "total_variance": report.total_variance,
            "total_bridged": report.total_bridged,
            "bridging_coverage_percent": round(report.bridging_coverage, 2),
            "remaining_variance": report.remaining_variance,
            "fully_reconciled": report.fully_reconciled
        }
    }

@app.post("/api/v1/gl/proofing/bridge")
async def add_variance_bridge(
    run_id: str = Query(..., description="Run ID"),
    category: str = Query(..., description="Variance category (e.g., TIMING_DIFFERENCE, PENDING_CLEARANCES)"),
    description: str = Query(..., description="Bridge description"),
    amount: float = Query(..., description="Variance amount"),
    justification: str = Query(..., description="Justification for the variance"),
    transaction_date: str = Query(None, description="Transaction date (YYYY-MM-DD)"),
    report_date: str = Query(None, description="Report date (YYYY-MM-DD)")
):
    """Add a variance bridge to explain part of the variance"""
    bridge = gl_engine.add_variance_bridge(
        run_id=run_id,
        category=category,
        description=description,
        amount=amount,
        justification=justification,
        transaction_date=transaction_date,
        report_date=report_date
    )
    
    return {
        "status": "success",
        "bridge_id": bridge.bridge_id,
        "category": bridge.category.value,
        "amount": bridge.amount,
        "aging_days": bridge.aging_days,
        "priority": bridge.priority,
        "message": f"Variance bridge created: ₹{amount:,.2f} ({bridge.category.value})"
    }

@app.get("/api/v1/gl/proofing/report/{report_id}")
async def get_proofing_report(report_id: str):
    """Get a specific GL proofing report"""
    report = gl_engine.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    
    return {
        "status": "success",
        "report": report
    }

@app.get("/api/v1/gl/proofing/reports")
async def get_all_proofing_reports():
    """Get all GL proofing reports"""
    reports = gl_engine.get_all_reports()
    
    return {
        "status": "success",
        "total_reports": len(reports),
        "reports": reports
    }

@app.get("/api/v1/gl/proofing/unreconciled/{run_id}")
async def get_unreconciled_accounts(run_id: str):
    """Get unreconciled GL accounts for a run"""
    accounts = gl_engine.get_unreconciled_accounts(run_id)
    
    return {
        "status": "success",
        "run_id": run_id,
        "unreconciled_count": len(accounts),
        "accounts": [acc.to_dict() for acc in accounts]
    }

@app.get("/api/v1/gl/proofing/high-priority/{run_id}")
async def get_high_priority_bridges(run_id: str):
    """Get high and critical priority variance bridges"""
    bridges = gl_engine.get_high_priority_bridges(run_id)
    
    critical = [b for b in bridges if b.priority == "CRITICAL"]
    high = [b for b in bridges if b.priority == "HIGH"]
    
    return {
        "status": "success",
        "run_id": run_id,
        "critical_count": len(critical),
        "high_count": len(high),
        "total": len(bridges),
        "critical_bridges": [b.to_dict() for b in critical],
        "high_bridges": [b.to_dict() for b in high]
    }

@app.get("/api/v1/gl/proofing/aging/{run_id}")
async def get_aging_summary(run_id: str):
    """Get variance bridge aging summary"""
    aging = gl_engine.get_aging_summary(run_id)
    
    total = (
        len(aging.get("0_1_days", [])) +
        len(aging.get("1_3_days", [])) +
        len(aging.get("3_7_days", [])) +
        len(aging.get("7_plus_days", []))
    )
    
    return {
        "status": "success",
        "run_id": run_id,
        "total_bridges": total,
        "aging_summary": aging
    }

@app.post("/api/v1/gl/proofing/bridge/resolve/{bridge_id}")
async def resolve_variance_bridge(bridge_id: str, resolved_by: str = Query("System")):
    """Mark a variance bridge as resolved"""
    gl_engine.resolve_variance_bridge(bridge_id, resolved_by)
    
    return {
        "status": "success",
        "bridge_id": bridge_id,
        "message": f"Variance bridge resolved by {resolved_by}"
    }

# ==================== AUDIT TRAIL & LOGGING ENDPOINTS (Phase 3 Task 5) ====================

@app.get("/api/v1/audit/trail/{run_id}")
async def get_audit_trail(run_id: str):
    """Get complete audit trail for a run"""
    trail = audit_trail.get_run_audit_trail(run_id)
    
    return {
        "status": "success",
        "run_id": run_id,
        "total_entries": len(trail),
        "entries": trail
    }

@app.get("/api/v1/audit/user/{user_id}")
async def get_user_actions(user_id: str, limit: int = Query(100, description="Limit results")):
    """Get all actions performed by a specific user"""
    actions = audit_trail.get_user_actions(user_id, limit)
    
    return {
        "status": "success",
        "user_id": user_id,
        "total_actions": len(actions),
        "actions": actions
    }

@app.get("/api/v1/audit/summary")
async def get_audit_summary(run_id: Optional[str] = Query(None, description="Optional run ID filter")):
    """Get audit trail summary"""
    summary = audit_trail.get_audit_summary(run_id)
    
    return {
        "status": "success",
        "summary": summary
    }

@app.get("/api/v1/audit/date-range")
async def get_actions_by_date(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """Get audit entries within a date range"""
    entries = audit_trail.get_actions_by_date(start_date, end_date)
    
    return {
        "status": "success",
        "start_date": start_date,
        "end_date": end_date,
        "total_entries": len(entries),
        "entries": entries
    }

@app.post("/api/v1/audit/log-action")
async def log_custom_action(
    run_id: str = Query(..., description="Run ID"),
    action: str = Query(..., description="Action name"),
    user_id: Optional[str] = Query(None, description="User ID"),
    level: str = Query("INFO", description="Log level (INFO, WARNING, ERROR, CRITICAL)"),
    details: str = Query("{}", description="Details JSON")
):
    """Log a custom action to audit trail"""
    action_details = json.loads(details)
    level_enum = AuditLevel[level.upper()]
    
    entry = audit_trail.log_action(
        action=AuditAction.USER_ACTION,
        run_id=run_id,
        user_id=user_id,
        level=level_enum,
        details={
            "action_name": action,
            **action_details
        }
    )
    
    return {
        "status": "success",
        "audit_id": entry.audit_id,
        "message": f"Action logged: {action}"
    }

@app.get("/api/v1/audit/compliance/{run_id}")
async def generate_compliance_report(
    run_id: str,
    report_type: str = Query("full", description="Report type (full, critical, high_privilege)")
):
    """Generate compliance report for a run"""
    report = audit_trail.generate_compliance_report(run_id, report_type)
    
    return {
        "status": "success",
        "report": report
    }

@app.post("/api/v1/audit/event/recon")
async def log_recon_event(
    run_id: str = Query(..., description="Run ID"),
    event: str = Query(..., description="Event (started, completed, failed)"),
    user_id: Optional[str] = Query(None, description="User ID"),
    matched_count: int = Query(0, description="Matched transaction count"),
    unmatched_count: int = Query(0, description="Unmatched transaction count"),
    error: Optional[str] = Query(None, description="Error message if failed")
):
    """Log reconciliation lifecycle event"""
    entry = audit_trail.log_reconciliation_event(
        run_id=run_id,
        event=event,
        user_id=user_id,
        matched_count=matched_count,
        unmatched_count=unmatched_count,
        error=error
    )
    
    return {
        "status": "success",
        "audit_id": entry.audit_id,
        "message": f"Reconciliation {event} logged"
    }

@app.post("/api/v1/audit/event/rollback")
async def log_rollback_event(
    run_id: str = Query(..., description="Run ID"),
    rollback_level: str = Query(..., description="Rollback level"),
    user_id: Optional[str] = Query(None, description="User ID"),
    status: str = Query("completed", description="Status (completed, failed)")
):
    """Log rollback operation"""
    entry = audit_trail.log_rollback_operation(
        run_id=run_id,
        rollback_level=rollback_level,
        user_id=user_id,
        status=status
    )
    
    return {
        "status": "success",
        "audit_id": entry.audit_id,
        "message": f"Rollback {rollback_level} logged"
    }

@app.post("/api/v1/audit/event/force-match")
async def log_force_match_event(
    run_id: str = Query(..., description="Run ID"),
    rrn: str = Query(..., description="RRN"),
    source1: str = Query(..., description="Source 1"),
    source2: str = Query(..., description="Source 2"),
    user_id: Optional[str] = Query(None, description="User ID")
):
    """Log force match operation"""
    entry = audit_trail.log_force_match(
        run_id=run_id,
        rrn=rrn,
        source1=source1,
        source2=source2,
        user_id=user_id
    )
    
    return {
        "status": "success",
        "audit_id": entry.audit_id,
        "message": f"Force match for {rrn} logged"
    }

@app.post("/api/v1/audit/event/gl")
async def log_gl_event(
    run_id: str = Query(..., description="Run ID"),
    operation: str = Query(..., description="Operation type"),
    user_id: Optional[str] = Query(None, description="User ID"),
    details: str = Query("{}", description="Additional details JSON")
):
    """Log GL operation"""
    operation_details = json.loads(details)
    entry = audit_trail.log_gl_operation(
        run_id=run_id,
        operation=operation,
        user_id=user_id,
        details=operation_details
    )
    
    return {
        "status": "success",
        "audit_id": entry.audit_id,
        "message": f"GL {operation} logged"
    }

@app.get("/health")
async def health_check():
    """Main API health check"""
    return {
        "status": "healthy",
        "service": "NSTechX Reconciliation API",
        "chatbot_available": CHATBOT_AVAILABLE
    }

@app.post("/api/v1/upload")
async def upload_files(
    cbs_inward: UploadFile = File(...),
    cbs_outward: UploadFile = File(...),
    switch: UploadFile = File(...),
    npci_inward: UploadFile = File(None),
    npci_outward: UploadFile = File(None),
    ntsl: UploadFile = File(None),
    adjustment: UploadFile = File(None),
    cbs_balance: str = None,
    transaction_date: str = None
):
    """Upload files - CBS and Switch are required, NPCI files are optional"""
    try:
        # Get current run ID
        current_run_id = RUN_ID_FORMAT
        
        # Create the run folder first
        run_folder = os.path.join(UPLOAD_DIR, current_run_id)
        os.makedirs(run_folder, exist_ok=True)
        
        # Helper function to process and validate a single file
        async def process_file(file: UploadFile, file_name_key: str):
            if not file or not file.filename:
                return None, None
            
            # Check file size
            file.file.seek(0, 2)
            file_size = file.file.tell()
            await file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File size for {file.filename} exceeds the limit of {MAX_FILE_SIZE / (1024*1024)} MB."
                )
            
            content = await file.read()
            if not content:
                return None, None
                
            return file_name_key, content

        files_to_process = {
            "cbs_inward": cbs_inward,
            "cbs_outward": cbs_outward,
            "switch": switch,
            "npci_inward": npci_inward,
            "npci_outward": npci_outward,
            "ntsl": ntsl,
            "adjustment": adjustment,
        }

        files = {}
        uploaded_files = []

        for key, file in files_to_process.items():
            name, content = await process_file(file, key)
            if name:
                files[file.filename] = content
                uploaded_files.append(name)

        # Save files with original names
        saved_folder = file_handler.save_uploaded_files(files, current_run_id)
        
        # Save metadata including which files were uploaded
        metadata = {
            "cbs_balance": cbs_balance,
            "transaction_date": transaction_date,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "uploaded_files": uploaded_files
        }
        metadata_path = os.path.join(run_folder, "metadata.json")
        with open(metadata_path, 'w') as f:
            __import__('json').dump(metadata, f, indent=2)
        
        return {
            "status": "success",
            "message": "Files uploaded successfully",
            "run_id": current_run_id,
            "folder": saved_folder,
            "cbs_balance": cbs_balance,
            "transaction_date": transaction_date,
            "uploaded_files": uploaded_files,
            "next_step": "Call /api/v1/recon/run to start reconciliation"
        }
    except HTTPException as e:
        # Re-raise HTTP exceptions to return proper HTTP responses
        raise e
    except Exception as e:
        # For other exceptions, return a 400 bad request
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

@app.get("/api/v1/upload/metadata")
async def get_upload_metadata():
    """Get metadata of the latest upload including which files were uploaded"""
    try:
        if not os.path.exists(UPLOAD_DIR):
            raise HTTPException(status_code=404, detail="Upload directory not found")
        
        run_folders = [f for f in os.listdir(UPLOAD_DIR) if f.startswith("RUN_")]
        if not run_folders:
            raise HTTPException(status_code=404, detail="No uploaded files found")
        
        latest_run = max(run_folders)
        metadata_path = os.path.join(UPLOAD_DIR, latest_run, "metadata.json")
        
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Metadata not found")
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        return {
            "status": "success",
            "run_id": latest_run,
            "metadata": metadata,
            "uploaded_files": metadata.get("uploaded_files", [])
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/v1/recon/run")
async def run_reconciliation(direction: str = "INWARD"):
    """Trigger reconciliation process with comprehensive exception handling"""
    run_id = None
    try:
        # Log reconciliation start
        audit_trail.log_reconciliation_event(
            run_id="INITIALIZING",
            event="started",
            user_id="SYSTEM"
        )

        # Get latest run folder
        if not os.path.exists(UPLOAD_DIR):
            raise HTTPException(status_code=404, detail="Upload directory not found")

        run_folders = [f for f in os.listdir(UPLOAD_DIR) if f.startswith("RUN_")]
        if not run_folders:
            raise HTTPException(status_code=404, detail="No uploaded files found")

        latest_run = max(run_folders)
        run_id = latest_run
        run_folder = os.path.join(UPLOAD_DIR, latest_run)

        # Check if the run folder exists
        if not os.path.exists(run_folder):
            raise HTTPException(status_code=404, detail=f"Run folder does not exist: {run_folder}")

        # Phase 1: File Loading with Exception Handling
        try:
            dataframes = file_handler.load_files_for_recon(run_folder)
            if not dataframes:
                # Handle file loading failure
                recovery = exception_handler.handle_validation_error(
                    run_id=run_id,
                    filename="ALL_FILES",
                    error_details={"error": "No valid files found", "folder": run_folder}
                )
                audit_trail.log_exception(run_id, "FILE_LOADING_FAILED", "No valid files found in upload folder")
                raise HTTPException(
                    status_code=400,
                    detail=f"File loading failed. Recovery strategy: {recovery.value}. Check file formats and column headers."
                )
        except Exception as file_error:
            # Handle file processing errors
            recovery = exception_handler.handle_validation_error(
                run_id=run_id,
                filename="FILE_PROCESSING",
                error_details={"error": str(file_error), "phase": "file_loading"}
            )
            audit_trail.log_exception(run_id, "FILE_PROCESSING_ERROR", str(file_error))
            raise HTTPException(
                status_code=400,
                detail=f"File processing error: {str(file_error)}. Recovery strategy: {recovery.value}"
            )

        # Phase 2: Reconciliation Logic with Exception Handling
        try:
            results = recon_engine.reconcile(dataframes)
        except Exception as recon_error:
            # Handle reconciliation logic errors
            recovery = exception_handler.handle_database_error(
                run_id=run_id,
                error_message=f"Reconciliation logic failed: {str(recon_error)}"
            )
            audit_trail.log_exception(run_id, "RECONCILIATION_LOGIC_ERROR", str(recon_error))
            raise HTTPException(
                status_code=500,
                detail=f"Reconciliation logic failed: {str(recon_error)}. Recovery strategy: {recovery.value}"
            )

        # Phase 3: Output Generation with Exception Handling
        try:
            # Create output directory
            output_folder = os.path.join(OUTPUT_DIR, latest_run)
            os.makedirs(output_folder, exist_ok=True)

            # Generate outputs
            report_path = recon_engine.generate_report(results, output_folder)
            adjustments_path = recon_engine.generate_adjustments_csv(results, output_folder)

            # Save recon_output.json
            json_path = os.path.join(output_folder, "recon_output.json")
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2)

        except Exception as output_error:
            # Handle output generation errors
            recovery = exception_handler.handle_insufficient_disk_space(
                run_id=run_id,
                required_bytes=1024*1024,  # 1MB estimate
                available_bytes=0  # Will be checked by handler
            )
            audit_trail.log_exception(run_id, "OUTPUT_GENERATION_ERROR", str(output_error))
            raise HTTPException(
                status_code=500,
                detail=f"Output generation failed: {str(output_error)}. Recovery strategy: {recovery.value}"
            )

        # Phase 4: Chatbot Integration with Exception Handling
        chatbot_reload_success = False
        if CHATBOT_AVAILABLE:
            try:
                success = lookup.reload_data()
                chatbot_reload_success = success
                logger.info(f"✅ Chatbot data reloaded successfully: {success}")
            except Exception as chatbot_error:
                logger.warning(f"⚠️  Warning: Could not reload chatbot data: {chatbot_error}")
                # Log but don't fail the entire process
                audit_trail.log_exception(run_id, "CHATBOT_RELOAD_WARNING", str(chatbot_error))

        # Phase 5: Generate Accounting Vouchers and GL Entries
        try:
            settlement_result = settlement_engine.generate_vouchers_from_recon(results, latest_run)
            logger.info(f"Generated {settlement_result['vouchers_generated']} vouchers totaling ₹{settlement_result['total_amount']:,.2f}")
        except Exception as settlement_error:
            logger.warning(f"Settlement generation failed: {str(settlement_error)}")
            settlement_result = None

        # Phase 6: Generate GL Proofing Report
        try:
            # Create sample GL accounts data (in real implementation, this would come from GL system)
            gl_accounts_data = [
                {
                    "code": "100100",
                    "name": "Cash in Hand",
                    "opening_balance": 1000000.00,
                    "closing_balance": 1000000.00 + (settlement_result['total_amount'] if settlement_result else 0),
                    "book_balance": 1000000.00 + (settlement_result['total_amount'] if settlement_result else 0)
                },
                {
                    "code": "100200",
                    "name": "Bank Account",
                    "opening_balance": 5000000.00,
                    "closing_balance": 5000000.00 + (settlement_result['total_amount'] if settlement_result else 0),
                    "book_balance": 5000000.00 + (settlement_result['total_amount'] if settlement_result else 0)
                }
            ]

            # Create variance bridges for any unmatched transactions
            variance_bridges_data = []
            for rrn, record in results.items():
                if record.get('status') in ['PARTIAL_MATCH', 'ORPHAN']:
                    amount = 0.0
                    if record.get('cbs'):
                        amount = record['cbs'].get('amount', 0)
                    elif record.get('switch'):
                        amount = record['switch'].get('amount', 0)
                    elif record.get('npci'):
                        amount = record['npci'].get('amount', 0)

                    if amount > 0:
                        variance_bridges_data.append({
                            "category": "PENDING_CLEARANCES",
                            "description": f"Unmatched transaction RRN {rrn}",
                            "amount": amount,
                            "justification": f"Transaction {rrn} requires manual reconciliation",
                            "transaction_date": record.get('cbs', {}).get('date') or datetime.now().strftime("%Y-%m-%d")
                        })

            if variance_bridges_data:
                gl_report = gl_engine.create_proofing_report(
                    run_id=latest_run,
                    report_date=datetime.now().strftime("%Y-%m-%d"),
                    gl_accounts_data=gl_accounts_data,
                    variance_bridges_data=variance_bridges_data
                )
                logger.info(f"GL Proofing Report generated: {gl_report.report_id}")
            else:
                logger.info("No variances detected - GL accounts are reconciled")

        except Exception as gl_error:
            logger.warning(f"GL proofing report generation failed: {str(gl_error)}")

        # Log successful completion
        audit_trail.log_reconciliation_event(
            run_id=run_id,
            event="completed",
            user_id="SYSTEM",
            matched_count=len(recon_engine.matched_records),
            unmatched_count=len(recon_engine.unmatched_records)
        )

        return {
            "status": "completed",
            "run_id": latest_run,
            "output_folder": output_folder,
            "matched_count": len(recon_engine.matched_records),
            "unmatched_count": len(recon_engine.unmatched_records),
            "exception_count": len(recon_engine.exceptions),
            "partial_match_count": len(recon_engine.partial_match_records),
            "orphan_count": len(recon_engine.orphan_records),
            "settlement_generated": settlement_result is not None,
            "settlement_vouchers": settlement_result['vouchers_generated'] if settlement_result else 0,
            "settlement_amount": settlement_result['total_amount'] if settlement_result else 0,
            "next_step": "Chatbot is now ready to query transactions",
            "chatbot_available": CHATBOT_AVAILABLE,
            "chatbot_reloaded": chatbot_reload_success
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        error_message = f"Unexpected reconciliation error: {str(e)}"
        if run_id:
            recovery = exception_handler.handle_database_error(
                run_id=run_id,
                error_message=error_message
            )
            audit_trail.log_exception(run_id, "UNEXPECTED_RECONCILIATION_ERROR", error_message)
            audit_trail.log_reconciliation_event(
                run_id=run_id,
                event="failed",
                user_id="SYSTEM",
                error=error_message
            )
        else:
            logger.error(f"Reconciliation failed before run_id assignment: {error_message}")

        raise HTTPException(
            status_code=500,
            detail=f"Reconciliation failed: {error_message}. Please check logs and retry."
        )

# ============================================================================
# CHATBOT ENDPOINTS (Integrated)
# ============================================================================

@app.get("/api/v1/chatbot/{rrn}")
async def chatbot_by_rrn(rrn: str):
    """Get transaction by RRN (path parameter)"""
    if not CHATBOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chatbot service unavailable")
    
    if not nlp.validate_rrn(rrn):
        error_response = response_formatter.format_validation_error(
            "Invalid RRN format. RRN must be exactly 12 digits",
            details={"provided": rrn, "expected_format": "12 digits", "length": len(rrn)}
        )
        return JSONResponse(status_code=400, content=error_response)
    
    transaction = lookup.search_by_rrn(rrn)
    
    if transaction is None:
        run_id = lookup.CURRENT_RUN_ID or "UNKNOWN"
        error_response = response_formatter.format_not_found_response(rrn, "rrn", run_id)
        return JSONResponse(status_code=404, content=error_response)
    
    run_id = lookup.CURRENT_RUN_ID or "UNKNOWN"
    response = response_formatter.format_transaction_response(transaction, run_id)
    return JSONResponse(status_code=200, content=response)

@app.get("/api/v1/chatbot")
async def chatbot_lookup(rrn: Optional[str] = Query(None), txn_id: Optional[str] = Query(None)):
    """Get transaction by RRN or Transaction ID (query parameters)"""
    if not CHATBOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chatbot service unavailable")
    
    if not rrn and not txn_id:
        error_response = response_formatter.format_validation_error(
            "Missing required parameter. Provide either 'rrn' or 'txn_id'",
            details={
                "provided": {"rrn": rrn, "txn_id": txn_id},
                "required": "At least one of: rrn, txn_id"
            }
        )
        return JSONResponse(status_code=400, content=error_response)
    
    if rrn:
        if not nlp.validate_rrn(rrn):
            error_response = response_formatter.format_validation_error(
                "Invalid RRN format. RRN must be exactly 12 digits",
                details={"provided": rrn, "expected_format": "12 digits", "length": len(rrn)}
            )
            return JSONResponse(status_code=400, content=error_response)
        
        transaction = lookup.search_by_rrn(rrn)
        search_type = "rrn"
        identifier = rrn
    
    else:
        if not nlp.validate_txn_id(txn_id):
            error_response = response_formatter.format_validation_error(
                "Invalid transaction ID format. Must contain only digits",
                details={"provided": txn_id, "expected_format": "Digits only"}
            )
            return JSONResponse(status_code=400, content=error_response)
        
        txn_search = f"TXN{txn_id}" if not txn_id.startswith("TXN") else txn_id
        transaction = lookup.search_by_txn_id(txn_search)
        search_type = "txn_id"
        identifier = txn_id
    
    if transaction is None:
        run_id = lookup.CURRENT_RUN_ID or "UNKNOWN"
        error_response = response_formatter.format_not_found_response(identifier, search_type, run_id)
        return JSONResponse(status_code=404, content=error_response)
    
    run_id = lookup.CURRENT_RUN_ID or "UNKNOWN"
    response = response_formatter.format_transaction_response(transaction, run_id)
    return JSONResponse(status_code=200, content=response)

@app.get("/api/v1/chatbot/stats")
async def chatbot_stats():
    """Get chatbot statistics"""
    if not CHATBOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chatbot service unavailable")
    
    stats = lookup.get_statistics()
    return JSONResponse(status_code=200, content=stats)

@app.post("/api/v1/chatbot/reload")
async def chatbot_reload():
    """Reload chatbot data manually"""
    if not CHATBOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chatbot service unavailable")
    
    success = lookup.reload_data()
    if success:
        return {
            "status": "success",
            "message": f"Data reloaded from {lookup.CURRENT_RUN_ID}",
            "transaction_count": len(lookup.RECON_DATA)
        }
    else:
        return {
            "status": "no_change",
            "message": f"Already using latest run: {lookup.CURRENT_RUN_ID}",
            "transaction_count": len(lookup.RECON_DATA)
        }

# ============================================================================
# RECONCILIATION ENDPOINTS
# ============================================================================

@app.get("/api/v1/recon/latest/report")
async def get_latest_report():
    """Get latest reconciliation report"""
    if not os.path.exists(OUTPUT_DIR):
        raise HTTPException(status_code=404, detail="Output directory not found")
    
    run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_") and not f.endswith(".lock")]
    if not run_folders:
        raise HTTPException(status_code=404, detail="No reconciliation runs found")
    
    latest_run = max(run_folders)
    report_path = os.path.join(OUTPUT_DIR, latest_run, "report.txt")
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return PlainTextResponse(open(report_path).read())

@app.get("/api/v1/recon/latest/adjustments")
async def get_latest_adjustments():
    """Get latest adjustments CSV"""
    if not os.path.exists(OUTPUT_DIR):
        raise HTTPException(status_code=404, detail="Output directory not found")
    
    run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_") and not f.endswith(".lock")]
    if not run_folders:
        raise HTTPException(status_code=404, detail="No reconciliation runs found")
    
    latest_run = max(run_folders)
    csv_path = os.path.join(OUTPUT_DIR, latest_run, "adjustments.csv")
    
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Adjustments CSV not found")
    
    return FileResponse(csv_path, media_type="text/csv", filename="adjustments.csv")

@app.get("/api/v1/recon/latest/raw")
async def get_latest_raw():
    """Get latest raw reconciliation output for chatbot"""
    if not os.path.exists(OUTPUT_DIR):
        raise HTTPException(status_code=404, detail="Output directory not found")
    
    run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_") and not f.endswith(".lock")]
    if not run_folders:
        raise HTTPException(status_code=404, detail="No reconciliation runs found")
    
    latest_run = max(run_folders)
    json_path = os.path.join(OUTPUT_DIR, latest_run, "recon_output.json")
    
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="Reconciliation JSON not found")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    return {
        "run_id": latest_run,
        "data": data,
        "summary": {
            "total_rrns": len(data),
            "matched_count": len([k for k, v in data.items() if v['status'] == 'MATCHED']),
            "unmatched_count": len([k for k, v in data.items() if v['status'] in ['PARTIAL_MATCH', 'ORPHAN']]),
            "exception_count": len([k for k, v in data.items() if v['status'] == 'MISMATCH']),
            "file_path": json_path
        }
    }

@app.post("/api/v1/force-match")
async def force_match_rrn(rrn: str, source1: str, source2: str, action: str = "match", lhs_column: str = None, rhs_column: str = None):
    """Force match two RRNs from different systems"""
    # Get latest reconciliation data
    run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_")]
    if not run_folders:
        raise HTTPException(status_code=404, detail="No reconciliation runs found")
    
    latest_run = max(run_folders)
    json_path = os.path.join(OUTPUT_DIR, latest_run, "recon_output.json")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Update the RRN status to force matched
    if rrn in data:
        data[rrn]['status'] = 'FORCE_MATCHED'
        # If specific columns are provided, copy only those fields
        if lhs_column and rhs_column:
            lhs_val = data[rrn].get(source1, {}).get(lhs_column)
            # ensure nested dicts exist
            if source2 not in data[rrn] or not isinstance(data[rrn].get(source2), dict):
                data[rrn][source2] = {}
            data[rrn][source2][rhs_column] = lhs_val
        else:
            # Fallback: copy entire object from source1 to source2 for common sources
            if source1 == 'cbs' and source2 in ['switch', 'npci']:
                data[rrn][source2] = data[rrn]['cbs']
            elif source2 == 'cbs' and source1 in ['switch', 'npci']:
                data[rrn][source1] = data[rrn]['cbs']
            elif source1 == 'switch' and source2 == 'npci':
                data[rrn]['npci'] = data[rrn]['switch']
    
    # Save updated data
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    return {
        "status": "success",
        "message": f"RRN {rrn} force matched between {source1} and {source2}",
        "action": action,
        "rrn": rrn
    }

@app.post("/api/v1/auto-match/parameters")
async def set_auto_match_parameters(
    amount_tolerance: float = 0.0,
    date_tolerance_days: int = 0,
    enable_auto_match: bool = True
):
    """Set auto-match parameters"""
    return {
        "status": "success",
        "parameters": {
            "amount_tolerance": amount_tolerance,
            "date_tolerance_days": date_tolerance_days,
            "enable_auto_match": enable_auto_match
        }
    }

@app.get("/api/v1/reports/{report_type}")
async def get_report(report_type: str):
    """Generate different types of reports"""
    run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_")]
    if not run_folders:
        raise HTTPException(status_code=404, detail="No reconciliation runs found")
    
    latest_run = max(run_folders)
    
    if report_type == "matched":
        # Generate matched transactions report
        json_path = os.path.join(OUTPUT_DIR, latest_run, "recon_output.json")
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        matched_data = {k: v for k, v in data.items() if v['status'] == 'MATCHED'}
        return {"report_type": "matched", "data": matched_data, "count": len(matched_data)}
    
    elif report_type == "unmatched":
        # Generate unmatched transactions report
        json_path = os.path.join(OUTPUT_DIR, latest_run, "recon_output.json")
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        unmatched_data = {k: v for k, v in data.items() if v['status'] in ['PARTIAL_MATCH', 'ORPHAN']}
        return {"report_type": "unmatched", "data": unmatched_data, "count": len(unmatched_data)}
    
    elif report_type == "ttum":
        # Generate TTUM report
        return {"report_type": "ttum", "message": "TTUM report generated", "run_id": latest_run}
    
    elif report_type == "summary":
        # Generate summary report
        json_path = os.path.join(OUTPUT_DIR, latest_run, "recon_output.json")
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        matched = len([k for k, v in data.items() if v['status'] == 'MATCHED'])
        partial_match = len([k for k, v in data.items() if v['status'] == 'PARTIAL_MATCH'])
        orphan = len([k for k, v in data.items() if v['status'] == 'ORPHAN'])
        mismatch = len([k for k, v in data.items() if v['status'] == 'MISMATCH'])
        
        return {
            "report_type": "summary",
            "data": {
                "total_transactions": len(data),
                "matched": matched,
                "partial_match": partial_match,
                "orphan": orphan,
                "mismatch": mismatch,
                "unmatched": partial_match + orphan
            }
        }
    
    else:
        raise HTTPException(status_code=404, detail=f"Report type {report_type} not supported")

@app.post("/api/v1/rollback")
async def rollback_reconciliation(run_id: str = None):
    """Rollback reconciliation process"""
    if not run_id:
        # Get latest run if no specific run_id provided
        run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_")]
        if not run_folders:
            raise HTTPException(status_code=404, detail="No reconciliation runs found")
        run_id = max(run_folders)
    
    # Delete the output folder for this run
    output_path = os.path.join(OUTPUT_DIR, run_id)
    if os.path.exists(output_path):
        import shutil
        import stat
        # Windows permission fix
        def handle_remove_readonly(func, path, exc):
            if os.path.exists(path):
                os.chmod(path, stat.S_IWRITE)
                func(path)
        
        shutil.rmtree(output_path, onerror=handle_remove_readonly)
    
    return {
        "status": "success",
        "message": f"Reconciliation run {run_id} rolled back successfully"
    }

@app.get("/api/v1/summary")
async def get_reconciliation_summary():
    """Get reconciliation summary for dashboard"""
    run_folders = sorted([f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_") and not f.endswith(".lock")], reverse=True)
    
    latest_run = None
    data = None
    
    for run_folder in run_folders:
        json_path = os.path.join(OUTPUT_DIR, run_folder, "recon_output.json")
        if os.path.exists(json_path):
            latest_run = run_folder
            with open(json_path, 'r') as f:
                data = json.load(f)
            break
            
    if not latest_run or data is None:
        return {
            "total_transactions": 0,
            "matched": 0,
            "unmatched": 0,
            "adjustments": 0,
            "status": "no_data"
        }
    
    matched = len([k for k, v in data.items() if isinstance(v, dict) and v.get('status') == 'MATCHED'])
    unmatched = len([k for k, v in data.items() if isinstance(v, dict) and v.get('status') in ['PARTIAL_MATCH', 'ORPHAN']])
    
    return {
        "total_transactions": len(data),
        "matched": matched,
        "unmatched": unmatched,
        "adjustments": unmatched,
        "status": "completed",
        "run_id": latest_run
    }

@app.get("/api/v1/summary/historical")
async def get_historical_summary():
    """Get historical summary data for charts"""
    if not os.path.exists(OUTPUT_DIR):
        return []

    run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_")]
    if not run_folders:
        return []

    # Sort by date (newest first) and take last 6 runs
    run_folders.sort(reverse=True)
    recent_runs = run_folders[:6]

    historical_data = []
    for run_folder in recent_runs:
        json_path = os.path.join(OUTPUT_DIR, run_folder, "recon_output.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)

                matched = len([k for k, v in data.items() if isinstance(v, dict) and v.get('status') == 'MATCHED'])
                unmatched = len([k for k, v in data.items() if isinstance(v, dict) and v.get('status') in ['PARTIAL_MATCH', 'ORPHAN']])

                # Extract date from run folder name (RUN_YYYYMMDD_HHMMSS)
                date_str = run_folder.replace("RUN_", "").split("_")[0]
                month_year = f"{date_str[4:6]}-{date_str[2:4]}"  # MM-YY format

                historical_data.append({
                    "month": month_year,
                    "allTxns": len(data),
                    "reconciled": matched
                })
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not process {json_path} for historical summary: {e}")
                continue

    # Sort by month
    historical_data.sort(key=lambda x: x["month"])
    return historical_data

# ============================================================================
# ROLLBACK ENDPOINTS (PHASE 3)
# ============================================================================

@app.post("/api/v1/rollback/ingestion")
async def ingestion_rollback(run_id: str, filename: str, error: str):
    """
    Rollback specific file that failed validation during upload
    Removes only the failed file, preserves other uploaded files

    Args:
        run_id: Current run identifier
        filename: Name of the file that failed validation
        error: Description of the validation error
    """
    # Log the rollback attempt
    audit_trail.log_rollback_operation(run_id, "ingestion", "SYSTEM", "started")

    can_roll, msg = rollback_manager.can_rollback(run_id, RollbackLevel.INGESTION)
    if not can_roll:
        audit_trail.log_rollback_operation(run_id, "ingestion", "SYSTEM", "failed", details={"error": msg})
        raise HTTPException(status_code=400, detail=msg)

    result = rollback_manager.ingestion_rollback(run_id, filename, error)

    # Log successful rollback
    audit_trail.log_rollback_operation(run_id, "ingestion", "SYSTEM", "completed")

    return result

@app.post("/api/v1/rollback/mid-recon")
async def mid_recon_rollback(run_id: str, error: str,
                            affected_transactions: Optional[List[str]] = Query(None)):
    """
    Rollback uncommitted transactions during reconciliation
    Triggered by critical errors (DB disconnection, crashes, etc.)

    Args:
        run_id: Current run identifier
        error: Description of the error
        affected_transactions: List of transaction IDs to rollback
    """
    # Log the rollback attempt
    audit_trail.log_rollback_operation(run_id, "mid_recon", "SYSTEM", "started")

    can_roll, msg = rollback_manager.can_rollback(run_id, RollbackLevel.MID_RECON)
    if not can_roll:
        audit_trail.log_rollback_operation(run_id, "mid_recon", "SYSTEM", "failed", details={"error": msg})
        raise HTTPException(status_code=400, detail=msg)

    result = rollback_manager.mid_recon_rollback(run_id, error, affected_transactions)

    # Log successful rollback
    audit_trail.log_rollback_operation(run_id, "mid_recon", "SYSTEM", "completed")

    return result

@app.post("/api/v1/rollback/cycle-wise")
async def cycle_wise_rollback(run_id: str, cycle_id: str):
    """
    Rollback specific NPCI cycle for re-processing
    Does not affect other cycles or previously matched transactions
    NPCI cycles: 1A, 1B, 1C, 2A, 2B, 2C, 3A, 3B, 3C, 4

    Args:
        run_id: Current run identifier
        cycle_id: NPCI cycle to rollback (e.g., '1C', '3B')
    """
    # Validate cycle ID format
    valid_cycles = ['1A', '1B', '1C', '2A', '2B', '2C', '3A', '3B', '3C', '4']
    if cycle_id not in valid_cycles:
        audit_trail.log_rollback_operation(run_id, "cycle_wise", "SYSTEM", "failed",
                                             details={"error": f"Invalid cycle ID: {cycle_id}"})
        raise HTTPException(status_code=400, detail=f"Invalid cycle ID '{cycle_id}'. Must be one of {valid_cycles}")

    # Log the rollback attempt
    audit_trail.log_rollback_operation(run_id, "cycle_wise", "SYSTEM", "started",
                                         details={"cycle_id": cycle_id})

    can_roll, msg = rollback_manager.can_rollback(run_id, RollbackLevel.CYCLE_WISE)
    if not can_roll:
        audit_trail.log_rollback_operation(run_id, "cycle_wise", "SYSTEM", "failed",
                                             details={"error": msg, "cycle_id": cycle_id})
        raise HTTPException(status_code=400, detail=msg)

    result = rollback_manager.cycle_wise_rollback(run_id, cycle_id)

    # Log successful rollback
    audit_trail.log_rollback_operation(run_id, "cycle_wise", "SYSTEM", "completed",
                                         details={"cycle_id": cycle_id, "transactions_restored": result.get("transactions_restored", 0)})

    return result

@app.post("/api/v1/rollback/whole-process")
async def whole_process_rollback(run_id: str, reason: str):
    """
    Complete rollback of the entire reconciliation process
    Resets all matched transactions, vouchers, and processed data to initial state

    Args:
        run_id: Current run identifier
        reason: Reason for rollback (e.g., 'Complete process reset')
    """
    # Log the rollback attempt
    audit_trail.log_rollback_operation(run_id, "whole_process", "SYSTEM", "started")

    can_roll, msg = rollback_manager.can_rollback(run_id, RollbackLevel.WHOLE_PROCESS)
    if not can_roll:
        audit_trail.log_rollback_operation(run_id, "whole_process", "SYSTEM", "failed", details={"error": msg})
        raise HTTPException(status_code=400, detail=msg)

    result = rollback_manager.whole_process_rollback(run_id, reason, confirmation_required=False)

    # Log successful rollback
    audit_trail.log_rollback_operation(run_id, "whole_process", "SYSTEM", "completed")

    return result

@app.post("/api/v1/rollback/accounting")
async def accounting_rollback(run_id: str, reason: str,
                             voucher_ids: Optional[List[str]] = Query(None)):
    """
    Rollback voucher generation when CBS upload fails
    Resets status from 'settled/voucher generated' to 'matched/pending'

    Args:
        run_id: Current run identifier
        reason: Reason for rollback (e.g., 'CBS upload failure')
        voucher_ids: List of voucher IDs to rollback
    """
    # Log the rollback attempt
    audit_trail.log_rollback_operation(run_id, "accounting", "SYSTEM", "started")

    can_roll, msg = rollback_manager.can_rollback(run_id, RollbackLevel.ACCOUNTING)
    if not can_roll:
        audit_trail.log_rollback_operation(run_id, "accounting", "SYSTEM", "failed", details={"error": msg})
        raise HTTPException(status_code=400, detail=msg)

    result = rollback_manager.accounting_rollback(run_id, reason, voucher_ids)

    # Log successful rollback
    audit_trail.log_rollback_operation(run_id, "accounting", "SYSTEM", "completed")

    return result

@app.get("/api/v1/rollback/history")
async def get_rollback_history(run_id: Optional[str] = Query(None)):
    """
    Get rollback history, optionally filtered by run_id

    Args:
        run_id: Optional - Filter history by specific run
    """
    history = rollback_manager.get_rollback_history(run_id)

    # Log the history access
    audit_trail.log_action(
        action=AuditAction.USER_ACTION,
        run_id=run_id or "ALL_RUNS",
        user_id="SYSTEM",
        details={
            "action": "rollback_history_accessed",
            "filter_run_id": run_id,
            "returned_count": len(history)
        }
    )

    return {
        "status": "success",
        "count": len(history),
        "history": history
    }