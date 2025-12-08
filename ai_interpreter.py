import json
import random
import google.generativeai as genai
from config import GEMINI_API_KEYS, GEMINI_MODEL_NAME
from logger import log

def get_gemini_interpretation(symbol: str, timeframe: str, signal_data: dict, previous_signal: dict = None):
    """
    使用 Google 官方 SDK 解读指标异动信号及其市场背景
    """
    if not GEMINI_API_KEYS:
        log.warning("GEMINI_API_KEYS are not set. AI interpretation will be skipped.")
        return "AI interpretation unavailable (API Keys missing)."

    # 为了可读性，将数据包拆分
    primary_signal = signal_data.get('primary_signal', {})
    market_context = signal_data.get('market_context', {})

    system_prompt = """You are a world-class crypto market analyst. Your analysis is concise, data-driven, and directly actionable for experienced traders. You avoid generic advice and focus on interpreting the provided data to form a coherent market thesis. Do not use emojis. Never give financial advice.

Your Task is to analyze the primary signal in conjunction with the broader market context provided. Structure your interpretation in the following format, and your entire analysis must be in Chinese:

【核心信号解读】What does the specific primary signal mean in technical terms? (e.g., "A volume Z-Score of 3.5 indicates an extreme deviation from the recent average, suggesting a major market participant's activity.")
【市场背景分析】How does the market context (recent price action, key indicators, CVD) support or contradict the primary signal? (e.g., "This volume spike is occurring as the price is testing a key resistance level identified by the EMA_26, and the RSI is approaching overbought territory. The recent CVD trend has been flat, suggesting this may be a climactic top rather than a breakout.")
【潜在影响与后续关注】What is the most likely short-term impact, and what specific price levels or indicator behaviors should be monitored for confirmation or invalidation? (e.g., "Potential for a short-term reversal. Watch for a price rejection at the $68,200 level. Confirmation would be a bearish divergence on the RSI on the next price swing.")
"""

    # 将K线数据格式化为更易读的字符串
    klines_str = "\n".join([f"  - O:{k['open']:.2f} H:{k['high']:.2f} L:{k['low']:.2f} C:{k['close']:.2f} V:{k['volume']:,.0f}" for k in market_context.get('recent_klines', [])])

    # 构建历史信号部分
    if previous_signal:
        prev_signal_context = f"""**0. Previous Signal Context:**
This is an update to a previously triggered signal. Your task is to analyze if the new signal represents a continuation, acceleration, or potential reversal of the situation.
Previous Signal:
```json
{json.dumps(previous_signal, indent=2)}
```
"""
    else:
        prev_signal_context = """**0. Context:**
This is a new signal alert.
"""

    user_prompt = f"""{prev_signal_context}
**Asset:** {symbol}
**Timeframe:** {timeframe}

**1. Primary Signal Detected:**
```json
{json.dumps(primary_signal, indent=2)}
```

**2. Market Context Snapshot:**
*   **Key On-Chain & Market Indicators:**
    ```json
    {json.dumps(market_context.get('key_indicators', {}), indent=2)}
    ```
*   **Key Technical Indicators:**
    ```json
    {json.dumps(market_context.get('technical_indicators', {}), indent=2)}
    ```
*   **Recent Price Action (Last 16 periods, newest first):**
{klines_str}
"""

    # Combine system prompt and user prompt
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    # --- API Key Rotation Logic ---
    # Create a copy of keys to avoid modifying the global list if we were to pop
    keys_to_try = list(GEMINI_API_KEYS)
    # Shuffle the keys to distribute load (simple load balancing)
    random.shuffle(keys_to_try)

    for i, api_key in enumerate(keys_to_try):
        try:
            # Configure GenAI with the current key
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(GEMINI_MODEL_NAME)
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.6
                )
            )
            
            log.info(f"Successfully received AI interpretation for {symbol} using Key #{i+1} (masked: ...{api_key[-4:]})")
            return response.text

        except Exception as e:
            log.warning(f"Error calling Google Gemini API with Key #{i+1} (masked: ...{api_key[-4:]}): {e}. Trying next key...")
            continue
    
    # If we exit the loop, all keys failed
    log.error("All Gemini API keys failed. AI interpretation unavailable.")
    return "AI interpretation unavailable (All API keys failed)."
