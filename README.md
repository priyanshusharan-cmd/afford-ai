<h1 align="center">AffordAI</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License MIT">
  <img src="https://img.shields.io/badge/HackerRank-Orchestrate-orange.svg" alt="HackerRank Orchestrate">
</p>

<p align="center">
  <em>An intelligent, AI-powered financial agent designed to answer a single, critical question: <strong>"Can I safely afford this?"</strong></em>
</p>

---

## 📖 Overview

**AffordAI** goes far beyond simple balance checks. It reconstructs a user's entire financial state, forecasts 90-day cash flows, and rigorously evaluates recurring expenses, pending payments, payment options, and contextual messages/images. By processing all of this, it provides a personalized, safe, and highly actionable payment recommendation. 

Whether it's deciding between paying in full today, utilizing installment plans, or waiting for a safer financial period, **AffordAI** guarantees your balance never dips below your essential threshold.

---

## ✨ Core Features

- 🔍 **Advanced Financial State Reconstruction:** Accurately builds user cash flow profiles and tracks income/expenses using historical events. Automatically detects patterns like rent and salary.
- 📈 **90-Day Predictive Cash Flow Simulation:** Projects finances up to 90 days out, ensuring user balances never fall below their customized minimum required threshold.
- 🧠 **Intelligent Payment Strategy Engine:** Decides intelligently between `full_payment`, `partial_payment`, `installments`, or `wait` based on real-time user constraints and market options.
- 🤖 **Multi-modal AI Parsing:** Leverages powerful Gemini and OpenAI APIs to extract missing financial data from images and textual message amendments (with seamless regex fallbacks when rate-limited).
- ⚡ **High-Precision Binary Search Optimization:** Pinpoints the absolute maximum safe amount (`amount_safe_to_pay`) a user can afford down to two decimal places—robust enough for high-magnitude currencies (like IDR).

---

## 🏗️ System Architecture

The agent operates through five core robust components to ensure deterministic, safe, and lightning-fast recommendations:

1. **`DataLoader`**: Ingests and structures CSV tables containing financial profiles, historical events, options, exchange rates, and user requests.
2. **`AIParser`**: Processes contextual images and messages to extract critical financial details (e.g., rent increases, missing transaction amounts) using state-of-the-art LLMs.
3. **`StateBuilder`**: Reconstructs the exact cash flow state on the `request_date`, categorizes expenses (fixed vs. variable), and detects recurring patterns while safely decaying obsolete ones.
4. **`Simulator`**: Simulates 90 days of future cash flows and runs a binary search algorithm to pinpoint exact affordability margins.
5. **`DecisionEngine`**: Synthesizes the simulation data to select the optimal payment plan, minimizing required spending changes while maximizing user satisfaction.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.9 or higher
* *(Optional)* API Keys for Gemini or OpenAI for multi-modal parsing. The system gracefully falls back to deterministic heuristics if keys are omitted.

### 1. Installation

Clone the repository and navigate into it:
```bash
git clone https://github.com/priyanshusharan-cmd/afford-ai.git
cd afford-ai
```

Set up and activate a virtual environment:

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. Configuration (Optional)

To enable LLM parsing, provide your API keys by exporting them in your terminal:

**Mac / Linux:**
```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
export OPENAI_API_KEY="your_openai_api_key_here"
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your_gemini_api_key_here"
$env:OPENAI_API_KEY="your_openai_api_key_here"
```

### 3. Running the Agent

**Run Full Evaluation:** Process all requests to generate the final `output.csv` and the usage report.
```bash
python3 code/main.py --mode=eval
```
*Note: Final predictions are saved to `output.csv` in the root directory.*

---

## 🎯 Evaluation Output Schema

For every processed request, the system securely outputs the following parameters in `output.csv`:

| Column | Description |
| :--- | :--- |
| `amount_safe_to_pay` | Maximum amount the user can safely pay today without risking minimum balances. |
| `affordability_status` | Returns either `affordable_now`, `affordable_with_plan`, `affordable_later`, or `not_affordable`. |
| `recommended_payment_method` | The safest recommended approach (`full_payment`, `partial_payment`, `installments`, `wait`, `not_recommended`). |
| `payment_plan` | Complete chronological payment schedule to fulfill the request safely. |
| `earliest_date_for_full_payment` | The earliest safe date for a single full payment. |
| `spending_changes_needed` | Highlights any flexible expenses that must be safely reduced or stopped. |
| `decision_explanation` | A fully transparent, human-readable explanation supporting the AI's mathematical recommendation. |

---

<br/>

<div align="center">
  <i>Built for the HackerRank Orchestrate: Buy or Wait? Challenge.</i>
</div>

<br/>

<div align="center">
  <a href="https://www.linkedin.com/in/priyanshusharan">
    <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png" width="40" height="40" alt="LinkedIn Profile"/>
  </a>
</div>
