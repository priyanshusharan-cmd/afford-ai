<h1 align="center">AffordAI</h1>

**Afford-AI** is an intelligent, AI-powered financial agent designed to answer a single, critical question: *"Can I safely afford this?"*

Going beyond simple balance checks, Afford-AI reconstructs a user's financial state, forecasts 90-day cash flows, and evaluates recurring expenses, pending payments, payment options, and contextual messages/images to provide a personalized, safe, and actionable payment recommendation.

---

## 🌟 Key Features

* **Advanced Financial State Reconstruction:** Accurately builds user cash flow profiles and tracks income and expenses using historical events, detecting patterns like rent and salary automatically.
* **90-Day Predictive Cash Flow Simulation:** Projects finances up to 90 days out, ensuring user balances never fall below their required minimum threshold.
* **Intelligent Payment Strategy Engine:** Decides between `full_payment`, `partial_payment`, `installments`, or `wait` based on user preferences and constraints.
* **Multi-modal AI Parsing:** Leverages Gemini and OpenAI APIs to extract missing financial data from images and textual message amendments (with seamless regex fallback when rate-limited).
* **High-Precision Binary Search Optimization:** Finds the absolute maximum safe amount (`amount_safe_to_pay`) a user can afford down to two decimal places, robust enough for high-magnitude currencies.

---

## 🧠 System Architecture

The agent operates through five core components to ensure deterministic, safe recommendations:

1. **DataLoader (`data_loader.py`)**: Ingests and structures CSV tables containing profiles, events, options, exchange rates, and requests.
2. **AIParser (`ai_parser.py`)**: Processes images and messages to extract critical financial details (e.g., rent increases, missing transaction amounts) using LLMs.
3. **StateBuilder (`state_builder.py`)**: Reconstructs the exact cash flow state on the `request_date`, categorizes expenses (fixed vs. variable), and detects recurring patterns while decaying obsolete ones.
4. **Simulator (`simulator.py`)**: Simulates 90 days of future cash flows and uses binary search to pinpoint exact affordability margins.
5. **DecisionEngine (`decision_engine.py`)**: Synthesizes the simulation data to select the optimal payment plan, minimizing required spending changes and maximizing user satisfaction.

---

## 🚀 Getting Started

### Prerequisites

* Python 3.9 or higher
* *(Optional)* API Keys for Gemini or OpenAI for multi-modal parsing. The system gracefully falls back to heuristics if keys are omitted.

### 1. Installation

Clone the repository and set up your environment:

```bash
git clone https://github.com/priyanshusharan-cmd/afford-ai.git
cd afford-ai

# Set up and activate a virtual environment
python3 -m venv venv2
source venv2/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration (Optional)

To enable LLM parsing, export your API keys in the terminal or add them to a `.env` file:

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
export OPENAI_API_KEY="your_openai_api_key_here"
```

### 3. Running the Agent

**Run in Sample Mode:** Evaluate a small 25-row subset and view the accuracy scores.
```bash
python3 code/main.py --mode=sample
python3 code/sample_scorer.py
```

**Run Full Evaluation:** Process all 250 requests to generate the final `output.csv` and the usage report.
```bash
python3 code/main.py --mode=eval
```
*Note: Final predictions are saved to `output.csv` in the root directory.*

---

## 📁 Repository Structure

```text
├── dataset/             # Input CSV data, template output, and media files
├── code/                # Core logic (DataLoader, AIParser, Simulator, etc.)
├── evaluation/          # Token usage reports and run summaries
├── solution/            # Packaged code.zip and output.csv for submission
├── output.csv           # Generated predictions
└── README.md            # This documentation
```

---

## 🎯 Evaluation Output Schema

For every request, the system outputs the following in `output.csv`:

* `amount_safe_to_pay`: Maximum amount the user can safely pay today.
* `affordability_status`: `affordable_now`, `affordable_with_plan`, `affordable_later`, or `not_affordable`.
* `recommended_payment_method`: Safest approach (`full_payment`, `partial_payment`, `installments`, `wait`, `not_recommended`).
* `payment_plan`: Complete payment schedule.
* `earliest_date_for_full_payment`: Earliest safe date for a single full payment.
* `spending_changes_needed`: Any flexible expenses that must be reduced/stopped.
* `decision_explanation`: A transparent explanation supporting the recommendation.

---

*Built for the HackerRank Orchestrate: Buy or Wait? Challenge.*
