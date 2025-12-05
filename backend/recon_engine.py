import pandas as pd
import os
from typing import Dict, List, Tuple
import json
from datetime import datetime
from loguru import logger
from settlement_engine import SettlementEngine

class ReconciliationEngine:
    def __init__(self, output_dir: str = "./data/output"):
        self.output_dir = output_dir
        self.matched_records = []
        self.partial_match_records = []
        self.orphan_records = []
        self.exceptions = []
        self.settlement_engine = SettlementEngine(output_dir)
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataframe"""
        # Fill missing RRN with empty string
        if 'RRN' in df.columns:
            df['RRN'] = df['RRN'].fillna('').astype(str).str.strip()
        
        # Fill missing Amount with 0
        if 'Amount' in df.columns:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        
        # Fill missing Tran_Date with default date
        if 'Tran_Date' in df.columns:
            df['Tran_Date'] = df['Tran_Date'].fillna('1970-01-01').astype(str)
        
        # Fill missing Dr_Cr with empty string
        if 'Dr_Cr' in df.columns:
            df['Dr_Cr'] = df['Dr_Cr'].fillna('').astype(str)
        
        # Fill missing RC with empty string
        if 'RC' in df.columns:
            df['RC'] = df['RC'].fillna('').astype(str)
        
        # Fill missing Tran_Type with empty string
        if 'Tran_Type' in df.columns:
            df['Tran_Type'] = df['Tran_Type'].fillna('').astype(str)
        
        return df

    def reconcile(self, dataframes: List[pd.DataFrame]) -> Dict:
        """Main reconciliation logic - RRN + Amount + Date matching with comprehensive error handling"""

        logger.info(f"Starting reconciliation with {len(dataframes)} dataframes")

        # Clear previous counts for fresh run
        self.matched_records = []
        self.partial_match_records = []
        self.orphan_records = []
        self.exceptions = []

        try:
            # Phase 1: Data preprocessing with validation
            processed_dataframes = []
            for i, df in enumerate(dataframes):
                try:
                    # Validate dataframe structure
                    required_cols = ['RRN', 'Amount', 'Tran_Date', 'Source']
                    missing_cols = [col for col in required_cols if col not in df.columns]
                    if missing_cols:
                        raise ValueError(f"Dataframe {i} missing required columns: {missing_cols}")

                    # Handle missing values
                    df = self._handle_missing_values(df)

                    # Remove rows where RRN is empty (can't match without RRN)
                    original_count = len(df)
                    df = df[df['RRN'] != ''].reset_index(drop=True)
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

            # Phase 2: Data combination with validation
            try:
                combined_df = pd.concat(processed_dataframes, ignore_index=True)
                logger.info(f"Combined dataframe has {len(combined_df)} total records")

                # Final cleanup - remove any remaining rows with empty RRN
                original_count = len(combined_df)
                combined_df = combined_df[combined_df['RRN'] != ''].reset_index(drop=True)
                removed_count = original_count - len(combined_df)

                if removed_count > 0:
                    logger.warning(f"Removed {removed_count} additional rows with empty RRN during combination")

                if combined_df.empty:
                    logger.error("Combined dataframe is empty after final cleanup")
                    raise ValueError("No valid transaction records found after data combination")

            except Exception as combine_error:
                logger.error(f"Error combining dataframes: {str(combine_error)}")
                raise ValueError(f"Data combination failed: {str(combine_error)}")

            # Phase 3: Reconciliation logic with error handling
            results = {}
            try:
                # Group by RRN
                grouped = combined_df.groupby('RRN')
                total_groups = len(grouped)

                logger.info(f"Processing {total_groups} unique RRN groups")

                for rrn, group in grouped:
                    try:
                        # Get unique sources for this RRN
                        sources = set(group['Source'].tolist())

                        # Create record structure
                        record = {
                            'cbs': None,
                            'switch': None,
                            'npci': None,
                            'status': 'UNKNOWN'
                        }

                        # Populate data by source
                        for _, row in group.iterrows():
                            source = row['Source'].lower()
                            if source in ['cbs', 'switch', 'npci']:
                                record[source] = {
                                    'amount': row['Amount'],
                                    'date': row['Tran_Date'],
                                    'dr_cr': row.get('Dr_Cr', ''),
                                    'rc': row.get('RC', ''),
                                    'tran_type': row.get('Tran_Type', '')
                                }

                        # Extract amounts and dates from the populated records
                        amounts = []
                        dates = []

                        if record['cbs']:
                            amounts.append(record['cbs']['amount'])
                            dates.append(record['cbs']['date'])
                        if record['switch']:
                            amounts.append(record['switch']['amount'])
                            dates.append(record['switch']['date'])
                        if record['npci']:
                            amounts.append(record['npci']['amount'])
                            dates.append(record['npci']['date'])

                        # Create sets for comparison (only from actual records, not duplicates)
                        amount_set = set(amounts)
                        date_set = set(dates)

                        # Determine status based on presence in systems AND data consistency
                        num_sources = len(sources)
                        amounts_match = len(amount_set) == 1
                        dates_match = len(date_set) == 1

                        if num_sources == 3:
                            # All 3 systems have the RRN
                            if amounts_match and dates_match:
                                # Perfect match: all 3 systems agree on amount and date
                                record['status'] = 'MATCHED'
                                self.matched_records.append(rrn)
                            else:
                                # Mismatch: all 3 systems have it but amounts/dates differ
                                record['status'] = 'MISMATCH'
                                self.exceptions.append(rrn)
                        elif num_sources == 2:
                            # 2 systems have the RRN
                            if amounts_match and dates_match:
                                # Partial match with consistent data
                                record['status'] = 'PARTIAL_MATCH'
                                self.partial_match_records.append(rrn)
                            else:
                                # Partial match but data doesn't agree
                                record['status'] = 'PARTIAL_MISMATCH'
                                self.exceptions.append(rrn)
                        elif num_sources == 1:
                            # Only 1 system has the RRN
                            record['status'] = 'ORPHAN'
                            self.orphan_records.append(rrn)
                        else:
                            # This shouldn't happen, but handle it
                            record['status'] = 'UNKNOWN'
                            self.exceptions.append(rrn)

                        results[rrn] = record

                    except Exception as rrn_error:
                        logger.error(f"Error processing RRN {rrn}: {str(rrn_error)}")
                        # Add to exceptions and continue processing other RRNs
                        self.exceptions.append(rrn)
                        results[rrn] = {
                            'cbs': None, 'switch': None, 'npci': None,
                            'status': 'PROCESSING_ERROR',
                            'error': str(rrn_error)
                        }

            except Exception as logic_error:
                logger.error(f"Critical error in reconciliation logic: {str(logic_error)}")
                raise ValueError(f"Reconciliation logic failed: {str(logic_error)}")

            # Phase 4: Final validation and summary
            # Combine unmatched records (partial matches + orphans)
            self.unmatched_records = self.partial_match_records + self.orphan_records

            # Log summary
            logger.info(f"Reconciliation completed: {len(results)} total RRNs processed")
            logger.info(f"Results: {len(self.matched_records)} matched, {len(self.partial_match_records)} partial, {len(self.orphan_records)} orphan, {len(self.exceptions)} exceptions")

            if not results:
                logger.warning("Reconciliation completed but no results generated")
                raise ValueError("Reconciliation completed but no transaction records were processed")

            return results

        except Exception as e:
            logger.error(f"Reconciliation failed with error: {str(e)}")
            # Re-raise with context
            raise ValueError(f"Reconciliation process failed: {str(e)}")
    
    def force_match_rrn(self, rrn: str, source1: str, source2: str, results: Dict):
        """Force match a specific RRN between two sources"""
        if rrn in results:
            # Update status to force matched
            results[rrn]['status'] = 'FORCE_MATCHED'
            
            # Sync amounts between the two sources
            if source1 in results[rrn] and source2 in results[rrn]:
                # Copy data from source1 to source2 (or vice versa)
                results[rrn][source2] = results[rrn][source1]
        
        return results
    
    def generate_report(self, results: Dict, run_id: str) -> str:
        """Generate human-readable report.txt with detailed breakdown"""
        report_content = f"""BANK RECONCILIATION REPORT
