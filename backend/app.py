from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from typing import Dict, Optional
from file_handler import FileHandler
from recon_engine import ReconciliationEngine
from config import RUN_ID_FORMAT, OUTPUT_DIR, UPLOAD_DIR

app = FastAPI(
    title="NSTechX Bank Reconciliation API",
    description="Complete reconciliation system with integrated chatbot service",
    version="1.0.0"
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

# ============================================================================
# CHATBOT INTEGRATION (EMBEDDED IN MAIN APP)
# ============================================================================

# Import chatbot modules
try:
    from chatbot_services import lookup
    from chatbot_services import nlp
    from chatbot_services import response_formatter
    CHATBOT_AVAILABLE = True
    print("✅ Chatbot modules loaded successfully")
except ImportError as e:
    CHATBOT_AVAILABLE = False
    print(f"⚠️  Warning: Chatbot modules not available - {e}")

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
    npci_inward: UploadFile = File(...),
    npci_outward: UploadFile = File(...),
    ntsl: UploadFile = File(...),
    adjustment: UploadFile = File(...),
    cbs_balance: str = None,
    transaction_date: str = None
):
    """Upload all 7 required files"""
    try:
        # Get current run ID
        current_run_id = RUN_ID_FORMAT
        
        # Create the run folder first
        run_folder = os.path.join(UPLOAD_DIR, current_run_id)
        os.makedirs(run_folder, exist_ok=True)
        
        # Collect all files with their original names
        files = {
            cbs_inward.filename: await cbs_inward.read(),
            cbs_outward.filename: await cbs_outward.read(),
            switch.filename: await switch.read(),
            npci_inward.filename: await npci_inward.read(),
            npci_outward.filename: await npci_outward.read(),
            ntsl.filename: await ntsl.read(),
            adjustment.filename: await adjustment.read()
        }
        
        # Save files with original names
        saved_folder = file_handler.save_uploaded_files(files, current_run_id)
        
        # Save metadata
        metadata = {
            "cbs_balance": cbs_balance,
            "transaction_date": transaction_date,
            "timestamp": __import__('datetime').datetime.now().isoformat()
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
            "next_step": "Call /api/v1/recon/run to start reconciliation"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

@app.post("/api/v1/recon/run")
async def run_reconciliation(direction: str = "INWARD"):
    """Trigger reconciliation process"""
    try:
        # Get latest run folder
        if not os.path.exists(UPLOAD_DIR):
            raise HTTPException(status_code=404, detail="Upload directory not found")
        
        run_folders = [f for f in os.listdir(UPLOAD_DIR) if f.startswith("RUN_")]
        if not run_folders:
            raise HTTPException(status_code=404, detail="No uploaded files found")
        
        latest_run = max(run_folders)
        run_folder = os.path.join(UPLOAD_DIR, latest_run)
        
        # Check if the run folder exists
        if not os.path.exists(run_folder):
            raise HTTPException(status_code=404, detail=f"Run folder does not exist: {run_folder}")
        
        # Load files for reconciliation
        dataframes = file_handler.load_files_for_recon(run_folder)
        
        if not dataframes:
            raise HTTPException(status_code=400, detail="No files found in upload folder. Check file formats and column headers.")
        
        # Run reconciliation
        results = recon_engine.reconcile(dataframes)
        
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
        
        # ✅ Reload chatbot data after reconciliation completes
        if CHATBOT_AVAILABLE:
            try:
                success = lookup.reload_data()
                print(f"✅ Chatbot data reloaded successfully: {success}")
            except Exception as e:
                print(f"⚠️  Warning: Could not reload chatbot data: {e}")
        
        return {
            "status": "completed",
            "run_id": latest_run,
            "output_folder": output_folder,
            "matched_count": len(recon_engine.matched_records),
            "unmatched_count": len(recon_engine.unmatched_records),
            "exception_count": len(recon_engine.exceptions),
            "partial_match_count": len(recon_engine.partial_match_records),
            "orphan_count": len(recon_engine.orphan_records),
            "next_step": "Chatbot is now ready to query transactions",
            "chatbot_available": CHATBOT_AVAILABLE
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconciliation failed: {str(e)}")
        
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
        
        # Trigger chatbot data reload via API
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chatbot_services'))
            from lookup import reload_data
            reload_data()
            print(f"✅ Chatbot data reloaded with run {latest_run}")
        except Exception as e:
            print(f"⚠️  Warning: Could not reload chatbot data: {e}")
        
        return {
            "status": "completed",
            "run_id": latest_run,
            "output_folder": output_folder,
            "matched_count": len(recon_engine.matched_records),
            "unmatched_count": len(recon_engine.unmatched_records),
            "exception_count": len(recon_engine.exceptions),
            "partial_match_count": len(recon_engine.partial_match_records),
            "orphan_count": len(recon_engine.orphan_records)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconciliation failed: {str(e)}")

# ============================================================================
# CHATBOT ENDPOINTS (Integrated)
# ============================================================================

@app.get("/api/v1/chatbot/{rrn}")
async def chatbot_by_rrn(rrn: str):
    """Get transaction by RRN (path parameter)"""
    if not CHATBOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chatbot service unavailable")
    
    try:
        # Validate RRN format
        if not nlp.validate_rrn(rrn):
            error_response = response_formatter.format_validation_error(
                "Invalid RRN format. RRN must be exactly 12 digits",
                details={"provided": rrn, "expected_format": "12 digits", "length": len(rrn)}
            )
            return JSONResponse(status_code=400, content=error_response)
        
        # Search by RRN
        transaction = lookup.search_by_rrn(rrn)
        
        # Handle not found
        if transaction is None:
            run_id = lookup.CURRENT_RUN_ID or "UNKNOWN"
            error_response = response_formatter.format_not_found_response(rrn, "rrn", run_id)
            return JSONResponse(status_code=404, content=error_response)
        
        # Return successful response
        run_id = lookup.CURRENT_RUN_ID or "UNKNOWN"
        response = response_formatter.format_transaction_response(transaction, run_id)
        return JSONResponse(status_code=200, content=response)
    
    except Exception as e:
        error_response = response_formatter.format_error_response(e, context="chatbot_by_rrn")
        return JSONResponse(status_code=500, content=error_response)

@app.get("/api/v1/chatbot")
async def chatbot_lookup(rrn: Optional[str] = Query(None), txn_id: Optional[str] = Query(None)):
    """Get transaction by RRN or Transaction ID (query parameters)"""
    if not CHATBOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chatbot service unavailable")
    
    try:
        # Validate input
        if not rrn and not txn_id:
            error_response = response_formatter.format_validation_error(
                "Missing required parameter. Provide either 'rrn' or 'txn_id'",
                details={
                    "provided": {"rrn": rrn, "txn_id": txn_id},
                    "required": "At least one of: rrn, txn_id"
                }
            )
            return JSONResponse(status_code=400, content=error_response)
        
        # Search by RRN
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
        
        # Search by TXN_ID
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
        
        # Handle not found
        if transaction is None:
            run_id = lookup.CURRENT_RUN_ID or "UNKNOWN"
            error_response = response_formatter.format_not_found_response(identifier, search_type, run_id)
            return JSONResponse(status_code=404, content=error_response)
        
        # Return successful response
        run_id = lookup.CURRENT_RUN_ID or "UNKNOWN"
        response = response_formatter.format_transaction_response(transaction, run_id)
        return JSONResponse(status_code=200, content=response)
    
    except Exception as e:
        error_response = response_formatter.format_error_response(e, context="chatbot_lookup")
        return JSONResponse(status_code=500, content=error_response)

@app.get("/api/v1/chatbot/stats")
async def chatbot_stats():
    """Get chatbot statistics"""
    if not CHATBOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chatbot service unavailable")
    
    try:
        stats = lookup.get_statistics()
        return JSONResponse(status_code=200, content=stats)
    except Exception as e:
        error_response = response_formatter.format_error_response(e, context="chatbot_stats")
        return JSONResponse(status_code=500, content=error_response)

@app.post("/api/v1/chatbot/reload")
async def chatbot_reload():
    """Reload chatbot data manually"""
    if not CHATBOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chatbot service unavailable")
    
    try:
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
    except Exception as e:
        error_response = response_formatter.format_error_response(e, context="chatbot_reload")
        return JSONResponse(status_code=500, content=error_response)

# ============================================================================
# RECONCILIATION ENDPOINTS
# ============================================================================

@app.get("/api/v1/recon/latest/report")
async def get_latest_report():
    """Get latest reconciliation report"""
    try:
        if not os.path.exists(OUTPUT_DIR):
            raise HTTPException(status_code=404, detail="Output directory not found")
        
        run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_")]
        if not run_folders:
            raise HTTPException(status_code=404, detail="No reconciliation runs found")
        
        latest_run = max(run_folders)
        report_path = os.path.join(OUTPUT_DIR, latest_run, "report.txt")
        
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report file not found")
        
        return PlainTextResponse(open(report_path).read())
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/v1/recon/latest/adjustments")
async def get_latest_adjustments():
    """Get latest adjustments CSV"""
    try:
        if not os.path.exists(OUTPUT_DIR):
            raise HTTPException(status_code=404, detail="Output directory not found")
        
        run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_")]
        if not run_folders:
            raise HTTPException(status_code=404, detail="No reconciliation runs found")
        
        latest_run = max(run_folders)
        csv_path = os.path.join(OUTPUT_DIR, latest_run, "adjustments.csv")
        
        if not os.path.exists(csv_path):
            raise HTTPException(status_code=404, detail="Adjustments CSV not found")
        
        return FileResponse(csv_path, media_type="text/csv", filename="adjustments.csv")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/v1/recon/latest/raw")
async def get_latest_raw():
    """Get latest raw reconciliation output for chatbot"""
    try:
        if not os.path.exists(OUTPUT_DIR):
            raise HTTPException(status_code=404, detail="Output directory not found")
        
        run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_")]
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
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# NEW: Force Match API
@app.post("/api/v1/force-match")
async def force_match_rrn(rrn: str, source1: str, source2: str, action: str = "match"):
    """Force match two RRNs from different systems"""
    try:
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
            # Update amounts to match
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NEW: Auto-match parameters API
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

# NEW: Reports API
@app.get("/api/v1/reports/{report_type}")
async def get_report(report_type: str):
    """Generate different types of reports"""
    try:
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
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NEW: Rollback API (FIXED)
@app.post("/api/v1/rollback")
async def rollback_reconciliation(run_id: str = None):
    """Rollback reconciliation process"""
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")

# NEW: Summary API
@app.get("/api/v1/summary")
async def get_reconciliation_summary():
    """Get reconciliation summary for dashboard"""
    try:
        run_folders = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("RUN_")]
        if not run_folders:
            return {
                "total_transactions": 0,
                "matched": 0,
                "unmatched": 0,
                "adjustments": 0,
                "status": "no_data"
            }
        
        latest_run = max(run_folders)
        json_path = os.path.join(OUTPUT_DIR, latest_run, "recon_output.json")
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        matched = len([k for k, v in data.items() if v['status'] == 'MATCHED'])
        unmatched = len([k for k, v in data.items() if v['status'] in ['PARTIAL_MATCH', 'ORPHAN']])
        
        return {
            "total_transactions": len(data),
            "matched": matched,
            "unmatched": unmatched,
            "adjustments": unmatched,
            "status": "completed",
            "run_id": latest_run
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NEW: Historical data for charts
@app.get("/api/v1/summary/historical")
async def get_historical_summary():
    """Get historical summary data for charts"""
    try:
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
                with open(json_path, 'r') as f:
                    data = json.load(f)

                matched = len([k for k, v in data.items() if v['status'] == 'MATCHED'])
                unmatched = len([k for k, v in data.items() if v['status'] in ['PARTIAL_MATCH', 'ORPHAN']])

                # Extract date from run folder name (RUN_YYYYMMDD_HHMMSS)
                date_str = run_folder.replace("RUN_", "").split("_")[0]
                month_year = f"{date_str[4:6]}-{date_str[2:4]}"  # MM-YY format

                historical_data.append({
                    "month": month_year,
                    "allTxns": len(data),
                    "reconciled": matched
                })

        # Sort by month
        historical_data.sort(key=lambda x: x["month"])
        return historical_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "NSTechX Reconciliation API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)