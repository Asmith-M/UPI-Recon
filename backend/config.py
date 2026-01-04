import os
from datetime import datetime

# File paths
UPLOAD_DIR = "data/uploads"
OUTPUT_DIR = "data/output"
SAMPLE_DATA_DIR = "sample_data"

# Required fields for all files (our internal standard)
REQUIRED_FIELDS = {
    'RRN': str,
    'Amount': float,
    'Tran_Date': str,
    'Dr_Cr': str,
    'RC': str,
    'Tran_Type': str
}

# File types expected
EXPECTED_FILES = [
    'cbs_inward.csv',
    'cbs_outward.csv', 
    'switch.csv',
    'npci_inward.csv',
    'npci_outward.csv',
    'ntsl.csv',
    'adjustment.csv'
]

# Run ID format
RUN_ID_FORMAT = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# UPI Reconciliation Configurations
UPI_MATCHING_CONFIGS = [
    {
        'name': 'best_match',
        'params': ['UPI_Tran_ID', 'RRN', 'Tran_Date', 'Amount'],
        'required_fields': ['UPI_Tran_ID', 'RRN'],
        'description': 'Best match with all key parameters'
    },
    {
        'name': 'relaxed_match_i',
        'params': ['UPI_Tran_ID', 'Tran_Date', 'Amount'],
        'required_fields': ['UPI_Tran_ID'],
        'description': 'Relaxed match without RRN'
    },
    {
        'name': 'relaxed_match_ii',
        'params': ['RRN', 'Tran_Date', 'Amount'],
        'required_fields': ['RRN'],
        'description': 'Relaxed match without UPI_Tran_ID'
    }
]

# TTUM Types Configuration
TTUM_TYPES = {
    'REMITTER_REFUND': {
        'type': 'OUTWARD',
        'description': 'Refund to remitter for failed transactions',
        'gl_accounts': {
            'debit': 'NPCI_SETTLEMENT_ACCOUNT',
            'credit': 'REMITTER_ACCOUNT'
        }
    },
    'REMITTER_RECOVERY': {
        'type': 'OUTWARD',
        'description': 'Recovery from remitter for unauthorized transactions',
        'gl_accounts': {
            'debit': 'REMITTER_ACCOUNT',
            'credit': 'NPCI_SETTLEMENT_ACCOUNT'
        }
    },
    'FAILED_AUTO_CREDIT_REVERSAL': {
        'type': 'OUTWARD',
        'description': 'Reversal of failed auto-credit transactions',
        'gl_accounts': {
            'debit': 'NPCI_SETTLEMENT_ACCOUNT',
            'credit': 'REMITTER_ACCOUNT'
        }
    },
    'DOUBLE_DEBIT_CREDIT_REVERSAL': {
        'type': 'BOTH',
        'description': 'Reversal of double debit/credit entries',
        'gl_accounts': {
            'debit': 'REMITTER_ACCOUNT',
            'credit': 'NPCI_SETTLEMENT_ACCOUNT'
        }
    },
    'NTSL_SETTLEMENT': {
        'type': 'BOTH',
        'description': 'NTSL settlement entries',
        'gl_accounts': {
            'debit': 'INTERNAL_SETTLEMENT',
            'credit': 'NPCI_SETTLEMENT_ACCOUNT'
        }
    },
    'DRC': {
        'type': 'OUTWARD',
        'description': 'Debit Reversal Confirmation',
        'gl_accounts': {
            'debit': 'NPCI_SETTLEMENT_ACCOUNT',
            'credit': 'REMITTER_ACCOUNT'
        }
    },
    'RRC': {
        'type': 'OUTWARD',
        'description': 'Return Reversal Confirmation',
        'gl_accounts': {
            'debit': 'NPCI_SETTLEMENT_ACCOUNT',
            'credit': 'REMITTER_ACCOUNT'
        }
    },
    'BENEFICIARY_RECOVERY': {
        'type': 'INWARD',
        'description': 'Recovery from beneficiary for failed inward transactions',
        'gl_accounts': {
            'debit': 'BENEFICIARY_ACCOUNT',
            'credit': 'NPCI_SETTLEMENT_ACCOUNT'
        }
    },
    'BENEFICIARY_CREDIT': {
        'type': 'INWARD',
        'description': 'Credit to beneficiary for successful inward transactions',
        'gl_accounts': {
            'debit': 'NPCI_SETTLEMENT_ACCOUNT',
            'credit': 'BENEFICIARY_ACCOUNT'
        }
    },
    'TCC_102': {
        'type': 'INWARD',
        'description': 'Deemed accepted with CBS credit found',
        'gl_accounts': {
            'debit': 'NPCI_SETTLEMENT_ACCOUNT',
            'credit': 'BENEFICIARY_ACCOUNT'
        }
    },
    'TCC_103': {
        'type': 'INWARD',
        'description': 'Deemed accepted but no CBS credit - needs TTUM',
        'gl_accounts': {
            'debit': 'NPCI_SETTLEMENT_ACCOUNT',
            'credit': 'BENEFICIARY_ACCOUNT'
        }
    },
    'RET': {
        'type': 'BOTH',
        'description': 'Return transactions',
        'gl_accounts': {
            'debit': 'REMITTER_ACCOUNT',
            'credit': 'NPCI_SETTLEMENT_ACCOUNT'
        }
    },
    'REVERSAL': {
        'type': 'OUTWARD',
        'description': 'General reversal transactions for failed or erroneous entries',
        'gl_accounts': {
            'debit': 'NPCI_SETTLEMENT_ACCOUNT',
            'credit': 'REMITTER_ACCOUNT'
        }
    }
}

