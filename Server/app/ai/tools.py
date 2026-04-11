"""
Anthropic tool definition for structured stock prediction output.

Using tool_use (forced) means:
  - The JSON schema lives here, NOT in the prompt text.
  - Claude is guaranteed to return valid structured output.
  - No prompt parsing / regex hacks needed.
  - Saves ~200-300 tokens per call vs embedding the schema in the prompt.
"""

PREDICTION_TOOL: dict = {
    "name": "submit_prediction",
    "description": "Submit a structured next-day trading signal for the analysed stock.",
    "input_schema": {
        "type": "object",
        "required": [
            "signal",
            "confidence",
            "predicted_direction",
            "target_low",
            "target_high",
            "limit_price",
            "reasoning",
            "factors",
        ],
        "properties": {
            "signal": {
                "type": "string",
                "enum": ["bullish", "bearish", "neutral"],
                "description": "Overall market signal for the next trading day",
            },
            "confidence": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": "Confidence in the signal (0=no confidence, 100=very high)",
            },
            "predicted_direction": {
                "type": "string",
                "enum": ["up", "down", "neutral"],
                "description": "Expected next-day price direction",
            },
            "target_low": {
                "type": "number",
                "description": "Lower bound of expected price range tomorrow",
            },
            "target_high": {
                "type": "number",
                "description": "Upper bound of expected price range tomorrow",
            },
            "limit_price": {
                "type": "number",
                "description": (
                    "Suggested limit-order entry price. "
                    "Bullish: 1-2% below current (2-3% if confidence < 60). "
                    "Bearish/Neutral: at or just above current price."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": "3-5 sentence plain-English analysis",
            },
            "factors": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "description": "Key driving factors tagged by sentiment",
                "items": {
                    "type": "object",
                    "required": ["type", "text"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["bullish", "bearish", "risk"],
                        },
                        "text": {
                            "type": "string",
                            "description": "One-line description of the factor",
                        },
                    },
                },
            },
        },
    },
}
