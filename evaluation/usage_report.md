# Token Usage Report

## Model Information

- Provider: Google Gemini
- Model: gemini-3.7-flash
- Billing: Gemini API Free Tier

## Usage Summary

- Total model calls: 0
- Total input tokens: 0
- Total output tokens: 0
- Total tokens: 0
- Average tokens per request: 0.00
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
