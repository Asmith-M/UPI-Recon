import pandas as pd
import os
from typing import Dict, List, Tuple
import json
from datetime import datetime
from loguru import logger
from settlement_engine import SettlementEngine

# Constants
CBS = 'cbs'
SWITCH = 'switch'
NPCI = 'npci'
SOURCES = [CBS, SWITCH, NPCI]

RRN = 'RRN'
AMOUNT = 'Amount'
TRAN_DATE = 'Tran_Date'
SOURCE = 'Source'
DR_CR = 'Dr_Cr'
RC = 'RC'
TRAN_TYPE = 'Tran_Type'

MATCHED = 'MATCHED'
MISMATCH = 'MISMATCH'
PARTIAL_MATCH = 'PARTIAL_MATCH'
PARTIAL_MISMATCH = 'PARTIAL_MISMATCH'
ORPHAN = 'ORPHAN'
UNKNOWN = 'UNKNOWN'
FORCE_MATCHED = 'FORCE_MATCHED'
PROCESSING_ERROR = 'PROCESSING_ERROR'

class ReconciliationEngine:
    def __init__(self, output_dir: str = "./data/output"):
        self.output_dir = output_dir
        self.matched_records = []
        self.partial_match_records = []
        self.orphan_records = []
        self.exceptions = []
        self.settlement_engine = SettlementEngine(output_dir)
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataframe based on a configuration."""
        
        # Configuration for handling missing values
        missing_value_config = {
            RRN: {'fillna': '', 'astype': str, 'strip': True},
            AMOUNT: {'to_numeric': True, 'fillna': 0},
            TRAN_DATE: {'fillna': '1970-01-01', 'astype': str},
            DR_CR: {'fillna': '', 'astype': str},
            RC: {'fillna': '', 'astype': str},
            TRAN_TYPE: {'fillna': '', 'astype': str}
        }

        for col, config in missing_value_config.items():
            if col in df.columns:
                if config.get('to_numeric'):
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(config['fillna'])
                else:
                    df[col] = df[col].fillna(config['fillna'])
                
                if 'astype' in config:
                    df[col] = df[col].astype(config['astype'])
                
                if config.get('strip'):
                    df[col] = df[col].str.strip()
        
        return df

    def reconcile(self, dataframes: List[pd.DataFrame]) -> Dict:
        """Main reconciliation logic - RRN + Amount + Date matching with comprehensive error handling"""
        logger.info(f"Starting reconciliation with {len(dataframes)} dataframes")

        self._clear_previous_run_data()

        try:
            processed_dataframes = self._preprocess_dataframes(dataframes)
            combined_df = self._combine_dataframes(processed_dataframes)
            results = self._perform_reconciliation_logic(combined_df)
            self._generate_summary(results)
            
            return results

        except Exception as e:
            logger.error(f"Reconciliation failed with error: {str(e)}")
            raise ValueError(f"Reconciliation process failed: {str(e)}")

    def _clear_previous_run_data(self):
        """Clears data from previous reconciliation runs."""
        self.matched_records = []
        self.partial_match_records = []
        self.orphan_records = []
        self.exceptions = []

    def _preprocess_dataframes(self, dataframes: List[pd.DataFrame]) -> List[pd.DataFrame]:
        """Preprocessing and validation of the input dataframes."""
        processed_dataframes = []
        for i, df in enumerate(dataframes):
            try:
                required_cols = [RRN, AMOUNT, TRAN_DATE, SOURCE]
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    raise ValueError(f"Dataframe {i} missing required columns: {missing_cols}")

                df = self._handle_missing_values(df)

                original_count = len(df)
                df = df[df[RRN] != ''].reset_index(drop=True)
                removed_count = original_count - len(df)

                if removed_count > 0:
                    logger.warning(f"Removed {removed_count} rows with empty RRN from dataframe {i}")

                if not df.empty:
                    processed_dataframes.append(df)
                    logger.info(f"Processed dataframe {i}: {len(df)} valid records")
                else:
                    logger.warning(f"Dataframe {i} became empty after preprocessing")

            except Exception as df_error:
                logger.error(f"Error preprocessing dataframe {i}: {str(df_error)}")
                raise ValueError(f"Data preprocessing failed for dataframe {i}: {str(df_error)}")
        
        if not processed_dataframes:
            logger.error("No valid dataframes after preprocessing")
            raise ValueError("No valid data found after preprocessing all dataframes")
            
        return processed_dataframes

    def _combine_dataframes(self, dataframes: List[pd.DataFrame]) -> pd.DataFrame:
        """Combine the processed dataframes into a single dataframe."""
        try:
            combined_df = pd.concat(dataframes, ignore_index=True)
            logger.info(f"Combined dataframe has {len(combined_df)} total records")

            original_count = len(combined_df)
            combined_df = combined_df[combined_df[RRN] != ''].reset_index(drop=True)
            removed_count = original_count - len(combined_df)

            if removed_count > 0:
                logger.warning(f"Removed {removed_count} additional rows with empty RRN during combination")

            if combined_df.empty:
                logger.error("Combined dataframe is empty after final cleanup")
                raise ValueError("No valid transaction records found after data combination")
                
            return combined_df

        except Exception as combine_error:
            logger.error(f"Error combining dataframes: {str(combine_error)}")
            raise ValueError(f"Data combination failed: {str(combine_error)}")

    def _perform_reconciliation_logic(self, combined_df: pd.DataFrame) -> Dict:
        """This method contains the core reconciliation logic."""
        results = {}
        try:
            grouped = combined_df.groupby(RRN)
            total_groups = len(grouped)
            logger.info(f"Processing {total_groups} unique RRN groups")

            for rrn, group in grouped:
                try:
                    sources = set(group[SOURCE].tolist())
                    record = self._create_record_structure()

                    self._populate_record_by_source(record, group)
                    
                    self._classify_record(rrn, record, sources)

                    results[rrn] = record

                except Exception as rrn_error:
                    logger.error(f"Error processing RRN {rrn}: {str(rrn_error)}")
                    self.exceptions.append(rrn)
                    results[rrn] = self._create_error_record(rrn_error)

        except Exception as logic_error:
            logger.error(f"Critical error in reconciliation logic: {str(logic_error)}")
            raise ValueError(f"Reconciliation logic failed: {str(logic_error)}")
            
        return results

    def _create_record_structure(self) -> Dict:
        """Creates a new, empty record structure."""
        return {
            CBS: None,
            SWITCH: None,
            NPCI: None,
            'status': UNKNOWN
        }

    def _populate_record_by_source(self, record: Dict, group: pd.DataFrame):
        """Populates a record with data from a grouped DataFrame."""
        for _, row in group.iterrows():
            source = row[SOURCE].lower()
            if source in SOURCES:
                record[source] = {
                    'amount': row[AMOUNT],
                    'date': row[TRAN_DATE],
                    'dr_cr': row.get(DR_CR, ''),
                    'rc': row.get(RC, ''),
                    'tran_type': row.get(TRAN_TYPE, '')
                }

    def _classify_record(self, rrn: str, record: Dict, sources: set):
        """Classifies a record based on its status (e.g., MATCHED, MISMATCH)."""
        amounts = [record[s]['amount'] for s in SOURCES if record[s]]
        dates = [record[s]['date'] for s in SOURCES if record[s]]

        amount_set = set(amounts)
        date_set = set(dates)

        num_sources = len(sources)
        amounts_match = len(amount_set) == 1
        dates_match = len(date_set) == 1

        if num_sources == 3:
            if amounts_match and dates_match:
                record['status'] = MATCHED
                self.matched_records.append(rrn)
            else:
                record['status'] = MISMATCH
                self.exceptions.append(rrn)
        elif num_sources == 2:
            if amounts_match and dates_match:
                record['status'] = PARTIAL_MATCH
                self.partial_match_records.append(rrn)
            else:
                record['status'] = PARTIAL_MISMATCH
                self.exceptions.append(rrn)
        elif num_sources == 1:
            record['status'] = ORPHAN
            self.orphan_records.append(rrn)
        else:
            record['status'] = UNKNOWN
            self.exceptions.append(rrn)
            
    def _create_error_record(self, error: Exception) -> Dict:
        """Creates a new record that represents a processing error."""
        return {
            CBS: None, SWITCH: None, NPCI: None,
            'status': PROCESSING_ERROR,
            'error': str(error)
        }

    def _generate_summary(self, results: Dict):
        """Generates a summary of the reconciliation results."""
        logger.info(f"Reconciliation completed: {len(results)} total RRNs processed")
        logger.info(f"Results: {len(self.matched_records)} matched, {len(self.partial_match_records)} partial, {len(self.orphan_records)} orphan, {len(self.exceptions)} exceptions")

        if not results:
            logger.warning("Reconciliation completed but no results generated")
            raise ValueError("Reconciliation completed but no transaction records were processed")
    
    def force_match_rrn(self, rrn: str, source1: str, source2: str, results: Dict):
        """Force match a specific RRN between two sources"""
        if rrn in results:
            record = results[rrn]
            
            # Check if both sources exist in the record
            if record.get(source1) and record.get(source2):
                # Update status to force matched
                record['status'] = FORCE_MATCHED
                
                # Sync amount and date from source1 to source2
                record[source2]['amount'] = record[source1]['amount']
                record[source2]['date'] = record[source1]['date']
                
                logger.info(f"Successfully force-matched RRN {rrn} between {source1} and {source2}")
            else:
                logger.warning(f"Could not force-match RRN {rrn}: one or both sources not found.")
        else:
            logger.warning(f"Could not force-match RRN {rrn}: RRN not found in results.")
        
        return results
    
    def generate_report(self, results: Dict, run_id: str) -> str:
        """Generate human-readable report.txt with detailed breakdown"""
        unmatched_records = self.partial_match_records + self.orphan_records
        report_content = f"""BANK RECONCILIATION REPORT
