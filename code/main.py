import os
import sys
import pandas as pd
from data_loader import DataLoader
from ai_parser import AIParser
from state_builder import StateBuilder
from simulator import Simulator
from decision_engine import DecisionEngine

def main():
    mode = "full"
    if len(sys.argv) > 1 and sys.argv[1] == "--mode=sample":
        mode = "sample"
        
    print(f"Running in {mode} mode...")
    
    # 1. Init Pipeline
    dl = DataLoader(os.path.join(os.path.dirname(__file__), '..', 'dataset'), is_sample=(mode == "sample"))
    ai = AIParser()
    sb = StateBuilder(dl, ai)
    sim = Simulator(dl)
    engine = DecisionEngine(sim)
    
    results = []
    
    if dl.requests is None or dl.requests.empty:
        print("No requests found.")
        return
        
    total_reqs = len(dl.requests)
    print(f"Processing {total_reqs} requests...")
    
    # 2. Process each request
    for idx, req_row in dl.requests.iterrows():
        user_id = req_row['user_id']
        req_id = req_row['request_id']
        
        # Get state
        req_date_str = req_row['request_date'].strftime("%Y-%m-%d") if isinstance(req_row['request_date'], pd.Timestamp) else req_row['request_date']
        state = sb.get_user_state(user_id, req_date_str)
        
        if not state:
            # Fallback if profile not found
            results.append({
                "request_id": req_id,
                "amount_safe_to_pay": 0,
                "affordability_status": "not_affordable",
                "recommended_payment_method": "not_recommended",
                "payment_plan": "none",
                "earliest_date_for_full_payment": "",
                "spending_changes_needed": "none",
                "decision_explanation": "User profile not found."
            })
            continue
            
        # Evaluate
        decision = engine.evaluate_request(req_row, state)
        decision["request_id"] = req_id
        results.append(decision)
        
        if (idx + 1) % 10 == 0:
            print(f"Processed {idx + 1}/{total_reqs}")
            
    # 3. Output
    output_cols = [
        "request_id", "amount_safe_to_pay", "affordability_status", 
        "recommended_payment_method", "payment_plan", "earliest_date_for_full_payment", 
        "spending_changes_needed", "decision_explanation"
    ]
    
    df_out = pd.DataFrame(results)[output_cols]
    
    if mode == "full":
        out_path = os.path.join(os.path.dirname(__file__), '..', 'output.csv')
        df_out.to_csv(out_path, index=False)
        print(f"Saved {len(df_out)} predictions to {out_path}")
        
        # Write usage report
        usage = ai.usage_stats
        report_path = os.path.join(os.path.dirname(__file__), '..', 'evaluation', 'usage_report.md')
        
        total_toks = usage["total_tokens"]
        avg_toks = total_toks / total_reqs if total_reqs > 0 else 0
        
        cost = (usage["prompt_tokens"] / 1000000 * 0.150) + (usage["completion_tokens"] / 1000000 * 0.600)
        
        report_content = f"""# Token Usage Report

## Model Information
- Provider: OpenAI
- Model: gpt-4o-mini / gpt-4o

## Usage Summary
- Total model calls: {usage['calls']}
- Total input tokens: {usage['prompt_tokens']}
- Total output tokens: {usage['completion_tokens']}
- Total tokens: {total_toks}
- Average tokens per request: {avg_toks:.2f}
- Estimated total cost: ${cost:.4f}
- Estimated per-request cost: ${(cost/total_reqs if total_reqs>0 else 0):.4f}

## Breakdown
- Includes image OCR calls and message parsing calls.
"""
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            f.write(report_content)
        print(f"Saved usage report to {report_path}")
    else:
        out_path = os.path.join(os.path.dirname(__file__), '..', 'dataset', 'sample_predictions.csv')
        df_out.to_csv(out_path, index=False)
        print(f"Saved sample predictions to {out_path}")

if __name__ == "__main__":
    main()
