"""
Settlement Accounting Engine - Phase 3 Task 4
Generates vouchers and GL entries from reconciled transactions
Integrates with GL Proofing for variance analysis and bridging
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
from logging_config import get_logger

logger = get_logger(__name__)


class VoucherType(Enum):
    """Types of accounting vouchers"""
    PAYMENT = "PAYMENT"          # Customer payments
    REVERSAL = "REVERSAL"        # Transaction reversals
    ADJUSTMENT = "ADJUSTMENT"    # Manual adjustments
    SETTLEMENT = "SETTLEMENT"    # Settlement entries


class VoucherStatus(Enum):
    """Status of voucher processing"""
    GENERATED = "generated"      # Voucher created
    POSTED = "posted"           # Posted to GL
    FAILED = "failed"           # Posting failed
    REVERSED = "reversed"       # Voucher reversed


class GLEntry:
    """Represents a General Ledger entry"""

    def __init__(
        self,
        account_code: str,
        account_name: str,
        debit_amount: float = 0.0,
        credit_amount: float = 0.0,
        description: str = "",
        reference: str = ""
    ):
        self.account_code = account_code
        self.account_name = account_name
        self.debit_amount = debit_amount
        self.credit_amount = credit_amount
        self.description = description
        self.reference = reference
        self.entry_id = f"GL_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "entry_id": self.entry_id,
            "account_code": self.account_code,
            "account_name": self.account_name,
            "debit_amount": self.debit_amount,
            "credit_amount": self.credit_amount,
            "description": self.description,
            "reference": self.reference,
            "timestamp": self.timestamp
        }


class Voucher:
    """Represents an accounting voucher"""

    def __init__(
        self,
        voucher_id: str,
        voucher_type: VoucherType,
        transaction_date: str,
        amount: float,
        description: str,
        gl_entries: List[GLEntry]
    ):
        self.voucher_id = voucher_id
        self.voucher_type = voucher_type
        self.transaction_date = transaction_date
        self.amount = amount
        self.description = description
        self.gl_entries = gl_entries
        self.status = VoucherStatus.GENERATED
        self.created_at = datetime.now().isoformat()
        self.posted_at = None
        self.rrn = None  # Link to original transaction

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "voucher_id": self.voucher_id,
            "voucher_type": self.voucher_type.value,
            "transaction_date": self.transaction_date,
            "amount": self.amount,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "posted_at": self.posted_at,
            "rrn": self.rrn,
            "gl_entries": [entry.to_dict() for entry in self.gl_entries]
        }


class SettlementEngine:
    """Engine for generating vouchers and GL entries from reconciled transactions"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.settlement_dir = os.path.join(output_dir, "settlement")
        os.makedirs(self.settlement_dir, exist_ok=True)

        # GL Account mappings (configurable)
        self.gl_accounts = {
            "cash_account": {"code": "100100", "name": "Cash in Hand"},
            "bank_account": {"code": "100200", "name": "Bank Account"},
            "suspense_account": {"code": "200100", "name": "Suspense Account"},
            "fee_income": {"code": "400100", "name": "Transaction Fee Income"},
            "fee_expense": {"code": "500100", "name": "Transaction Fee Expense"},
            "settlement_payable": {"code": "200200", "name": "Settlement Payable"},
            "settlement_receivable": {"code": "100300", "name": "Settlement Receivable"}
        }

        self.vouchers: List[Voucher] = []
        self.voucher_counter = 1

    def generate_vouchers_from_recon(self, recon_results: Dict, run_id: str) -> Dict:
        """
        Generate vouchers and GL entries from reconciliation results

        Args:
            recon_results: Reconciliation results dictionary
            run_id: Current run identifier

        Returns:
            Dict with settlement details
        """
        logger.info(f"Generating vouchers for run {run_id}")

        vouchers = []
        total_amount = 0.0
        matched_count = 0
        settlement_count = 0

        # Process matched transactions
        for rrn, record in recon_results.items():
            if record.get('status') == 'MATCHED':
                try:
                    voucher = self._create_payment_voucher(rrn, record)
                    if voucher:
                        vouchers.append(voucher)
                        total_amount += voucher.amount
                        matched_count += 1

                except Exception as e:
                    logger.error(f"Failed to create voucher for RRN {rrn}: {str(e)}")

            elif record.get('status') in ['PARTIAL_MATCH', 'ORPHAN']:
                try:
                    voucher = self._create_settlement_voucher(rrn, record)
                    if voucher:
                        vouchers.append(voucher)
                        settlement_count += 1

                except Exception as e:
                    logger.error(f"Failed to create settlement voucher for RRN {rrn}: {str(e)}")

        # Save vouchers to file
        settlement_data = {
            "run_id": run_id,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_vouchers": len(vouchers),
                "matched_transactions": matched_count,
                "settlement_transactions": settlement_count,
                "total_amount": total_amount
            },
            "vouchers": [v.to_dict() for v in vouchers]
        }

        settlement_path = os.path.join(self.settlement_dir, f"settlement_{run_id}.json")
        with open(settlement_path, 'w') as f:
            json.dump(settlement_data, f, indent=2)

        self.vouchers.extend(vouchers)

        logger.info(f"Generated {len(vouchers)} vouchers totaling ₹{total_amount:,.2f}")

        return {
            "status": "success",
            "run_id": run_id,
            "vouchers_generated": len(vouchers),
            "total_amount": total_amount,
            "matched_count": matched_count,
            "settlement_count": settlement_count,
            "settlement_file": settlement_path
        }

    def _create_payment_voucher(self, rrn: str, record: Dict) -> Optional[Voucher]:
        """Create payment voucher for matched transactions"""
        # Get transaction amount (assume CBS amount as primary)
        amount = 0.0
        transaction_date = ""

        if record.get('cbs'):
            amount = record['cbs'].get('amount', 0)
            transaction_date = record['cbs'].get('date', '')

        if amount <= 0:
            return None

        voucher_id = f"VOUCHER_{self.voucher_counter:06d}"
        self.voucher_counter += 1

        # Create GL entries for payment voucher
        gl_entries = []

        # Debit bank account (money received)
        gl_entries.append(GLEntry(
            account_code=self.gl_accounts["bank_account"]["code"],
            account_name=self.gl_accounts["bank_account"]["name"],
            debit_amount=amount,
            description=f"Payment received - RRN {rrn}",
            reference=f"RRN:{rrn}"
        ))

        # Credit settlement receivable (liability to customer)
        gl_entries.append(GLEntry(
            account_code=self.gl_accounts["settlement_receivable"]["code"],
            account_name=self.gl_accounts["settlement_receivable"]["name"],
            credit_amount=amount,
            description=f"Settlement receivable - RRN {rrn}",
            reference=f"RRN:{rrn}"
        ))

        voucher = Voucher(
            voucher_id=voucher_id,
            voucher_type=VoucherType.PAYMENT,
            transaction_date=transaction_date,
            amount=amount,
            description=f"Payment voucher for matched transaction RRN {rrn}",
            gl_entries=gl_entries
        )
        voucher.rrn = rrn

        return voucher

    def _create_settlement_voucher(self, rrn: str, record: Dict) -> Optional[Voucher]:
        """Create settlement voucher for unmatched transactions"""
        # Get available amount
        amount = 0.0
        transaction_date = ""
        source = ""

        # Prefer CBS amount, then Switch, then NPCI
        if record.get('cbs'):
            amount = record['cbs'].get('amount', 0)
            transaction_date = record['cbs'].get('date', '')
            source = "CBS"
        elif record.get('switch'):
            amount = record['switch'].get('amount', 0)
            transaction_date = record['switch'].get('date', '')
            source = "Switch"
        elif record.get('npci'):
            amount = record['npci'].get('amount', 0)
            transaction_date = record['npci'].get('date', '')
            source = "NPCI"

        if amount <= 0:
            return None

        voucher_id = f"SETTLE_{self.voucher_counter:06d}"
        self.voucher_counter += 1

        # Create GL entries for settlement voucher
        gl_entries = []

        # Debit suspense account (unmatched transaction)
        gl_entries.append(GLEntry(
            account_code=self.gl_accounts["suspense_account"]["code"],
            account_name=self.gl_accounts["suspense_account"]["name"],
            debit_amount=amount,
            description=f"Unmatched transaction - RRN {rrn} ({source})",
            reference=f"RRN:{rrn}"
        ))

        # Credit settlement payable (amount to be settled)
        gl_entries.append(GLEntry(
            account_code=self.gl_accounts["settlement_payable"]["code"],
            account_name=self.gl_accounts["settlement_payable"]["name"],
            credit_amount=amount,
            description=f"Settlement payable - RRN {rrn}",
            reference=f"RRN:{rrn}"
        ))

        voucher = Voucher(
            voucher_id=voucher_id,
            voucher_type=VoucherType.SETTLEMENT,
            transaction_date=transaction_date,
            amount=amount,
            description=f"Settlement voucher for unmatched transaction RRN {rrn} ({source})",
            gl_entries=gl_entries
        )
        voucher.rrn = rrn

        return voucher

    def post_vouchers_to_gl(self, voucher_ids: Optional[List[str]] = None) -> Dict:
        """
        Post vouchers to General Ledger

        Args:
            voucher_ids: Specific voucher IDs to post (None for all)

        Returns:
            Dict with posting results
        """
        target_vouchers = []
        if voucher_ids:
            target_vouchers = [v for v in self.vouchers if v.voucher_id in voucher_ids]
        else:
            target_vouchers = [v for v in self.vouchers if v.status == VoucherStatus.GENERATED]

        posted_count = 0
        failed_count = 0

        for voucher in target_vouchers:
            try:
                # Validate GL entries balance
                total_debit = sum(entry.debit_amount for entry in voucher.gl_entries)
                total_credit = sum(entry.credit_amount for entry in voucher.gl_entries)

                if abs(total_debit - total_credit) > 0.01:  # Allow small rounding differences
                    raise ValueError(f"Voucher {voucher.voucher_id} is not balanced: Debit ₹{total_debit}, Credit ₹{total_credit}")

                # Mark as posted
                voucher.status = VoucherStatus.POSTED
                voucher.posted_at = datetime.now().isoformat()
                posted_count += 1

                logger.info(f"Posted voucher {voucher.voucher_id} to GL")

            except Exception as e:
                voucher.status = VoucherStatus.FAILED
                failed_count += 1
                logger.error(f"Failed to post voucher {voucher.voucher_id}: {str(e)}")

        return {
            "status": "completed",
            "posted_count": posted_count,
            "failed_count": failed_count,
            "total_attempted": len(target_vouchers)
        }

    def get_voucher_summary(self, run_id: Optional[str] = None) -> Dict:
        """Get voucher summary statistics"""
        if run_id:
            # Load from file
            settlement_file = os.path.join(self.settlement_dir, f"settlement_{run_id}.json")
            if os.path.exists(settlement_file):
                with open(settlement_file, 'r') as f:
                    data = json.load(f)
                return data.get("summary", {})

        # Calculate from current vouchers
        total_vouchers = len(self.vouchers)
        posted_vouchers = len([v for v in self.vouchers if v.status == VoucherStatus.POSTED])
        total_amount = sum(v.amount for v in self.vouchers)

        return {
            "total_vouchers": total_vouchers,
            "posted_vouchers": posted_vouchers,
            "total_amount": total_amount,
            "pending_posting": total_vouchers - posted_vouchers
        }

    def get_gl_entries_for_voucher(self, voucher_id: str) -> List[Dict]:
        """Get GL entries for a specific voucher"""
        for voucher in self.vouchers:
            if voucher.voucher_id == voucher_id:
                return [entry.to_dict() for entry in voucher.gl_entries]
        return []


# Helper function for API integration
def create_settlement_engine(output_dir: str) -> SettlementEngine:
    """Factory function to create settlement engine"""
    return SettlementEngine(output_dir)
