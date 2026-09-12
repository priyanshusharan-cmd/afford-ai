import pandas as pd
import sys
import os

def validate_output(output_csv, requests_csv):
    try:
        out_df = pd.read_csv(output_csv)
        req_df = pd.read_csv(requests_csv)
    except Exception as e:
        print(f"Error reading CSVs: {e}")
        return False
        
    errors = []
    
    # 1. Row count matches
    if len(out_df) != len(req_df):
        errors.append(f"Row count mismatch: output {len(out_df)} vs requests {len(req_df)}")
        
    # 2. Columns
    expected_cols = [
        "request_id", "amount_safe_to_pay", "affordability_status", 
        "recommended_payment_method", "payment_plan", "earliest_date_for_full_payment", 
        "spending_changes_needed", "decision_explanation"
    ]
    if list(out_df.columns) != expected_cols:
        errors.append(f"Column mismatch. Expected: {expected_cols}")
        
    # 3. 0 <= amount <= req
    merged = out_df.merge(req_df[['request_id', 'requested_amount']], on='request_id', how='left')
    invalid_amts = merged[(merged['amount_safe_to_pay'] < 0) | (merged['amount_safe_to_pay'] > merged['requested_amount'])]
    if not invalid_amts.empty:
        errors.append(f"{len(invalid_amts)} rows have invalid amount_safe_to_pay bounds.")
        
    # 4. Enums
    valid_status = ["affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"]
    valid_method = ["full_payment", "partial_payment", "installments", "wait", "not_recommended"]
    
    invalid_s = out_df[~out_df['affordability_status'].isin(valid_status)]
    if not invalid_s.empty:
        errors.append(f"Invalid status values: {invalid_s['affordability_status'].unique()}")
        
    invalid_m = out_df[~out_df['recommended_payment_method'].isin(valid_method)]
    if not invalid_m.empty:
        errors.append(f"Invalid method values: {invalid_m['recommended_payment_method'].unique()}")
        
    # 9. affordable_now
    now_rows = out_df[out_df['affordability_status'] == 'affordable_now']
    now_merged = now_rows.merge(req_df[['request_id', 'request_date']], on='request_id')
    bad_now = now_merged[now_merged['earliest_date_for_full_payment'].astype(str) != now_merged['request_date'].astype(str)]
    if not bad_now.empty:
        errors.append(f"{len(bad_now)} affordable_now rows have wrong earliest_date.")
        
    # 10. not_affordable
    not_aff = out_df[out_df['affordability_status'] == 'not_affordable']
    bad_not = not_aff[not_aff['earliest_date_for_full_payment'].notna()]
    if not bad_not.empty:
        errors.append(f"{len(bad_not)} not_affordable rows have non-empty earliest_date.")
        
    if not errors:
        print("✅ Output passed validation constraints!")
        return True
    else:
        print("❌ Validation Errors:")
        for e in errors:
            print(f"  - {e}")
        return False

if __name__ == '__main__':
    args = sys.argv[1:]
    out = args[0] if args else '../output.csv'
    req = args[1] if len(args) > 1 else '../dataset/requests.csv'
    validate_output(os.path.join(os.path.dirname(__file__), out), 
                    os.path.join(os.path.dirname(__file__), req))
