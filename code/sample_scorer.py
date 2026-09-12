import pandas as pd
import sys
import os

def score_samples(preds_csv, truths_csv):
    try:
        preds = pd.read_csv(preds_csv)
        truths = pd.read_csv(truths_csv)
    except Exception as e:
        print(f"Error reading CSVs: {e}")
        return
        
    merged = preds.merge(truths, on='request_id', suffixes=('_pred', '_truth'))
    
    if merged.empty:
        print("No overlapping request_ids found between predictions and ground truth.")
        return
        
    total = len(merged)
    status_match = 0
    method_match = 0
    
    for _, row in merged.iterrows():
        s_p, s_t = row['affordability_status_pred'], row['affordability_status_truth']
        m_p, m_t = row['recommended_payment_method_pred'], row['recommended_payment_method_truth']
        
        if s_p == s_t: status_match += 1
        if m_p == m_t: method_match += 1
        
        if s_p != s_t or m_p != m_t:
            print(f"{row['request_id']}:")
            if s_p != s_t:
                print(f"  Status mismatch: Pred={s_p}, Truth={s_t}")
            if m_p != m_t:
                print(f"  Method mismatch: Pred={m_p}, Truth={m_t}")
            print(f"  Amount: Pred={row['amount_safe_to_pay_pred']}, Truth={row['amount_safe_to_pay_truth']}")
            print()
            
    print(f"Sample Accuracy ({total} requests):")
    print(f"  Status: {status_match}/{total} ({status_match/total:.1%})")
    print(f"  Method: {method_match}/{total} ({method_match/total:.1%})")

if __name__ == '__main__':
    args = sys.argv[1:]
    preds = args[0] if args else '../dataset/sample_predictions.csv'
    truths = args[1] if len(args) > 1 else '../dataset/sample_requests.csv'
    score_samples(os.path.join(os.path.dirname(__file__), preds), 
                  os.path.join(os.path.dirname(__file__), truths))
