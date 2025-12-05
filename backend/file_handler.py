import os
import pandas as pd
from typing import Dict, List
from config import UPLOAD_DIR, OUTPUT_DIR, RUN_ID_FORMAT
from logging_config import get_logger

logger = get_logger(__name__)

class FileHandler:
    def __init__(self):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    def save_uploaded_files(self, files: Dict, run_id: str) -> str:
        """Save uploaded files to timestamped folder - Windows compatible"""
        run_folder = os.path.join(UPLOAD_DIR, run_id)
        os.makedirs(run_folder, exist_ok=True)
        
        for filename, file_content in files.items():
            clean_filename = filename.replace('\\', '_').replace('/', '_')
            file_path = os.path.join(run_folder, clean_filename)
            
            try:
                with open(file_path, 'wb') as f:
                    f.write(file_content)
            except Exception as e:
                print(f"Error saving file {filename}: {e}")
                continue
        
        return run_folder
    
    def load_files_for_recon(self, run_folder: str) -> List[pd.DataFrame]:
        """Load all files and add source column with smart column detection"""
        dataframes = []
        
        if not os.path.exists(run_folder):
            print(f"Folder does not exist: {run_folder}")
            return dataframes
        
        for filename in os.listdir(run_folder):
            filepath = os.path.join(run_folder, filename)
            
            # Skip empty files (placeholder files)
            if os.path.getsize(filepath) == 0:
                print(f"Skipping empty file: {filename}")
                continue
            
            if filename.endswith('.csv'):
                try:
                    df = pd.read_csv(filepath)
                except Exception as e:
                    print(f"Error reading CSV file {filepath}: {e}")
                    continue
            elif filename.endswith(('.xlsx', '.xls')):
                try:
                    df = pd.read_excel(filepath)
                except Exception as e:
                    print(f"Error reading Excel file {filepath}: {e}")
                    continue
            else:
                continue
            
            if 'cbs' in filename.lower():
                source = 'CBS'
            elif 'switch' in filename.lower():
                source = 'SWITCH'
            elif 'npci' in filename.lower():
                source = 'NPCI'
            else:
                source = 'OTHER'
            
            # Smart auto-map columns
            df = self._smart_map_columns(df)
            df['Source'] = source
            dataframes.append(df)
        return dataframes
    
    def _smart_map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Smartly map columns using multiple detection methods"""
        renamed_df = df.copy()
        
        # Standard column definitions with multiple possible names
        column_definitions = {
            'RRN': ['rrn', 'reference number', 'ref number', 'reference', 'ref', 
                   'transaction id', 'txn id', 'transaction_id', 'txn_id', 'id', 
                   'unique id', 'unique_id', 'reference_no', 'ref_no'],
            'Amount': ['amount', 'amt', 'tran amount', 'transaction amount', 
                      'tran_amt', 'transaction_amt', 'value', 'amt', 'amount_inr', 
                      'tran_value', 'transaction_value', 'principal', 'principal_amount'],
            'Tran_Date': ['date', 'tran date', 'transaction date', 'tran_date', 
                         'transaction_date', 'trn date', 'trn_date', 'dt', 
                         'trans_date', 'transaction_dt', 'date_time', 'datetime',
                         'tran_datetime', 'transaction_datetime'],
            'Dr_Cr': ['dr_cr', 'd/c', 'dr/cr', 'debit_credit', 'debit/credit', 
                     'type', 'transaction_type', 'tran_type', 'txn_type', 'mode',
                     'credit_debit', 'c/d', 'cd'],
            'RC': ['rc', 'rcode', 'response code', 'response_code', 'status', 
                  'status_code', 'response', 'rcode_val', 'response_val', 'error_code'],
            'Tran_Type': ['type', 'tran type', 'transaction type', 'tran_type', 
                         'transaction_type', 'mode', 'payment type', 'payment_type', 
                         'transaction_mode', 'payment_mode', 'service', 'service_type']
        }
        
        # Create standard columns
        for standard_col, possible_names in column_definitions.items():
            found_col = self._find_best_matching_column(df.columns, possible_names)
            
            if found_col:
                renamed_df[standard_col] = df[found_col]
            else:
                renamed_df[standard_col] = None
        
        # Keep only required columns + Source
        required_cols = ['RRN', 'Amount', 'Tran_Date', 'Dr_Cr', 'RC', 'Tran_Type', 'Source']
        available_cols = [col for col in required_cols if col in renamed_df.columns]
        
        return renamed_df[available_cols]
    
    def _find_best_matching_column(self, df_columns, possible_names):
        """Find the best matching column using multiple strategies"""
        # Strategy 1: Exact match (case-insensitive)
        for col in df_columns:
            if col.lower().strip() in [name.lower() for name in possible_names]:
                return col
        
        # Strategy 2: Partial match (contains keywords)
        for col in df_columns:
            col_lower = col.lower().strip()
            for name in possible_names:
                if name.lower() in col_lower or col_lower in name.lower():
                    return col
        
        # Strategy 3: Return first column if no matches found (for debugging)
        # This is fallback - in production you might want to return None
        return None