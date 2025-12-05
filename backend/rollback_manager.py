"""
Rollback Manager - Handles granular rollback operations at multiple levels
Supports: Ingestion, Mid-Recon, Cycle-Wise, and Accounting Rollback
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
from logging_config import get_logger

logger = get_logger(__name__)


class RollbackLevel(Enum):
    """Rollback operation levels"""
    INGESTION = "ingestion"          # File validation failure
    MID_RECON = "mid_recon"          # During reconciliation
    CYCLE_WISE = "cycle_wise"        # Specific NPCI cycle
    ACCOUNTING = "accounting"        # Voucher generation failure


class RollbackStatus(Enum):
    """Status of rollback operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class RollbackManager:
    """Manages granular rollback operations"""
    
    def __init__(self, upload_dir: str = "./data/uploads", output_dir: str = "./data/output"):
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        self.rollback_history_file = os.path.join(output_dir, "rollback_history.json")
        self._ensure_history_file()
    
    def _ensure_history_file(self):
        """Ensure rollback history file exists"""
        os.makedirs(os.path.dirname(self.rollback_history_file), exist_ok=True)
        if not os.path.exists(self.rollback_history_file):
            with open(self.rollback_history_file, 'w') as f:
                json.dump([], f)
    
    def _log_rollback(self, rollback_level: RollbackLevel, run_id: str, details: Dict) -> str:
        """Log rollback operation with timestamp and details"""
        with open(self.rollback_history_file, 'r') as f:
            history = json.load(f)
        
        rollback_id = f"ROLLBACK_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        record = {
            "rollback_id": rollback_id,
            "level": rollback_level.value,
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "status": RollbackStatus.PENDING.value,
            "details": details
        }
        
        history.append(record)
        with open(self.rollback_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        return rollback_id
    
    def _update_rollback_status(self, rollback_id: str, status: RollbackStatus):
        """Update rollback operation status"""
        with open(self.rollback_history_file, 'r') as f:
            history = json.load(f)
        
        for record in history:
            if record["rollback_id"] == rollback_id:
                record["status"] = status.value
                record["updated_at"] = datetime.now().isoformat()
                break
        
        with open(self.rollback_history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    # ========================================================================
    # STAGE 1: INGESTION ROLLBACK
    # ========================================================================
    
    def ingestion_rollback(self, run_id: str, failed_filename: str, 
                          validation_error: str) -> Dict:
        """
        Rollback specific file that failed validation during upload
        Removes only the failed file, preserves other uploaded files
        
        Args:
            run_id: Current run identifier
            failed_filename: Name of the file that failed validation
            validation_error: Description of the validation error
        
        Returns:
            Dict with rollback details and status
        """
        rollback_id = self._log_rollback(
            RollbackLevel.INGESTION,
            run_id,
            {
                "failed_file": failed_filename,
                "error": validation_error,
                "action": "remove_failed_file"
            }
        )
        
        try:
            self._update_rollback_status(rollback_id, RollbackStatus.IN_PROGRESS)
            
            run_folder = os.path.join(self.upload_dir, run_id)
            failed_file_path = os.path.join(run_folder, failed_filename)
            
            # Remove the failed file
            if os.path.exists(failed_file_path):
                os.remove(failed_file_path)
                logger.info(f"Ingestion rollback: Removed {failed_filename} from {run_id}")
            
            # Update metadata
            metadata_path = os.path.join(run_folder, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Remove from uploaded_files
                if "uploaded_files" in metadata:
                    metadata["uploaded_files"] = [
                        f for f in metadata["uploaded_files"] if f != failed_filename
                    ]
                
                # Add rollback record
                if "rollback_history" not in metadata:
                    metadata["rollback_history"] = []
                metadata["rollback_history"].append({
                    "rollback_id": rollback_id,
                    "timestamp": datetime.now().isoformat(),
                    "removed_file": failed_filename,
                    "reason": validation_error
                })
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            self._update_rollback_status(rollback_id, RollbackStatus.COMPLETED)
            
            return {
                "status": "success",
                "rollback_id": rollback_id,
                "message": f"Ingestion rollback completed for {failed_filename}",
                "removed_file": failed_filename,
                "run_id": run_id
            }
        
        except Exception as e:
            logger.error(f"Ingestion rollback failed: {str(e)}")
            self._update_rollback_status(rollback_id, RollbackStatus.FAILED)
            raise
    
    # ========================================================================
    # STAGE 2: MID-RECON ROLLBACK
    # ========================================================================
    
    def mid_recon_rollback(self, run_id: str, error_message: str,
                          affected_transactions: Optional[List[str]] = None,
                          confirmation_required: bool = False) -> Dict:
        """
        Rollback uncommitted transactions during reconciliation
        Triggered by critical errors (DB disconnection, crashes, etc.)
        Restores all affected transactions to 'unmatched' state with atomic operations

        Args:
            run_id: Current run identifier
            error_message: Description of the error that triggered rollback
            affected_transactions: List of transaction IDs to rollback
            confirmation_required: Whether user confirmation is needed

        Returns:
            Dict with rollback details
        """
        # Validate rollback operation
        can_rollback, validation_msg = self._validate_rollback_allowed(run_id, RollbackLevel.MID_RECON)
        if not can_rollback:
            raise ValueError(f"Mid-recon rollback not allowed: {validation_msg}")

        if confirmation_required:
            return {
                "status": "confirmation_required",
                "message": f"Mid-recon rollback requires confirmation. Error: {error_message}",
                "affected_transactions": affected_transactions or [],
                "run_id": run_id,
                "confirmation_details": {
                    "rollback_level": "mid_recon",
                    "error_message": error_message,
                    "affected_count": len(affected_transactions) if affected_transactions else 0
                }
            }

        rollback_id = self._log_rollback(
            RollbackLevel.MID_RECON,
            run_id,
            {
                "error": error_message,
                "affected_count": len(affected_transactions) if affected_transactions else 0,
                "action": "restore_unmatched_state",
                "confirmation_provided": not confirmation_required
            }
        )

        try:
            self._update_rollback_status(rollback_id, RollbackStatus.IN_PROGRESS)

            # Load current recon output
            output_dir = os.path.join(self.output_dir, run_id)
            recon_output_path = os.path.join(output_dir, "recon_output.json")

            if not os.path.exists(recon_output_path):
                raise FileNotFoundError(f"Reconciliation output not found: {recon_output_path}")

            with open(recon_output_path, 'r') as f:
                recon_data = json.load(f)

            # Create backup before rolling back (atomic operation)
            backup_path = os.path.join(output_dir, f"recon_output_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            try:
                shutil.copy(recon_output_path, backup_path)
                logger.info(f"Backup created: {backup_path}")
            except Exception as backup_error:
                logger.error(f"Failed to create backup: {str(backup_error)}")
                raise ValueError(f"Cannot proceed without backup: {str(backup_error)}")

            # Atomic transaction state restoration
            original_matched = recon_data.get("matched", [])
            original_unmatched = recon_data.get("unmatched", [])
            transactions_restored = []

            if affected_transactions:
                # Find and validate affected transactions
                affected_txns_found = []
                for txn_id in affected_transactions:
                    matching_txns = [
                        t for t in original_matched
                        if t.get("txn_id") == txn_id or t.get("rrn") == txn_id
                    ]
                    if matching_txns:
                        affected_txns_found.extend(matching_txns)
                    else:
                        logger.warning(f"Transaction {txn_id} not found in matched transactions")

                # Remove affected transactions from matched
                remaining_matched = [
                    t for t in original_matched
                    if not any(t.get("txn_id") == txn_id or t.get("rrn") == txn_id for txn_id in affected_transactions)
                ]

                # Add affected transactions back to unmatched with rollback metadata
                restored_unmatched = original_unmatched.copy()
                for txn in affected_txns_found:
                    txn_copy = txn.copy()
                    txn_copy["rollback_metadata"] = {
                        "rollback_id": rollback_id,
                        "previous_status": "matched",
                        "rollback_timestamp": datetime.now().isoformat(),
                        "rollback_reason": error_message
                    }
                    restored_unmatched.append(txn_copy)
                    transactions_restored.append(txn.get("rrn") or txn.get("txn_id"))

                # Update recon data atomically
                recon_data["matched"] = remaining_matched
                recon_data["unmatched"] = restored_unmatched
            else:
                # Rollback all matched transactions if no specific transactions provided
                logger.warning("No specific transactions provided - rolling back all matched transactions")
                all_matched_txns = original_matched.copy()
                recon_data["matched"] = []
                recon_data["unmatched"] = original_unmatched + all_matched_txns
                transactions_restored = [t.get("rrn") or t.get("txn_id") for t in all_matched_txns]

            # Update status counters with rollback information
            recon_data["summary"] = {
                "total_matched": len(recon_data.get("matched", [])),
                "total_unmatched": len(recon_data.get("unmatched", [])),
                "last_rollback": {
                    "rollback_id": rollback_id,
                    "level": "mid_recon",
                    "transactions_restored": len(transactions_restored),
                    "error_message": error_message,
                    "timestamp": datetime.now().isoformat()
                },
                "rollback_timestamp": datetime.now().isoformat()
            }

            # Atomic save operation
            temp_file = recon_output_path + ".tmp"
            try:
                with open(temp_file, 'w') as f:
                    json.dump(recon_data, f, indent=2)
                os.replace(temp_file, recon_output_path)  # Atomic file replacement
                logger.info(f"Mid-recon rollback completed for {run_id}. {len(transactions_restored)} transactions restored.")
            except Exception as save_error:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                raise ValueError(f"Failed to save rolled back data: {str(save_error)}")

            self._update_rollback_status(rollback_id, RollbackStatus.COMPLETED)

            return {
                "status": "success",
                "rollback_id": rollback_id,
                "message": f"Mid-recon rollback completed. {len(transactions_restored)} transactions restored to unmatched state.",
                "affected_transactions": affected_transactions or [],
                "transactions_restored": transactions_restored,
                "run_id": run_id,
                "backup_created": backup_path,
                "confirmation_provided": not confirmation_required
            }

        except Exception as e:
            logger.error(f"Mid-recon rollback failed: {str(e)}")
            self._update_rollback_status(rollback_id, RollbackStatus.FAILED)
            raise
    
    # ========================================================================
    # STAGE 3: CYCLE-WISE ROLLBACK
    # ========================================================================
    
    def cycle_wise_rollback(self, run_id: str, cycle_id: str,
                           confirmation_required: bool = False) -> Dict:
        """
        Rollback specific NPCI cycle for re-processing with atomic operations
        Does not affect other cycles or previously matched transactions
        NPCI operates on 10 cycles: 1A, 1B, 1C, 2A, 2B, 2C, 3A, 3B, 3C, 4

        Args:
            run_id: Current run identifier
            cycle_id: NPCI cycle to rollback (e.g., '1C', '3B')
            confirmation_required: Whether user confirmation is needed

        Returns:
            Dict with rollback details
        """
        # Validate rollback operation
        can_rollback, validation_msg = self._validate_rollback_allowed(run_id, RollbackLevel.CYCLE_WISE)
        if not can_rollback:
            raise ValueError(f"Cycle-wise rollback not allowed: {validation_msg}")

        # Validate cycle_id format
        valid_cycles = ['1A', '1B', '1C', '2A', '2B', '2C', '3A', '3B', '3C', '4']
        if cycle_id not in valid_cycles:
            raise ValueError(f"Invalid cycle ID '{cycle_id}'. Valid cycles: {', '.join(valid_cycles)}")

        if confirmation_required:
            return {
                "status": "confirmation_required",
                "message": f"Cycle-wise rollback requires confirmation for cycle {cycle_id}",
                "cycle_id": cycle_id,
                "run_id": run_id,
                "confirmation_details": {
                    "rollback_level": "cycle_wise",
                    "cycle_id": cycle_id,
                    "action": "restore_cycle_data"
                }
            }

        rollback_id = self._log_rollback(
            RollbackLevel.CYCLE_WISE,
            run_id,
            {
                "cycle_id": cycle_id,
                "action": "restore_cycle_data",
                "confirmation_provided": not confirmation_required
            }
        )

        try:
            self._update_rollback_status(rollback_id, RollbackStatus.IN_PROGRESS)

            output_dir = os.path.join(self.output_dir, run_id)
            recon_output_path = os.path.join(output_dir, "recon_output.json")

            if not os.path.exists(recon_output_path):
                raise FileNotFoundError(f"Reconciliation output not found: {recon_output_path}")

            with open(recon_output_path, 'r') as f:
                recon_data = json.load(f)

            # Create backup before rolling back (atomic operation)
            backup_path = os.path.join(output_dir, f"cycle_{cycle_id}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            try:
                shutil.copy(recon_output_path, backup_path)
                logger.info(f"Backup created: {backup_path}")
            except Exception as backup_error:
                logger.error(f"Failed to create backup: {str(backup_error)}")
                raise ValueError(f"Cannot proceed without backup: {str(backup_error)}")

            # Atomic cycle transaction restoration
            matched_txns = recon_data.get("matched", [])
            original_unmatched = recon_data.get("unmatched", [])

            # Find transactions from specific cycle with validation
            cycle_txns = []
            for txn in matched_txns:
                if txn.get("cycle_id") == cycle_id:
                    cycle_txns.append(txn)

            if not cycle_txns:
                logger.warning(f"No transactions found for cycle {cycle_id} in matched transactions")
                # Still proceed but log the situation

            # Remove cycle transactions from matched
            remaining_matched = [t for t in matched_txns if t.get("cycle_id") != cycle_id]

            # Add cycle transactions back to unmatched with rollback metadata
            restored_unmatched = original_unmatched.copy()
            for txn in cycle_txns:
                txn_copy = txn.copy()
                txn_copy["rollback_metadata"] = {
                    "rollback_id": rollback_id,
                    "previous_status": "matched",
                    "cycle_id": cycle_id,
                    "rollback_timestamp": datetime.now().isoformat(),
                    "rollback_reason": f"Cycle {cycle_id} rollback for re-processing"
                }
                restored_unmatched.append(txn_copy)

            # Update recon data atomically
            recon_data["matched"] = remaining_matched
            recon_data["unmatched"] = restored_unmatched

            # Update status counters with detailed rollback information
            recon_data["summary"] = {
                "total_matched": len(remaining_matched),
                "total_unmatched": len(restored_unmatched),
                "last_cycle_rollback": {
                    "rollback_id": rollback_id,
                    "cycle_id": cycle_id,
                    "transactions_restored": len(cycle_txns),
                    "timestamp": datetime.now().isoformat(),
                    "confirmation_provided": not confirmation_required
                },
                "rollback_timestamp": datetime.now().isoformat()
            }

            # Atomic save operation
            temp_file = recon_output_path + ".tmp"
            try:
                with open(temp_file, 'w') as f:
                    json.dump(recon_data, f, indent=2)
                os.replace(temp_file, recon_output_path)  # Atomic file replacement
                logger.info(f"Cycle-wise rollback for {cycle_id} completed. {len(cycle_txns)} transactions restored.")
            except Exception as save_error:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                raise ValueError(f"Failed to save rolled back data: {str(save_error)}")

            self._update_rollback_status(rollback_id, RollbackStatus.COMPLETED)

            return {
                "status": "success",
                "rollback_id": rollback_id,
                "message": f"Cycle {cycle_id} rolled back for re-processing. {len(cycle_txns)} transactions restored.",
                "cycle_id": cycle_id,
                "transactions_restored": len(cycle_txns),
                "run_id": run_id,
                "backup_created": backup_path,
                "confirmation_provided": not confirmation_required
            }

        except Exception as e:
            logger.error(f"Cycle-wise rollback failed: {str(e)}")
            self._update_rollback_status(rollback_id, RollbackStatus.FAILED)
            raise
    
    # ========================================================================
    # STAGE 4: ACCOUNTING ROLLBACK
    # ========================================================================
    
    def accounting_rollback(self, run_id: str, reason: str,
                           voucher_ids: Optional[List[str]] = None,
                           confirmation_required: bool = False) -> Dict:
        """
        Rollback voucher generation when CBS upload fails with atomic operations
        Resets status from 'settled/voucher generated' to 'matched/pending'
        Prevents corrupted GL entries with comprehensive validation

        Args:
            run_id: Current run identifier
            reason: Reason for rollback (e.g., 'CBS upload failure')
            voucher_ids: List of voucher IDs to rollback (None for all)
            confirmation_required: Whether user confirmation is needed

        Returns:
            Dict with rollback details
        """
        # Validate rollback operation
        can_rollback, validation_msg = self._validate_rollback_allowed(run_id, RollbackLevel.ACCOUNTING)
        if not can_rollback:
            raise ValueError(f"Accounting rollback not allowed: {validation_msg}")

        # Validate reason
        if not reason or not reason.strip():
            raise ValueError("Rollback reason cannot be empty")

        if confirmation_required:
            voucher_count = len(voucher_ids) if voucher_ids else "all"
            return {
                "status": "confirmation_required",
                "message": f"Accounting rollback requires confirmation. {voucher_count} vouchers will be reset.",
                "reason": reason,
                "voucher_ids": voucher_ids,
                "run_id": run_id,
                "confirmation_details": {
                    "rollback_level": "accounting",
                    "reason": reason,
                    "voucher_count": len(voucher_ids) if voucher_ids else 0,
                    "action": "reset_vouchers_to_pending"
                }
            }

        rollback_id = self._log_rollback(
            RollbackLevel.ACCOUNTING,
            run_id,
            {
                "reason": reason,
                "voucher_count": len(voucher_ids) if voucher_ids else 0,
                "action": "reset_to_matched_pending",
                "confirmation_provided": not confirmation_required
            }
        )

        try:
            self._update_rollback_status(rollback_id, RollbackStatus.IN_PROGRESS)

            output_dir = os.path.join(self.output_dir, run_id)
            accounting_path = os.path.join(output_dir, "accounting_output.json")

            if not os.path.exists(accounting_path):
                raise FileNotFoundError(f"Accounting output not found: {accounting_path}")

            with open(accounting_path, 'r') as f:
                accounting_data = json.load(f)

            # Create backup before rolling back (atomic operation)
            backup_path = os.path.join(output_dir, f"accounting_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            try:
                shutil.copy(accounting_path, backup_path)
                logger.info(f"Backup created: {backup_path}")
            except Exception as backup_error:
                logger.error(f"Failed to create backup: {str(backup_error)}")
                raise ValueError(f"Cannot proceed without backup: {str(backup_error)}")

            # Atomic voucher status reset
            vouchers = accounting_data.get("vouchers", [])
            vouchers_reset = []
            vouchers_not_found = []

            if voucher_ids:
                # Specific voucher rollback
                for voucher_id in voucher_ids:
                    voucher_found = False
                    for voucher in vouchers:
                        if voucher.get("voucher_id") == voucher_id:
                            if voucher.get("status") == "voucher_generated":
                                voucher["previous_status"] = voucher["status"]
                                voucher["status"] = "matched/pending"
                                voucher["rollback_metadata"] = {
                                    "rollback_id": rollback_id,
                                    "rollback_timestamp": datetime.now().isoformat(),
                                    "rollback_reason": reason,
                                    "previous_gl_entries": voucher.get("gl_entries", [])
                                }
                                # Clear GL entries to prevent corruption
                                voucher["gl_entries"] = []
                                vouchers_reset.append(voucher_id)
                                voucher_found = True
                                break
                    if not voucher_found:
                        vouchers_not_found.append(voucher_id)
            else:
                # Rollback all vouchers
                for voucher in vouchers:
                    if voucher.get("status") == "voucher_generated":
                        voucher["previous_status"] = voucher["status"]
                        voucher["status"] = "matched/pending"
                        voucher["rollback_metadata"] = {
                            "rollback_id": rollback_id,
                            "rollback_timestamp": datetime.now().isoformat(),
                            "rollback_reason": reason,
                            "previous_gl_entries": voucher.get("gl_entries", [])
                        }
                        # Clear GL entries to prevent corruption
                        voucher["gl_entries"] = []
                        vouchers_reset.append(voucher.get("voucher_id"))

            # Log warnings for vouchers not found
            if vouchers_not_found:
                logger.warning(f"Vouchers not found for rollback: {', '.join(vouchers_not_found)}")

            # Update accounting summary with detailed rollback information
            accounting_data["accounting_status"] = {
                "status": "rolled_back",
                "vouchers_reset": len(vouchers_reset),
                "vouchers_not_found": len(vouchers_not_found),
                "rollback_reason": reason,
                "rollback_id": rollback_id,
                "timestamp": datetime.now().isoformat(),
                "confirmation_provided": not confirmation_required,
                "gl_entries_cleared": True
            }

            # Atomic save operation
            temp_file = accounting_path + ".tmp"
            try:
                with open(temp_file, 'w') as f:
                    json.dump(accounting_data, f, indent=2)
                os.replace(temp_file, accounting_path)  # Atomic file replacement
                logger.info(f"Accounting rollback completed for {run_id}. {len(vouchers_reset)} vouchers reset. Reason: {reason}")
            except Exception as save_error:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                raise ValueError(f"Failed to save rolled back accounting data: {str(save_error)}")

            self._update_rollback_status(rollback_id, RollbackStatus.COMPLETED)

            return {
                "status": "success",
                "rollback_id": rollback_id,
                "message": f"Accounting rollback completed. {len(vouchers_reset)} vouchers reset to matched/pending state.",
                "reason": reason,
                "vouchers_reset": vouchers_reset,
                "vouchers_not_found": vouchers_not_found,
                "run_id": run_id,
                "backup_created": backup_path,
                "confirmation_provided": not confirmation_required,
                "gl_entries_cleared": True
            }

        except Exception as e:
            logger.error(f"Accounting rollback failed: {str(e)}")
            self._update_rollback_status(rollback_id, RollbackStatus.FAILED)
            raise
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_rollback_history(self, run_id: Optional[str] = None) -> List[Dict]:
        """Get rollback history, optionally filtered by run_id"""
        with open(self.rollback_history_file, 'r') as f:
            history = json.load(f)
        
        if run_id:
            return [r for r in history if r.get("run_id") == run_id]
        return history
    
    def _validate_run_exists(self, run_id: str) -> bool:
        """Validate that the run folder exists"""
        run_folder = os.path.join(self.upload_dir, run_id)
        return os.path.exists(run_folder)

    def _validate_files_exist(self, run_id: str, required_files: List[str]) -> Tuple[bool, str]:
        """Validate that required files exist for rollback"""
        run_folder = os.path.join(self.upload_dir, run_id)
        missing_files = []

        for file in required_files:
            if not os.path.exists(os.path.join(run_folder, file)):
                missing_files.append(file)

        if missing_files:
            return False, f"Missing required files: {', '.join(missing_files)}"

        return True, "All required files present"

    def _validate_rollback_allowed(self, run_id: str, rollback_level: RollbackLevel) -> Tuple[bool, str]:
        """Validate if rollback operation is allowed based on current state"""
        # Check for recent rollback (prevent cascading rollbacks)
        history = self.get_rollback_history(run_id)
        if history and history[-1]["status"] == RollbackStatus.IN_PROGRESS.value:
            return False, "Rollback already in progress for this run"

        # Check if run exists
        if not self._validate_run_exists(run_id):
            return False, f"Run {run_id} not found"

        # Level-specific validations
        if rollback_level == RollbackLevel.MID_RECON:
            output_dir = os.path.join(self.output_dir, run_id)
            recon_file = os.path.join(output_dir, "recon_output.json")
            if not os.path.exists(recon_file):
                return False, "No reconciliation output found for mid-recon rollback"

        elif rollback_level == RollbackLevel.CYCLE_WISE:
            output_dir = os.path.join(self.output_dir, run_id)
            recon_file = os.path.join(output_dir, "recon_output.json")
            if not os.path.exists(recon_file):
                return False, "No reconciliation output found for cycle-wise rollback"

        elif rollback_level == RollbackLevel.ACCOUNTING:
            output_dir = os.path.join(self.output_dir, run_id)
            accounting_file = os.path.join(output_dir, "accounting_output.json")
            if not os.path.exists(accounting_file):
                return False, "No accounting output found for accounting rollback"

        return True, "Rollback allowed"

    def can_rollback(self, run_id: str, rollback_level: RollbackLevel) -> Tuple[bool, str]:
        """Check if rollback operation is allowed"""
        return self._validate_rollback_allowed(run_id, rollback_level)
