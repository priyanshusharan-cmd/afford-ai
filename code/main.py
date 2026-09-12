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

    # --------------------------------------------------------------
    # 1. INITIALIZE PIPELINE
    # --------------------------------------------------------------

    dataset_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "dataset"
    )

    dl = DataLoader(
        dataset_path,
        is_sample=(mode == "sample")
    )

    ai = AIParser()

    sb = StateBuilder(
        dl,
        ai
    )

    sim = Simulator(dl)

    engine = DecisionEngine(sim)

    results = []

    # --------------------------------------------------------------
    # 2. VALIDATE REQUEST DATA
    # --------------------------------------------------------------

    if dl.requests is None or dl.requests.empty:
        print("No requests found.")
        return

    total_reqs = len(dl.requests)

    print(
        f"Processing {total_reqs} requests..."
    )

    # --------------------------------------------------------------
    # 3. PROCESS REQUESTS
    # --------------------------------------------------------------

    for idx, req_row in dl.requests.iterrows():

        user_id = req_row["user_id"]
        req_id = req_row["request_id"]

        # Convert request date to YYYY-MM-DD.
        request_date = req_row["request_date"]

        if isinstance(request_date, pd.Timestamp):
            req_date_str = request_date.strftime(
                "%Y-%m-%d"
            )
        else:
            req_date_str = str(request_date)

        # ----------------------------------------------------------
        # Build canonical financial state.
        # ----------------------------------------------------------

        state = sb.get_user_state(
            user_id,
            req_date_str
        )

        # ----------------------------------------------------------
        # Missing profile fallback.
        # ----------------------------------------------------------

        if not state:
            results.append(
                {
                    "request_id": req_id,
                    "amount_safe_to_pay": 0,
                    "affordability_status": "not_affordable",
                    "recommended_payment_method": "not_recommended",
                    "payment_plan": "none",
                    "earliest_date_for_full_payment": "",
                    "spending_changes_needed": "none",
                    "decision_explanation": (
                        "User profile not found."
                    )
                }
            )

            continue

        # ----------------------------------------------------------
        # Evaluate affordability.
        # ----------------------------------------------------------

        try:
            decision = engine.evaluate_request(
                req_row,
                state
            )

            decision["request_id"] = req_id

            results.append(decision)

        except Exception as e:
            print(
                f"ERROR processing {req_id}: {e}"
            )

            # Safe failure: do not claim affordability if the
            # decision engine fails.
            results.append(
                {
                    "request_id": req_id,
                    "amount_safe_to_pay": 0,
                    "affordability_status": "not_affordable",
                    "recommended_payment_method": "not_recommended",
                    "payment_plan": "none",
                    "earliest_date_for_full_payment": "",
                    "spending_changes_needed": "none",
                    "decision_explanation": (
                        "Unable to safely evaluate this request."
                    )
                }
            )

        # ----------------------------------------------------------
        # Progress reporting.
        # ----------------------------------------------------------

        if (idx + 1) % 10 == 0:
            print(
                f"Processed {idx + 1}/{total_reqs}"
            )

    # --------------------------------------------------------------
    # 4. BUILD OUTPUT
    # --------------------------------------------------------------

    output_cols = [
        "request_id",
        "amount_safe_to_pay",
        "affordability_status",
        "recommended_payment_method",
        "payment_plan",
        "earliest_date_for_full_payment",
        "spending_changes_needed",
        "decision_explanation"
    ]

    df_out = pd.DataFrame(results)

    # Make sure all required columns exist.
    for column in output_cols:
        if column not in df_out.columns:
            df_out[column] = ""

    df_out = df_out[output_cols]

    # --------------------------------------------------------------
    # 5. FULL RUN
    # --------------------------------------------------------------

    if mode == "full":

        out_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "output.csv"
        )

        df_out.to_csv(
            out_path,
            index=False
        )

        print(
            f"Saved {len(df_out)} predictions to {out_path}"
        )

        # ----------------------------------------------------------
        # Gemini usage report.
        # ----------------------------------------------------------

        usage = ai.usage_stats

        report_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "evaluation",
            "usage_report.md"
        )

        total_toks = usage["total_tokens"]

        avg_toks = (
            total_toks / total_reqs
            if total_reqs > 0
            else 0
        )

        report_content = f"""# Token Usage Report

## Model Information

- Provider: Google Gemini
- Model: {ai.model}
- Billing: Gemini API Free Tier

## Usage Summary

- Total model calls: {usage['calls']}
- Total input tokens: {usage['prompt_tokens']}
- Total output tokens: {usage['completion_tokens']}
- Total tokens: {total_toks}
- Average tokens per request: {avg_toks:.2f}
- Estimated total cost: $0.0000 (Gemini API Free Tier)
- Estimated per-request cost: $0.0000 (Gemini API Free Tier)

## Breakdown

Gemini is used only for evidence extraction:

1. Financial message interpretation
2. Image transaction amount extraction

The final affordability decision is produced deterministically
by the financial state builder, 90-day simulator, and decision
engine.

## Notes

- API key is loaded from the GEMINI_API_KEY environment variable.
- No API key is stored in source code.
- No API key is included in this report.
- The reported token counts come from Gemini response usage
  metadata when available.
"""

        os.makedirs(
            os.path.dirname(report_path),
            exist_ok=True
        )

        with open(
            report_path,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(report_content)

        print(
            f"Saved usage report to {report_path}"
        )

    # --------------------------------------------------------------
    # 6. SAMPLE RUN
    # --------------------------------------------------------------

    else:

        out_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "dataset",
            "sample_predictions.csv"
        )

        df_out.to_csv(
            out_path,
            index=False
        )

        print(
            f"Saved {len(df_out)} sample predictions to {out_path}"
        )

        print()
        print("Gemini usage:")
        print(
            f"  Calls: {ai.usage_stats['calls']}"
        )
        print(
            f"  Input tokens: "
            f"{ai.usage_stats['prompt_tokens']}"
        )
        print(
            f"  Output tokens: "
            f"{ai.usage_stats['completion_tokens']}"
        )
        print(
            f"  Total tokens: "
            f"{ai.usage_stats['total_tokens']}"
        )


if __name__ == "__main__":
    main()