import pandas as pd
import os
from typing import Dict, List, Tuple
import json
from datetime import datetime
from loguru import logger
from settlement_engine import SettlementEngine
from config import UPLOAD_DIR as CFG_UPLOAD_DIR

# Constants
CBS = 'cbs'
SWITCH = 'switch'
NPCI = 'npci'
NTSL = 'ntsl'
SOURCES = [CBS, SWITCH, NPCI, NTSL]

RRN = 'RRN'
AMOUNT = 'Amount'
TRAN_DATE = 'Tran_Date'
SOURCE = 'Source'
DR_CR = 'Dr_Cr'
RC = 'RC'
TRAN_TYPE = 'Tran_Type'
UPI_ID = 'UPI_Tran_ID'

MATCHED = 'MATCHED'
MISMATCH = 'MISMATCH'
PARTIAL_MATCH = 'PARTIAL_MATCH'
PARTIAL_MISMATCH = 'PARTIAL_MISMATCH'
ORPHAN = 'ORPHAN'
UNKNOWN = 'UNKNOWN'
FORCE_MATCHED = 'FORCE_MATCHED'
PROCESSING_ERROR = 'PROCESSING_ERROR'
HANGING = 'HANGING'
DUPLICATE = 'DUPLICATE'

class ReconciliationEngine:
    def __init__(self, output_dir: str = "./data/output"):
        self.output_dir = output_dir
        self.matched_records = []
        self.partial_match_records = []
        self.orphan_records = []
        self.exceptions = []
        self.unmatched_records = []
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
        self.unmatched_records = []

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
            # First: attempt matching by UPI_Tran_ID when RRN missing
            if UPI_ID in combined_df.columns:
                upi_df = combined_df[combined_df[UPI_ID].notnull() & (combined_df[RRN].isnull() | (combined_df[RRN] == ''))]
                if not upi_df.empty:
                    upi_grouped = upi_df.groupby(UPI_ID)
                    for upi, ugroup in upi_grouped:
                        try:
                            key = f"UPI_{upi}"
                            record = self._create_record_structure()
                            self._populate_record_by_source(record, ugroup)
                            # simple matching check
                            amounts = [record[s]['amount'] for s in SOURCES if record[s]]
                            dates = [record[s]['date'] for s in SOURCES if record[s]]
                            if len(set(amounts)) == 1 and len(set(dates)) == 1 and len([s for s in SOURCES if record[s]]) >= 2:
                                record['status'] = MATCHED
                                self.matched_records.append(key)
                            else:
                                record['status'] = PARTIAL_MATCH
                                self.partial_match_records.append(key)
                            results[key] = record
                        except Exception as e:
                            logger.warning(f"UPI grouping failed for {upi}: {e}")

            # detect duplicates per RRN within each source
            dup_rrns = []
            for src in [CBS, SWITCH, NPCI]:
                src_df = combined_df[combined_df[SOURCE].str.lower() == src]
                counts = src_df[RRN].value_counts()
                dups = counts[counts > 1].index.tolist()
                dup_rrns.extend(dups)

            grouped = combined_df.groupby(RRN)
            total_groups = len(grouped)
            logger.info(f"Processing {total_groups} unique RRN groups")

            for rrn, group in grouped:
                try:
                    sources = set(group[SOURCE].tolist())
                    record = self._create_record_structure()

                    self._populate_record_by_source(record, group)
                    # Cut-off handling: if a declined txn has a reversal present (RC startswith 'RB'),
                    # mark as HANGING (declined with reversal in next/other cycle)
                    try:
                        if self._detect_cutoff_reversal(group, record):
                            record['status'] = HANGING
                            record['hanging_reason'] = 'declined_with_reversal'
                            if 'hanging_list' not in results:
                                results['hanging_list'] = []
                            results['hanging_list'].append(rrn)
                            results[rrn] = record
                            continue
                    except Exception:
                        pass
                    # Duplicate detection: same RRN multiple times in same source
                    if rrn in dup_rrns:
                        record['status'] = DUPLICATE
                        self.exceptions.append(rrn)
                        results[rrn] = record
                        continue

                    # Self-reversal: debit + credit same amount and date within any source
                    # Look for pairs in group
                    if DR_CR in group.columns:
                        # Normalize values
                        try:
                            grp = group.copy()
                            grp['amount_num'] = pd.to_numeric(grp[AMOUNT], errors='coerce').fillna(0)
                            grp['drcr'] = grp[DR_CR].astype(str).str.upper()
                            # find matching debit-credit pairs
                            for _, r1 in grp.iterrows():
                                for _, r2 in grp.iterrows():
                                    if r1[RRN] == r2[RRN] and r1['amount_num'] == r2['amount_num'] and r1['drcr'] != r2['drcr'] and r1[TRAN_DATE] == r2[TRAN_DATE]:
                                        record['status'] = MATCHED
                                        self.matched_records.append(rrn)
                                        results[rrn] = record
                                        raise StopIteration
                        except StopIteration:
                            continue

                    self._classify_record(rrn, record, sources)

                    # Hanging detection: CBS + SWITCH present, NPCI missing
                    if record['status'] == ORPHAN and record.get(CBS) and record.get(SWITCH) and not record.get(NPCI):
                        record['status'] = HANGING
                        # add a hanging list for report
                        if 'hanging_list' not in results:
                            results['hanging_list'] = []
                        results['hanging_list'].append(rrn)

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
            NTSL: None,
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

    def _detect_cutoff_reversal(self, group: pd.DataFrame, record: Dict) -> bool:
        """Detect declined transactions that have a reversal present (RC starting with 'RB').
        If found, returns True to indicate hanging/cutoff condition.
        Operates on the grouped DataFrame for a single RRN."""
        try:
            # Normalize RC values
            rc_vals = group[RC].astype(str).str.strip().str.upper().fillna('') if RC in group.columns else []
            # Any reversal markers
            has_reversal = any(str(r).upper().startswith('RB') for r in rc_vals)
            # Any declined (non-success) markers
            success_markers = {'00', '0', 'SUCCESS', 'S'}
            has_decline = any((str(r) not in success_markers and str(r) != '') for r in rc_vals)

            # If both decline and reversal present, treat as cut-off hanging
            return has_decline and has_reversal
        except Exception:
            return False

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

        # TCC rules: if NPCI RC startswith 'RB'
        try:
            npc = record.get(NPCI)
            cbs = record.get(CBS)
            if npc and str(npc.get('rc','')).upper().startswith('RB'):
                if cbs and cbs.get('dr_cr','').upper().startswith('C'):
                    record['tcc'] = 'TCC_102'
                else:
                    record['tcc'] = 'TCC_103'
                    # mark as needs TTUM
                    record['needs_ttum'] = True
        except Exception:
            pass

        # NTSL Settlement: if NTSL exists and amount equals CBS/GL amount, mark as settlement matched
        try:
            ntsl_rec = record.get(NTSL)
            if ntsl_rec:
                ntsl_amt = float(str(ntsl_rec.get('amount') or 0) or 0)
                # Prefer CBS as GL-equivalent; fallback to switch or npci
                gl_amt = None
                if cbs and cbs.get('amount') is not None:
                    gl_amt = float(cbs.get('amount') or 0)
                elif record.get(SWITCH) and record.get(SWITCH).get('amount') is not None:
                    gl_amt = float(record.get(SWITCH).get('amount') or 0)
                elif record.get(NPCI) and record.get(NPCI).get('amount') is not None:
                    gl_amt = float(record.get(NPCI).get('amount') or 0)

                if gl_amt is not None and abs(ntsl_amt - gl_amt) < 0.01:
                    # Treat as matched settlement
                    record['status'] = MATCHED
                    record['settlement_matched'] = True
                    if rrn not in self.matched_records:
                        self.matched_records.append(rrn)
        except Exception:
            pass

        # Failed txn handling: NPCI failed + CBS success -> Exception
        try:
            if npc:
                rc_val = str(npc.get('rc','')).upper()
                # treat non-success as failure (simple heuristics)
                if rc_val not in ['00','0','SUCCESS','S']:
                    if cbs and str(cbs.get('rc','')).upper() in ['00','0','SUCCESS','S']:
                        record['status'] = 'EXCEPTION'
                        self.exceptions.append(rrn)
        except Exception:
            pass
            
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

        # Populate unmatched_records as combination of partial_match_records and orphan_records
        self.unmatched_records = self.partial_match_records + self.orphan_records

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
    
    def generate_summary_json(self, results: Dict, run_folder: str) -> str:
        """Generate a summary.json file with key reconciliation metrics."""
        summary_data = {
            'run_id': os.path.basename(run_folder),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'totals': {
                'count': len([r for r in results.values() if isinstance(r, dict)]),
                'amount': sum((rec.get(CBS, {}).get('amount') if isinstance(rec, dict) and rec.get(CBS) else (rec.get(SWITCH, {}) or {}).get('amount', 0)) for rec in results.values() if isinstance(rec, dict))
            },
            'matched': {
                'count': len(self.matched_records),
                'amount': sum(results[rrn][CBS]['amount'] for rrn in self.matched_records if rrn in results and isinstance(results[rrn], dict) and results[rrn].get(CBS))
            },
            'unmatched': {
                'count': len(self.unmatched_records),
                'amount': sum((results[rrn][CBS]['amount'] if rrn in self.unmatched_records and rrn in results and isinstance(results[rrn], dict) and results[rrn].get(CBS) else (results[rrn].get(SWITCH, {}) or {}).get('amount', 0)) for rrn in self.unmatched_records if rrn in results and isinstance(results[rrn], dict))
            },
            'hanging': { # Placeholder for future logic
                'count': 0,
                'amount': 0.0
            },
            'exceptions': {
                'count': len(self.exceptions),
                'amount': sum((results[rrn][CBS]['amount'] if rrn in self.exceptions and rrn in results and isinstance(results[rrn], dict) and results[rrn].get(CBS) else (results[rrn].get(SWITCH, {}) or {}).get('amount', 0)) for rrn in self.exceptions if rrn in results and isinstance(results[rrn], dict))
            }
        }
        
        output_path = os.path.join(run_folder, "summary.json")
        with open(output_path, 'w') as f:
            json.dump(summary_data, f, indent=4)
        
        logger.info(f"Generated summary.json at {output_path}")
        return output_path

    def generate_report(self, results: Dict, run_folder: str, run_id: str = None) -> str:
        """Generate human-readable report.txt and summary.json"""
        # Also generate the JSON summary
        self.generate_summary_json(results, run_folder)
        
        unmatched_records = self.partial_match_records + self.orphan_records
        report_content = f"""BANK RECONCILIATION REPORT
Run ID: {os.path.basename(run_folder)}
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
        
        report_path = os.path.join(run_folder, "report.txt")
        with open(report_path, 'w') as f:
            f.write(report_content)
        # Save full recon output for enquiries and rollback
        try:
            recon_out_path = os.path.join(run_folder, 'recon_output.json')
            with open(recon_out_path, 'w') as rf:
                json.dump(results, rf, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write recon_output.json: {e}")

        # Pairwise matched reports (GL-Switch, Switch-NPCI, GL-NPCI)
        try:
            reports_dir = os.path.join(run_folder, 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            import csv

            # prepare rows for each pair
            rows_gl_switch = []
            rows_switch_npci = []
            rows_gl_npci = []

            for rrn, rec in results.items():
                if not isinstance(rec, dict):
                    continue
                cbs = rec.get(CBS)
                switch = rec.get(SWITCH)
                npci = rec.get(NPCI)
                ntsl = rec.get(NTSL)

                rows_gl_switch.append([rrn, cbs.get('amount') if cbs else '', switch.get('amount') if switch else '', rec.get('status', '')])
                rows_switch_npci.append([rrn, switch.get('amount') if switch else '', npci.get('amount') if npci else '', rec.get('status', '')])
                rows_gl_npci.append([rrn, cbs.get('amount') if cbs else '', npci.get('amount') if npci else '', rec.get('status', '')])

            # write CSVs
            with open(os.path.join(reports_dir, 'gl_switch.csv'), 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(['RRN', 'CBS_Amount', 'SWITCH_Amount', 'Status'])
                w.writerows(rows_gl_switch)

            with open(os.path.join(reports_dir, 'switch_npci.csv'), 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(['RRN', 'SWITCH_Amount', 'NPCI_Amount', 'Status'])
                w.writerows(rows_switch_npci)

            with open(os.path.join(reports_dir, 'gl_npci.csv'), 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(['RRN', 'CBS_Amount', 'NPCI_Amount', 'Status'])
                w.writerows(rows_gl_npci)
        except Exception as e:
            logger.warning(f"Failed to generate pairwise reports: {e}")

        # Generate source-wise listings and per-upload-file listings
        try:
            # Aggregate source-wise from results
            for source in [CBS.upper(), SWITCH.upper(), NPCI.upper()]:
                rows = []
                for rrn, rec in results.items():
                    if not isinstance(rec, dict):
                        continue
                    src_rec = rec.get(source.lower())
                    if src_rec:
                        rows.append([
                            rrn,
                            src_rec.get('amount',''),
                            src_rec.get('date',''),
                            src_rec.get('dr_cr',''),
                            src_rec.get('rc',''),
                            src_rec.get('tran_type',''),
                            rec.get('status','')
                        ])
                if rows:
                    with open(os.path.join(reports_dir, f"{source.lower()}_listing.csv"), 'w', newline='') as sf:
                        sw = csv.writer(sf)
                        sw.writerow(['RRN','Amount','Tran_Date','Dr_Cr','RC','Tran_Type','Status'])
                        sw.writerows(rows)

            # Per-file listing: read uploaded CSV/XLSX files found under run_folder
            for root, dirs, files in os.walk(run_folder):
                for fname in files:
                    if not fname.lower().endswith(('.csv', '.xlsx', '.xls')):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        df = pd.read_csv(fpath) if fname.lower().endswith('.csv') else pd.read_excel(fpath)
                        df = self._handle_missing_values(self._smart_map_columns(df))
                        # add source from filename
                        src = 'OTHER'
                        fname_l = fname.lower()
                        if 'cbs' in fname_l:
                            src = 'CBS'
                        elif 'switch' in fname_l:
                            src = 'SWITCH'
                        elif 'npci' in fname_l or 'npc' in fname_l:
                            src = 'NPCI'
                        # direction inference
                        direction = ''
                        if 'inward' in fname_l:
                            direction = 'INWARD'
                        elif 'outward' in fname_l:
                            direction = 'OUTWARD'

                        out_rows = []
                        for _, r in df.iterrows():
                            out_rows.append([
                                r.get(RRN,''), r.get(AMOUNT,''), r.get(TRAN_DATE,''), r.get(DR_CR,''), r.get(RC,''), r.get(TRAN_TYPE,''), src, direction
                            ])
                        if out_rows:
                            out_fn = os.path.join(reports_dir, f"file_listing_{os.path.splitext(fname)[0]}.csv")
                            with open(out_fn, 'w', newline='') as of:
                                w = csv.writer(of)
                                w.writerow(['RRN','Amount','Tran_Date','Dr_Cr','RC','Tran_Type','Source','Direction'])
                                w.writerows(out_rows)
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Failed to generate source/file listings: {e}")

        # Cross-run cut-off detection: if this run has declines for an RRN and the next chronological run
        # contains a reversal (RC starts with 'RB'), flag the current RRN as HANGING.
        try:
            if run_id:
                runs = [d for d in os.listdir(CFG_UPLOAD_DIR) if d.startswith('RUN_')]
                runs = sorted(runs)
                if run_id in runs:
                    idx = runs.index(run_id)
                    next_idx = idx + 1
                    if next_idx < len(runs):
                        next_run = runs[next_idx]
                        next_run_folder = os.path.join(CFG_UPLOAD_DIR, next_run)
                        next_recon = os.path.join(next_run_folder, 'recon_output.json')
                        if os.path.exists(next_recon):
                            try:
                                with open(next_recon, 'r') as nf:
                                    next_data = json.load(nf)
                                # determine reversal RRNs in next run
                                rev_rrns = set()
                                if isinstance(next_data, dict) and not next_data.get('matched') and not next_data.get('unmatched'):
                                    for k, v in next_data.items():
                                        if isinstance(v, dict):
                                            npci = v.get(NPCI)
                                            if npci and str(npci.get('rc','')).upper().startswith('RB'):
                                                rev_rrns.add(k)
                                else:
                                    for rec in next_data.get('matched', []) + next_data.get('unmatched', []):
                                        if isinstance(rec, dict) and rec.get('NPCI') and str(rec.get('NPCI').get('rc','')).upper().startswith('RB'):
                                            rev_rrns.add(rec.get('rrn') or rec.get('RRN'))

                                # flag current results
                                for rrn in list(results.keys()):
                                    if rrn in rev_rrns:
                                        rec = results.get(rrn)
                                        if rec:
                                            rec['status'] = HANGING
                                            rec['hanging_reason'] = 'declined_then_reversed_next_cycle'
                                            if 'hanging_list' not in results:
                                                results['hanging_list'] = []
                                            if rrn not in results['hanging_list']:
                                                results['hanging_list'].append(rrn)
                            except Exception:
                                pass
        except Exception:
            pass
        # Hanging CSV logic: write current pending hanging state, and if present in previous two runs, mark as final hanging
        hanging_rrns = results.get('hanging_list', [])
        try:
            import csv
            # write hanging_state.json in current run folder for future runs to reference
            state_path = os.path.join(run_folder, 'hanging_state.json')
            try:
                with open(state_path, 'w') as sf:
                    json.dump({'hanging': hanging_rrns, 'generated_at': datetime.now().isoformat()}, sf, indent=2)
            except Exception:
                pass

            # If run_id provided, check previous two runs for hanging_state occurrences
            final_hangings = []
            if run_id:
                # locate runs sorted
                root_upload = os.path.dirname(os.path.dirname(run_folder)) if os.path.basename(run_folder).startswith('cycle_') else os.path.join(os.path.dirname(run_folder))
                # Better: list runs from UPLOAD_DIR
                from config import UPLOAD_DIR as CFG_UPLOAD
                runs = [d for d in os.listdir(CFG_UPLOAD) if d.startswith('RUN_')]
                runs = sorted(runs)
                if run_id in runs:
                    idx = runs.index(run_id)
                    prev_runs = []
                    # get previous two runs indices
                    if idx-1 >= 0:
                        prev_runs.append(runs[idx-1])
                    if idx-2 >= 0:
                        prev_runs.append(runs[idx-2])

                    # count how many previous runs had the rrn in hanging_state
                    for rrn in hanging_rrns:
                        count = 0
                        for pr in prev_runs:
                            pr_state = os.path.join(CFG_UPLOAD, pr, 'hanging_state.json')
                            if os.path.exists(pr_state):
                                try:
                                    with open(pr_state, 'r') as pf:
                                        data = json.load(pf)
                                    if rrn in data.get('hanging', []):
                                        count += 1
                                except Exception:
                                    pass
                        # if found in both previous runs (count==2) then mark as final hanging
                        if count >= 2:
                            final_hangings.append(rrn)

            # write final hanging.csv for those meeting the wait condition
            if final_hangings:
                try:
                    hanging_path = os.path.join(run_folder, 'hanging.csv')
                    with open(hanging_path, 'w', newline='') as hf:
                        writer = csv.writer(hf)
                        writer.writerow(['RRN', 'Reason'])
                        for r in final_hangings:
                            writer.writerow([r, 'CBS+Switch present, NPCI missing (waited 2 cycles)'])
                except Exception as e:
                    logger.warning(f"Failed to write hanging.csv: {e}")
        except Exception as e:
            logger.warning(f"Hanging processing failed: {e}")

        return report_path

    def generate_unmatched_ageing(self, results: Dict, run_folder: str) -> str:
        """Generate unmatched.csv with ageing buckets (0-7,8-30,>30)"""
        import csv
        from datetime import datetime

        unmatched = self.partial_match_records + self.orphan_records
        if not unmatched:
            return ''

        path = os.path.join(run_folder, 'unmatched_ageing.csv')
        try:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['RRN', 'Amount', 'Tran_Date', 'AgeDays', 'Bucket', 'Status'])
                for rrn in unmatched:
                    rec = results.get(rrn, {})
                    # pick a date from available sources
                    date_str = ''
                    amount = ''
                    for s in [CBS, SWITCH, NPCI]:
                        if rec.get(s):
                            date_str = rec[s].get('date','')
                            amount = rec[s].get('amount','')
                            break
                    try:
                        if date_str:
                            dt = datetime.fromisoformat(date_str)
                        else:
                            dt = datetime.now()
                        age = (datetime.now() - dt).days
                    except Exception:
                        age = 0
                    if age <= 7:
                        bucket = '0-7'
                    elif age <= 30:
                        bucket = '8-30'
                    else:
                        bucket = '>30'
                    writer.writerow([rrn, amount, date_str, age, bucket, rec.get('status','')])
        except Exception as e:
            logger.warning(f"Failed to write unmatched_ageing.csv: {e}")
            return ''
        return path
    
    def generate_adjustments_csv(self, results: Dict, run_folder: str) -> str:
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
        csv_path = os.path.join(run_folder, "adjustments.csv")
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