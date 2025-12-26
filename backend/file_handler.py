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
        """Save uploaded files to timestamped folder with standardized naming - Windows compatible"""
        run_folder = os.path.join(UPLOAD_DIR, run_id)
        os.makedirs(run_folder, exist_ok=True)

        # Enhanced file type mapping with better pattern recognition
        file_type_mapping = {
            'cbs_inward': ['cbs_inward', 'cbs inward', 'cbs-inward', 'cbsinward'],
            'cbs_outward': ['cbs_outward', 'cbs outward', 'cbs-outward', 'cbsoutward'],
            'switch': ['switch', 'switch_file', 'switch data', 'switch-data'],
            'npci_inward': ['npci_inward', 'npci inward', 'npci-inward', 'npciinward', 'npci inward remittance'],
            'npci_outward': ['npci_outward', 'npci outward', 'npci-outward', 'npcioutward', 'npci outward remittance'],
            'ntsl': ['ntsl', 'ntsl_file', 'ntsl data', 'national', 'national_switch'],
            'adjustment': ['adjustment', 'adjustments', 'adj', 'adjustment_file']
        }

        saved_files = {}
        file_metadata = {}

        for filename, file_content in files.items():
            # Determine file type using enhanced pattern matching
            file_type = self._determine_file_type(filename, file_type_mapping)

            # Generate standardized filename with timestamp and validation
            standardized_name = self._generate_standardized_filename(file_type, filename)

            file_path = os.path.join(run_folder, standardized_name)

            try:
                # Validate file content before saving
                if self._validate_file_content(file_content, filename):
                    with open(file_path, 'wb') as f:
                        f.write(file_content)

                    saved_files[file_type] = standardized_name
                    file_metadata[filename] = {
                        'standardized_name': standardized_name,
                        'file_type': file_type,
                        'original_name': filename,
                        'file_size': len(file_content),
                        'saved_at': os.path.getctime(file_path)
                    }
                    logger.info(f"✅ Saved file: {standardized_name} (original: {filename}, type: {file_type})")
                else:
                    logger.warning(f"⚠️  Skipped invalid/empty file: {filename}")
                    continue

            except Exception as e:
                logger.error(f"❌ Error saving file {filename}: {e}")
                continue

        # Save enhanced file mapping and metadata
        self._save_file_metadata(run_folder, saved_files, file_metadata)

        return run_folder

    def _determine_file_type(self, filename: str, file_type_mapping: Dict) -> str:
        """Determine file type using enhanced pattern matching"""
        filename_lower = filename.lower().strip()

        # Check for exact matches first
        for file_type, patterns in file_type_mapping.items():
            for pattern in patterns:
                if pattern.lower() in filename_lower:
                    return file_type

        # Fallback: extract type from filename components
        if 'cbs' in filename_lower:
            if 'inward' in filename_lower or 'inw' in filename_lower:
                return 'cbs_inward'
            elif 'outward' in filename_lower or 'out' in filename_lower:
                return 'cbs_outward'
            else:
                return 'cbs_general'
        elif 'switch' in filename_lower:
            return 'switch'
        elif 'npci' in filename_lower:
            if 'inward' in filename_lower or 'inw' in filename_lower:
                return 'npci_inward'
            elif 'outward' in filename_lower or 'out' in filename_lower:
                return 'npci_outward'
            else:
                return 'npci_general'
        elif 'ntsl' in filename_lower or 'national' in filename_lower:
            return 'ntsl'
        elif 'adjust' in filename_lower:
            return 'adjustment'

        # Final fallback: clean filename for type
        return filename_lower.replace(' ', '_').replace('-', '_').split('_')[0]

    def _generate_standardized_filename(self, file_type: str, original_filename: str) -> str:
        """Generate standardized filename with timestamp and proper extension"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Determine file extension
        extension = self._get_file_extension(original_filename)

        # Create standardized name based on file type
        if file_type == 'cbs_inward':
            return f"cbs_inward_{timestamp}{extension}"
        elif file_type == 'cbs_outward':
            return f"cbs_outward_{timestamp}{extension}"
        elif file_type == 'switch':
            return f"switch_{timestamp}{extension}"
        elif file_type == 'npci_inward':
            return f"npci_inward_{timestamp}{extension}"
        elif file_type == 'npci_outward':
            return f"npci_outward_{timestamp}{extension}"
        elif file_type == 'ntsl':
            return f"ntsl_{timestamp}{extension}"
        elif file_type == 'adjustment':
            return f"adjustment_{timestamp}{extension}"
        else:
            # Generic naming for unknown types
            return f"{file_type}_{timestamp}{extension}"

    def _get_file_extension(self, filename: str) -> str:
        """Determine appropriate file extension"""
        filename_lower = filename.lower()
        if filename_lower.endswith('.csv'):
            return '.csv'
        elif filename_lower.endswith(('.xlsx', '.xls')):
            return '.xlsx'
        elif filename_lower.endswith('.txt'):
            return '.txt'
        elif filename_lower.endswith('.json'):
            return '.json'
        else:
            # Default to CSV for financial data files
            return '.csv'

    def _validate_file_content(self, file_content: bytes, filename: str) -> bool:
        """Validate file content before saving"""
        if not file_content or len(file_content) == 0:
            logger.warning(f"File '{filename}' is empty.")
            return False

        # Check for minimum file size (at least 10 bytes for valid data)
        if len(file_content) < 10:
            logger.warning(f"File '{filename}' is too small to be a valid data file.")
            return False

        # Validate file content based on extension
        if filename.lower().endswith('.xlsx'):
            if not self._is_xlsx(file_content):
                logger.error(f"File '{filename}' has an .xlsx extension but is not a valid XLSX file.")
                return False
        
        return True

    def _is_xlsx(self, file_content: bytes) -> bool:
        """Check if the file content has the XLSX magic number."""
        # XLSX files (which are zip files) start with 'PK\x03\x04'
        return file_content.startswith(b'PK\x03\x04')

    def _save_file_metadata(self, run_folder: str, saved_files: Dict, file_metadata: Dict):
        """Save comprehensive file metadata and mapping"""
        try:
            # Save file mapping
            mapping_file = os.path.join(run_folder, "file_mapping.json")
            with open(mapping_file, 'w') as f:
                import json
                json.dump(saved_files, f, indent=2)

            # Save detailed metadata
            metadata_file = os.path.join(run_folder, "file_metadata.json")
            with open(metadata_file, 'w') as f:
                json.dump(file_metadata, f, indent=2, default=str)

            logger.info(f"✅ File metadata saved for {len(saved_files)} files")

        except Exception as e:
            logger.warning(f"⚠️  Could not save file metadata: {e}")
    
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