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