Run ID: {run_id}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
Total RRNs processed: {len(results)}
Matched records: {len(self.matched_records)} (All 3 systems agree)
Partial Match records: {len(self.partial_match_records)} (2 systems match, 1 missing)
Orphan records: {len(self.orphan_records)} (Only in 1 system)
Exceptions: {len(self.exceptions)} (Data mismatches or inconsistencies)

Unmatched records: {len(self.unmatched_records)} (Partial + Orphan)

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
                'RRN': rrn,
                'Status': record['status'],
                'CBS_Amount': record['cbs']['amount'] if record['cbs'] else '',
                'Switch_Amount': record['switch']['amount'] if record['switch'] else '',
                'NPCI_Amount': record['npci']['amount'] if record['npci'] else '',
                'CBS_Date': record['cbs']['date'] if record['cbs'] else '',
                'Switch_Date': record['switch']['date'] if record['switch'] else '',
                'NPCI_Date': record['npci']['date'] if record['npci'] else '',
                'CBS_Source': 'X' if record['cbs'] else '',
                'Switch_Source': 'X' if record['switch'] else '',
                'NPCI_Source': 'X' if record['npci'] else '',
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
        if status == 'ORPHAN':
            missing_systems = []
            if not record['cbs']: missing_systems.append('CBS')
            if not record['switch']: missing_systems.append('Switch')
            if not record['npci']: missing_systems.append('NPCI')
            return f'Investigate missing in {", ".join(missing_systems)}'
        elif status == 'PARTIAL_MATCH':
            missing_systems = []
            if not record['cbs']: missing_systems.append('CBS')
            if not record['switch']: missing_systems.append('Switch')
            if not record['npci']: missing_systems.append('NPCI')
            return f'Check missing system data in {", ".join(missing_systems)}'
        elif status == 'MISMATCH':
            return 'CRITICAL: All systems have record but amounts/dates differ - investigate discrepancy'
        elif status == 'PARTIAL_MISMATCH':
            return 'WARNING: 2 systems have record but amounts/dates differ - investigate discrepancy'
        elif status == 'FORCE_MATCHED':
            return 'Manual intervention completed - forced match'
        elif status == 'MATCHED':
            return 'No action needed - perfect match'
        else:
            return 'Unknown status - manual review required'