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
from annexure_iv import generate_annexure_iv_csv
from reporting import write_report, write_ttum_xlsx


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
        # Load optional TTUM mapping and issuer action file
        self.ttum_mapping = self._load_ttum_mapping()
        self.issuer_actions = self._load_issuer_actions()

    def _load_ttum_mapping(self) -> Dict:
        """Load optional TTUM mapping JSON from config/ttum_mapping.json if present."""
        try:
            cfg_dir = os.path.join(os.path.dirname(__file__), 'config')
            cfg_path = os.path.join(cfg_dir, 'ttum_mapping.json')
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _load_issuer_actions(self) -> Dict:
        """Attempt to read issuer action mapping from bank_recon_files/Issuer_Raw_20260103.xlsx
        Returns a mapping of RRN string -> { 'action_point': str, 'outward_payable': str (optional) }
        Handles spreadsheets where the outward GL may be in a top header row and the data header is on a later row.
        """
        try:
            import pandas as pd
            issuer_path = os.path.join(os.path.dirname(__file__), 'bank_recon_files', 'Issuer_Raw_20260103.xlsx')
            if not os.path.exists(issuer_path):
                return {}

            df = pd.read_excel(issuer_path, sheet_name=0, header=None, dtype=str)

            # Find outward GL: search first 5 rows/cols for a cell that looks like A<digits>
            outward_gl = None
            import re
            pattern = re.compile(r"\bA\d{6,}\b")
            for i in range(min(5, len(df.index))):
                for j in range(min(8, len(df.columns))):
                    cell = str(df.iat[i, j]) if pd.notna(df.iat[i, j]) else ''
                    if pattern.search(cell):
                        outward_gl = pattern.search(cell).group(0)
                        break
                if outward_gl:
                    break

            # Find header row which contains 'RRN' or 'Txn Category' or 'Action'
            header_row_idx = None
            rrn_idx = None
            action_idx = None
            desc_idx = None
            for i in range(min(10, len(df.index))):
                row_text = ' '.join([str(x).lower() if pd.notna(x) else '' for x in df.iloc[i].tolist()])
                if 'rrn' in row_text or 'txn category' in row_text or 'action point' in row_text or 'description' in row_text:
                    header_row_idx = i
                    # identify column indices
                    for j, val in enumerate(df.iloc[i].tolist()):
                        v = str(val).strip().lower() if pd.notna(val) else ''
                        if 'rrn' in v or 'reference' in v:
                            rrn_idx = j
                        if 'action' in v or 'action point' in v:
                            action_idx = j
                        if 'description' in v or 'desc' in v:
                            desc_idx = j
                    break

            issuer_map = {}
            current_category = None
            start_row = header_row_idx + 1 if header_row_idx is not None else 0
            for i in range(start_row, len(df.index)):
                row = df.iloc[i].tolist()
                # category may appear in first column when RRN blank
                first = str(row[0]).strip() if pd.notna(row[0]) else ''
                if first and not any(ch.isdigit() for ch in first):
                    current_category = first
                # get rrn from identified column or by searching numeric-like cell
                rrn = None
                if rrn_idx is not None:
                    val = row[rrn_idx] if rrn_idx < len(row) else None
                    if pd.notna(val) and str(val).strip():
                        rrn = str(val).strip()
                if not rrn:
                    # try find a numeric-looking string in row
                    for v in row:
                        if pd.notna(v):
                            s = str(v).strip()
                            if s.isdigit():
                                rrn = s
                                break
                if not rrn:
                    continue
                action = ''
                if action_idx is not None and action_idx < len(row) and pd.notna(row[action_idx]):
                    action = str(row[action_idx]).strip()
                # fallback to derive action from current category
                if not action and current_category:
                    action = current_category

                issuer_map[str(rrn)] = {
                    'action_point': action,
                    'outward_payable': outward_gl
                }

            return issuer_map
        except Exception:
            return {}

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

    def generate_gl_statement(self, run_id: str, run_folder: str) -> str:
        """Generate a GL statement CSV from generated vouchers for the run."""
        import csv
        try:
            settlement_file = os.path.join(self.settlement_dir, f"settlement_{run_id}.json")
            if not os.path.exists(settlement_file):
                return ''
            with open(settlement_file, 'r') as f:
                data = json.load(f)

            reports_dir = os.path.join(run_folder, 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            gl_path = os.path.join(reports_dir, 'gl_statement.csv')
            with open(gl_path, 'w', newline='') as gf:
                writer = csv.writer(gf)
                writer.writerow(['Voucher_ID', 'RRN', 'Voucher_Type', 'Amount', 'Status', 'Created_At'])
                for v in data.get('vouchers', []):
                    writer.writerow([v.get('voucher_id'), v.get('rrn'), v.get('voucher_type'), v.get('amount'), v.get('status'), v.get('created_at')])

            return gl_path
        except Exception as e:
            logger.error(f"Failed to generate GL statement: {e}")
            return ''

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

    def generate_ttum_files(self, recon_results: Dict, run_folder: str) -> Dict:
        """Generate NPCI-like TTUM CSVs (DRC, RRC, TCC, RET, RECOVERY, REFUND)
        Generates a set of CSVs under run_folder/ttum and returns mapping of category->path.
        This implements a closer Annexure-IV-like CSV format per TTUM category.
        Fields (approx): InstructionType, InstructionRefNo, RRN, Amount, ValueDate, DrCr, RC, Tran_Type, AccountNo, IFSC, Narration, TTUM_Code
        """
        import csv
        import json
        ttum_dir = os.path.join(run_folder, 'ttum')
        os.makedirs(ttum_dir, exist_ok=True)

        # attempt to infer run_id and cycle_id from the provided run_folder path
        run_id = None
        cycle_id = None
        try:
            # walk up components to find a folder starting with 'RUN_'
            parts = os.path.normpath(run_folder).split(os.path.sep)
            for p in parts[::-1]:
                if p.startswith('RUN_'):
                    run_id = p
                    break
            # find any 'cycle_<id>' component
            for p in parts:
                if p.startswith('cycle_'):
                    cycle_id = p.split('cycle_', 1)[1]
                    break
        except Exception:
            run_id = None
            cycle_id = None

        categories = ['DRC', 'RRC', 'TCC', 'RET', 'RECOVERY', 'REFUND']
        created = {}
        annexure_records = []

        # mapping from our internal category -> Annexure Flag
        flag_map = {
            'DRC': 'DRC',
            'RRC': 'RRC',
            'TCC': 'TCC',
            'RET': 'RET',
            'REFUND': 'CR',
            'RECOVERY': 'DRC'
        }

        # Helper to pick source record
        def pick_source(rec):
            for s in ['cbs', 'switch', 'npci']:
                if rec.get(s):
                    return rec[s]
            return {}

        for cat in categories:
            # If we have a canonical run_id, prefer writing TTUMs via centralized reporting.write_report
            headers = [
                'InstructionType', 'InstructionRefNo', 'RRN', 'Amount', 'ValueDate', 'DrCr', 'RC', 'Tran_Type',
                'AccountNo', 'IFSC', 'Narration', 'TTUM_Code', 'GL_Debit_Account', 'GL_Credit_Account'
            ]

            rows_for_cat = []
            for rrn, rec in recon_results.items():
                    if not isinstance(rec, dict):
                        continue
                    status = rec.get('status')
                    src = pick_source(rec)
                    amount = src.get('amount', '')
                    tran_date = src.get('date', '')
                    drcr = src.get('dr_cr', '')
                    rc = src.get('rc', '')
                    ttype = src.get('tran_type', '')

                    # normalize rrn as string for lookup
                    rrn_str = str(rrn)
                    issuer_action = {}
                    try:
                        if self.issuer_actions and rrn_str in self.issuer_actions:
                            issuer_action = self.issuer_actions.get(rrn_str, {}) or {}
                    except Exception:
                        issuer_action = {}

                    # normalize value date to YYYYMMDD-ish where possible
                    value_date = ''
                    try:
                        if tran_date:
                            # attempt several formats
                            try:
                                value_date = datetime.fromisoformat(tran_date).strftime('%Y%m%d')
                            except Exception:
                                try:
                                    value_date = datetime.strptime(tran_date, '%Y-%m-%d').strftime('%Y%m%d')
                                except Exception:
                                    value_date = tran_date
                    except Exception:
                        value_date = tran_date

                    instr_type = cat
                    instr_ref = f"TTUM_{cat}_{rrn}"
                    narration = f"{cat} for {rrn}"

                    # Default GL mapping (use settlement engine GL config)
                    gl_debit = self.gl_accounts.get('suspense_account', {}).get('code', '')
                    gl_credit = self.gl_accounts.get('settlement_payable', {}).get('code', '')


                    # If issuer provides a specific outward/payable GL, use it as override
                    try:
                        if issuer_action and isinstance(issuer_action, dict):
                            out_gl = issuer_action.get('outward_payable')
                            if out_gl and str(out_gl).strip():
                                # Use issuer outward GL for credit when action suggests outward/payable
                                gl_credit = str(out_gl).strip()
                    except Exception:
                        pass

                    # Determine TTUM-specific accounting mapping per functional rules
                    if cat == 'REFUND' and status in ['ORPHAN', 'PARTIAL_MATCH', 'MISMATCH']:
                        gl_debit = self.gl_accounts.get('settlement_payable', {}).get('code', '')
                        # default remitter credit to bank_account unless issuer overrides
                        gl_credit = self.gl_accounts.get('bank_account', {}).get('code', '')
                        # issuer_action may explicitly indicate refund mapping
                        if issuer_action and isinstance(issuer_action, dict):
                            action = (issuer_action.get('action_point') or '').lower()
                            if 'refund' in action:
                                # if issuer outward_payable provided, use it as credit (payable)
                                out_gl = issuer_action.get('outward_payable')
                                if out_gl and str(out_gl).strip():
                                    gl_credit = str(out_gl).strip()

                    if cat == 'RECOVERY' and status in ['ORPHAN', 'PARTIAL_MATCH', 'MISMATCH']:
                        gl_debit = self.gl_accounts.get('bank_account', {}).get('code', '')
                        gl_credit = self.gl_accounts.get('settlement_receivable', {}).get('code', '')
                        if issuer_action and isinstance(issuer_action, dict):
                            action = (issuer_action.get('action_point') or '').lower()
                            if 'recovery' in action:
                                out_gl = issuer_action.get('outward_payable')
                                if out_gl and str(out_gl).strip():
                                    # for recovery use outward_payable as relevant accounting reference
                                    gl_credit = str(out_gl).strip()

                    if cat == 'TCC' and rec.get('tcc') == 'TCC_103':
                        gl_debit = self.gl_accounts.get('suspense_account', {}).get('code', '')
                        gl_credit = self.gl_accounts.get('settlement_payable', {}).get('code', '')

                    if cat in ['DRC', 'RRC']:
                        if str(drcr).upper().startswith('D'):
                            gl_debit = self.gl_accounts.get('settlement_payable', {}).get('code', '')
                            gl_credit = self.gl_accounts.get('suspense_account', {}).get('code', '')
                        else:
                            gl_debit = self.gl_accounts.get('suspense_account', {}).get('code', '')
                            gl_credit = self.gl_accounts.get('settlement_payable', {}).get('code', '')

                    # TCC generation: NPCI RC startswith RB
                    if cat == 'TCC' and rc and str(rc).upper().startswith('RB'):
                        row = [instr_type, instr_ref, rrn, amount, value_date, drcr, rc, ttype, '', '', narration, 'TCC', gl_debit, gl_credit]
                        rows_for_cat.append(dict(zip(headers, row)))
                        # collect annexure row
                        try:
                            annex_flag = flag_map.get(cat, 'TCC')
                            shtdat = ''
                            # value_date may be YYYYMMDD, convert to YYYY-MM-DD when possible
                            try:
                                if value_date and len(value_date) == 8 and value_date.isdigit():
                                    shtdat = datetime.strptime(value_date, '%Y%m%d').strftime('%Y-%m-%d')
                            except Exception:
                                shtdat = ''
                            annexure_records.append({
                                'Bankadjref': f"BR_{cat}_{rrn}_{int(datetime.now().timestamp())}",
                                'Flag': annex_flag,
                                'shtdat': shtdat or tran_date or '',
                                'adjsmt': amount or '',
                                'Shser': rrn,
                                'Shcrd': f"NBIN{rrn}",
                                'FileName': os.path.basename(path),
                                'reason': rc or '',
                                'specifyother': narration
                            })
                        except Exception:
                            pass

                    # DRC/RRC for settlement differences (use PARTIAL_MATCH/ORPHAN/MISMATCH)
                    if cat in ['DRC', 'RRC'] and status in ['PARTIAL_MATCH', 'ORPHAN', 'MISMATCH']:
                        row = [instr_type, instr_ref, rrn, amount, value_date, drcr, rc, ttype, '', '', narration, cat, gl_debit, gl_credit]
                        rows_for_cat.append(dict(zip(headers, row)))
                        # collect annexure row
                        try:
                            annex_flag = flag_map.get(cat, cat)
                            shtdat = ''
                            try:
                                if value_date and len(value_date) == 8 and value_date.isdigit():
                                    shtdat = datetime.strptime(value_date, '%Y%m%d').strftime('%Y-%m-%d')
                            except Exception:
                                shtdat = ''
                            annexure_records.append({
                                'Bankadjref': f"BR_{cat}_{rrn}_{int(datetime.now().timestamp())}",
                                'Flag': annex_flag,
                                'shtdat': shtdat or tran_date or '',
                                'adjsmt': amount or '',
                                'Shser': rrn,
                                'Shcrd': f"NBIN{rrn}",
                                'FileName': os.path.basename(path),
                                'reason': rc or '',
                                'specifyother': narration
                            })
                        except Exception:
                            pass

                    # REFUND/RECOVERY for outward/inward mismatches
                    if cat in ['RECOVERY', 'REFUND'] and status in ['ORPHAN', 'PARTIAL_MATCH', 'MISMATCH']:
                        # If issuer_action indicates Ignore or Hanging or No Action, skip
                        skip_for_action = False
                        if issuer_action and isinstance(issuer_action, dict):
                            act = (issuer_action.get('action_point') or '').lower()
                            if any(x in act for x in ['ignore', 'no action', 'hanging', 'hang', 'matched', 'both leg present']):
                                skip_for_action = True
                        if not skip_for_action:
                            row = [instr_type, instr_ref, rrn, amount, value_date, drcr, rc, ttype, '', '', narration, cat, gl_debit, gl_credit]
                            rows_for_cat.append(dict(zip(headers, row)))
                            # collect annexure row (map REFUND->CR)
                            try:
                                annex_flag = flag_map.get(cat, 'CR')
                                shtdat = ''
                                try:
                                    if value_date and len(value_date) == 8 and value_date.isdigit():
                                        shtdat = datetime.strptime(value_date, '%Y%m%d').strftime('%Y-%m-%d')
                                except Exception:
                                    shtdat = ''
                                annexure_records.append({
                                    'Bankadjref': f"BR_{cat}_{rrn}_{int(datetime.now().timestamp())}",
                                    'Flag': annex_flag,
                                    'shtdat': shtdat or tran_date or '',
                                    'adjsmt': amount or '',
                                    'Shser': rrn,
                                    'Shcrd': f"NBIN{rrn}",
                                    'FileName': os.path.basename(path),
                                    'reason': rc or '',
                                    'specifyother': narration
                                })
                            except Exception:
                                pass

                    # RET (returns) - NPCI failed but CBS success
                    if cat == 'RET' and (rec.get('needs_ttum') or rec.get('status') == 'EXCEPTION'):
                        row = [instr_type, instr_ref, rrn, amount, value_date, drcr, rc, ttype, '', '', f'RET for {rrn}', 'RET', gl_debit, gl_credit]
                        rows_for_cat.append(dict(zip(headers, row)))
                        try:
                            annex_flag = flag_map.get(cat, 'RET')
                            shtdat = ''
                            try:
                                if value_date and len(value_date) == 8 and value_date.isdigit():
                                    shtdat = datetime.strptime(value_date, '%Y%m%d').strftime('%Y-%m-%d')
                            except Exception:
                                shtdat = ''
                            annexure_records.append({
                                'Bankadjref': f"BR_{cat}_{rrn}_{int(datetime.now().timestamp())}",
                                'Flag': annex_flag,
                                'shtdat': shtdat or tran_date or '',
                                'adjsmt': amount or '',
                                'Shser': rrn,
                                'Shcrd': f"NBIN{rrn}",
                                'FileName': os.path.basename(path),
                                'reason': rc or '',
                                'specifyother': f'RET for {rrn}'
                            })
                        except Exception:
                            pass

            # If we inferred a run_id, write via reporting utility (centralized output path), otherwise fallback to legacy file under run_folder
            if run_id:
                try:
                    outp = write_report(run_id, cycle_id, 'ttum', f"{cat.lower()}.csv", headers, rows_for_cat)
                    created[cat] = outp
                    write_ttum_xlsx(run_id, cycle_id, f"{cat.lower()}", headers, rows_for_cat)
                except Exception:
                    # fallback: write directly into ttum_dir
                    path = os.path.join(ttum_dir, f"{cat.lower()}.csv")
                    with open(path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(headers)
                        for r in rows_for_cat:
                            writer.writerow([r.get(h, '') for h in headers])
                    created[cat] = path
            else:
                path = os.path.join(ttum_dir, f"{cat.lower()}.csv")
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    for r in rows_for_cat:
                        writer.writerow([r.get(h, '') for h in headers])
                created[cat] = path

        # write index file
        try:
            idx = os.path.join(ttum_dir, 'index.json')
            with open(idx, 'w') as jf:
                json.dump({'generated': datetime.now().isoformat(), 'files': list(created.values())}, jf, indent=2)
        except Exception:
            pass

        # Generate Annexure-IV CSV if we collected any records
        try:
            if annexure_records:
                # Normalize annexure records to ensure mandatory fields (shtdat, adjsmt)
                norm_recs = []
                for rec in annexure_records:
                    r = rec.copy()
                    # ensure shtdat exists and is YYYY-MM-DD; fallback to today
                    try:
                        if not r.get('shtdat'):
                            r['shtdat'] = datetime.now().strftime('%Y-%m-%d')
                        else:
                            try:
                                r['shtdat'] = datetime.fromisoformat(str(r['shtdat'])).strftime('%Y-%m-%d')
                            except Exception:
                                try:
                                    r['shtdat'] = datetime.strptime(str(r['shtdat']), '%Y-%m-%d').strftime('%Y-%m-%d')
                                except Exception:
                                    r['shtdat'] = datetime.now().strftime('%Y-%m-%d')
                    except Exception:
                        r['shtdat'] = datetime.now().strftime('%Y-%m-%d')

                    # ensure adjsmt formatted to two decimals
                    try:
                        if r.get('adjsmt') is None or str(r.get('adjsmt')).strip() == '':
                            r['adjsmt'] = '0.00'
                        else:
                            r['adjsmt'] = format(float(r['adjsmt']), '.2f')
                    except Exception:
                        r['adjsmt'] = '0.00'

                    # ensure required string fields
                    r['Bankadjref'] = str(r.get('Bankadjref') or f"BR_{int(datetime.now().timestamp())}")
                    r['Shser'] = str(r.get('Shser') or '')
                    r['Shcrd'] = str(r.get('Shcrd') or '')
                    r['FileName'] = str(r.get('FileName') or os.path.basename(ttum_dir))
                    # NPCI reason must be max 5 chars per Annexure-IV; truncate if longer
                    r['reason'] = str(r.get('reason') or '')[:5]
                    r['specifyother'] = str(r.get('specifyother') or '')

                    norm_recs.append(r)

                try:
                    # Prefer to write Annexure via standardized reporting if we have run_id
                    if run_id:
                        annex_path = generate_annexure_iv_csv(norm_recs, run_id=run_id, cycle_id=cycle_id)
                    else:
                        annex_path = os.path.join(ttum_dir, 'annexure_iv.csv')
                        generate_annexure_iv_csv(norm_recs, annex_path)
                    created['ANNEXURE_IV'] = annex_path
                except Exception as e:
                    logger.error(f"Failed to generate Annexure-IV CSV: {e}")
        except Exception:
            pass

        return created


# Helper function for API integration
def create_settlement_engine(output_dir: str) -> SettlementEngine:
    """Factory function to create settlement engine"""
    return SettlementEngine(output_dir)
