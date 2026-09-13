# HackerRank Orchestrate: Buy or Wait?

Build an AI-powered financial agent that decides whether a user can safely afford a requested expense.

## Approach Overview

This solution reconstructs a user's financial state to accurately forecast their future cash flow up to 90 days out. It then uses binary search to find the absolute maximum safe amount they can afford to pay without dipping below their required minimum balance.

### Core Components:
1. **DataLoader (`data_loader.py`)**: Loads the CSV tables (profiles, events, options, exchange rates, requests).
2. **AIParser (`ai_parser.py`)**: 
   - Uses the Gemini/OpenAI API (or a heuristic fallback when rate-limited) to extract missing amounts from images and parse message amendments.
   - Updates the financial events with these critical details (e.g. rent increases, salary delays).
3. **StateBuilder (`state_builder.py`)**: 
   - Reconstructs the exact cash flow state on the `request_date`.
   - Merges related/linked events, applies message amendments, and strictly separates fixed from variable flexible expenses.
   - Uses a robust pattern detection algorithm to identify recurring events (salary, rent, groceries, subscriptions).
   - Carefully excludes one-off fixed expenses and expired/dead patterns (using a dynamic time-decay threshold).
4. **Simulator (`simulator.py`)**: 
   - Projects the state forward 90 days.
   - Calculates the exact `buffer` above the `minimum_balance_to_keep`.
   - Uses a 50-iteration binary search to pinpoint the precise `amount_safe_to_pay` down to two decimal places (handles high-magnitude currencies like IDR perfectly).
5. **DecisionEngine (`decision_engine.py`)**: 
   - Takes the output of the simulator and generates viable payment plans (Wait, Partial, Installments, Full).
   - Selects the most optimal plan based on user preferences and constraints (minimizing spending changes).

## Setup Instructions

### Prerequisites
- Python 3.9+
- API Keys for Gemini or OpenAI (optional, the system falls back to heuristics if exhausted)

### 1. Installation
First, clone the repository and navigate into the project directory:
```bash
git clone https://github.com/priyanshusharan-cmd/afford-ai.git
cd afford-ai
```

Set up a virtual environment and install the required dependencies:
```bash
python3 -m venv venv2
source venv2/bin/activate
pip install -r requirements.txt
```

### 2. Configuration (Optional)
If you wish to use the LLM parsing capabilities, export your API keys in the terminal (or place them in a `.env` file):
```bash
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"
```
*(If no keys are provided or if rate limits are hit, the system seamlessly falls back to regex/heuristic parsing).*

### 3. Running the System
To evaluate the sample dataset (25 rows) and view accuracy:
```bash
python3 code/main.py --mode=sample
python3 code/sample_scorer.py
```

To run the full evaluation on all 250 requests (generates the final `output.csv` and `evaluation/usage_report.md`):
```bash
python3 code/main.py --mode=eval
```
The final predictions will be saved as `output.csv` in the root directory.

---

## Important File Locations

```text
dataset/        Input data and the blank output template.
code/           Your solution code.
output.csv      Final generated predictions in the repository root.
solution/       Contains the final `code.zip` and `output.csv` ready for submission.
```