# GL Account Mappings (to be configured based on bank setup)
GL_ACCOUNTS = {
    'NPCI_SETTLEMENT_ACCOUNT': 'NPCI_SETTLEMENT',
    'REMITTER_ACCOUNT': 'REMITTER_ACCOUNTS',
    'BENEFICIARY_ACCOUNT': 'BENEFICIARY_ACCOUNTS',
    'INTERNAL_SETTLEMENT': 'INTERNAL_SETTLEMENT',
    'PAYABLE_GL': 'PAYABLE_GL',
    'RECEIVABLE_GL': 'RECEIVABLE_GL'
}

# Exception Handling Matrix
EXCEPTION_MATRIX = {
    'SUCCESS_SUCCESS_SUCCESS': {
        'action': 'MATCHED',
        'ttum_required': False,
        'description': 'All three sources successful - no action needed'
    },
    'SUCCESS_SUCCESS_FAILED': {
        'action': 'REMITTER_REFUND',
        'ttum_required': True,
        'description': 'CBS and Switch successful, NPCI failed - remitter refund'
    },
    'SUCCESS_FAILED_SUCCESS': {
        'action': 'SWITCH_UPDATE',
        'ttum_required': False,
        'description': 'CBS and NPCI successful, Switch failed - update switch'
    },
    'SUCCESS_FAILED_FAILED': {
        'action': 'REMITTER_REFUND',
        'ttum_required': True,
        'description': 'CBS successful, Switch and NPCI failed - remitter refund'
    },
    'FAILED_SUCCESS_SUCCESS': {
        'action': 'BENEFICIARY_RECOVERY',
        'ttum_required': True,
        'description': 'CBS failed, Switch and NPCI successful - beneficiary recovery'
    },
    'FAILED_SUCCESS_FAILED': {
        'action': 'UNMATCHED',
        'ttum_required': False,
        'description': 'CBS and NPCI failed, Switch successful - manual review'
    },
    'FAILED_FAILED_SUCCESS': {
        'action': 'BENEFICIARY_RECOVERY',
        'ttum_required': True,
        'description': 'CBS and Switch failed, NPCI successful - beneficiary recovery'
    },
    'FAILED_FAILED_FAILED': {
        'action': 'UNMATCHED',
        'ttum_required': False,
        'description': 'All sources failed - manual review'
    }
}

# Transaction Categorization
TRANSACTION_CATEGORIES = {
    'MATCHED': 'Transactions successfully matched across all sources',
    'HANGING': 'Transactions pending from previous/next cycle',
    'TCC_102': 'Deemed accepted transactions with CBS credit',
    'TCC_103': 'Deemed accepted transactions without CBS credit',
    'RET': 'Return transactions',
    'UNMATCHED': 'Transactions that could not be matched'
}