Run ID: {run_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
Total RRNs processed: {len(results)}
Matched records: {len(self.matched_records)} (All 3 systems agree)
Partial Match records: {len(self.partial_match_records)} (2 systems match, 1 missing)
Orphan records: {len(self.orphan_records)} (Only in 1 system)
Exceptions: {len(self.exceptions)} (Data mismatches or inconsistencies)

Unmatched records: {len(unmatched_records)} (Partial + Orphan)

VALIDATION:
Total = Matched + Partial Match + Orphan + Exceptions = {len(self.matched_records) + len(self.partial_match_records) + len(self.orphan_records) + len(self.exceptions)}

MATCHED RECORDS ({len(self.matched_records)}):
{', '.join(self.matched_records[:20])}{'...' if len(self.matched_records) > 20 else ''}

PARTIAL MATCH RECORDS ({len(self.partial_match_records)}):
{', '.join(self.partial_match_records[:20])}{'...' if len(self.partial_match_records) > 20 else ''}

ORPHAN RECORDS ({len(self.orphan_records)}):
{', '.join(self.orphan_records[:20])}{'...' if len(self.orphan_records) > 20 else ''}

EXCEPTIONS ({len(self.exceptions)}):
{', '.join(self.exceptions[:20])}{'...' if len(self.exceptions) > 20 else ''}

DETAILED ANALYSIS:
- Matched: RRNs found in all 3 systems (CBS + Switch + NPCI) with SAME Amount + Date
- Partial Match: RRNs found in exactly 2 systems with matching data (missing in 1 system)
- Orphan: RRNs found in only 1 system (missing in 2 systems)
- Exceptions: RRNs with data inconsistencies
  * MISMATCH: Found in all 3 systems but amounts/dates don't match
  * PARTIAL_MISMATCH: Found in 2 systems but amounts/dates don't match
"""
        
        output_dir = os.path.dirname(run_id)
        report_path = os.path.join(output_dir, "report.txt")
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        return report_path
    
    def generate_adjustments_csv(self, results: Dict, run_id: str) -> str:
        """Generate adjustments.csv for Force Match UI"""
        adjustments_data = []
        
        for rrn, record in results.items():
            row = {
                RRN: rrn,
                'Status': record['status'],
                f'{CBS.upper()}_Amount': record[CBS]['amount'] if record[CBS] else '',
                f'{SWITCH.upper()}_Amount': record[SWITCH]['amount'] if record[SWITCH] else '',
                f'{NPCI.upper()}_Amount': record[NPCI]['amount'] if record[NPCI] else '',
                f'{CBS.upper()}_Date': record[CBS]['date'] if record[CBS] else '',
                f'{SWITCH.upper()}_Date': record[SWITCH]['date'] if record[SWITCH] else '',
                f'{NPCI.upper()}_Date': record[NPCI]['date'] if record[NPCI] else '',
                f'{CBS.upper()}_Source': 'X' if record[CBS] else '',
                f'{SWITCH.upper()}_Source': 'X' if record[SWITCH] else '',
                f'{NPCI.upper()}_Source': 'X' if record[NPCI] else '',
                'Suggested_Action': self._get_suggested_action(record)
            }
            adjustments_data.append(row)
        
        df = pd.DataFrame(adjustments_data)
        output_dir = os.path.dirname(run_id)
        csv_path = os.path.join(output_dir, "adjustments.csv")
        df.to_csv(csv_path, index=False)
        
        return csv_path
    
    def _get_suggested_action(self, record: Dict) -> str:
        """Determine suggested action based on status"""
        status = record['status']
        if status == ORPHAN:
            missing_systems = []
            if not record[CBS]: missing_systems.append(CBS.upper())
            if not record[SWITCH]: missing_systems.append(SWITCH.upper())
            if not record[NPCI]: missing_systems.append(NPCI.upper())
            return f'Investigate missing in {", ".join(missing_systems)}'
        elif status == PARTIAL_MATCH:
            missing_systems = []
            if not record[CBS]: missing_systems.append(CBS.upper())
            if not record[SWITCH]: missing_systems.append(SWITCH.upper())
            if not record[NPCI]: missing_systems.append(NPCI.upper())
            return f'Check missing system data in {", ".join(missing_systems)}'
        elif status == MISMATCH:
            return 'CRITICAL: All systems have record but amounts/dates differ - investigate discrepancy'
        elif status == PARTIAL_MISMATCH:
            return 'WARNING: 2 systems have record but amounts/dates differ - investigate discrepancy'
        elif status == FORCE_MATCHED:
            return 'Manual intervention completed - forced match'
        elif status == MATCHED:
            return 'No action needed - perfect match'
        else:
            return 'Unknown status - manual review required'