import json
import aiohttp
import ssl
import certifi
from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_MODEL_NAME, DEEPSEEK_API_URL,
    GEMINI_API_KEY, GEMINI_MODEL_NAME, GEMINI_API_URL
)
from logger import log

async def _call_openai_compatible_api(api_key: str, api_url: str, model_name: str, system_prompt: str, user_prompt: str) -> str:
    """
    Generic function to call an OpenAI-compatible API.
    Returns the content string on success, or raises an exception on failure.
    """
    if not api_key:
        raise ValueError("API Key is missing")
    if not api_url:
        raise ValueError("API URL is missing")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 1.0 
    }

    # Create SSL context with certifi
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        async with session.post(api_url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
                else:
                    raise ValueError(f"Invalid response format: {data}")
            else:
                error_text = await response.text()
                raise ValueError(f"API Error {response.status}: {error_text}")

async def get_ai_interpretation(symbol: str, timeframe: str, signal_data: dict, previous_signal: dict = None) -> tuple[str, str]:
    """
    使用 AI (优先 Gemini, 备用 DeepSeek) 解读指标异动信号及其市场背景 (Async).
    Returns: (interpretation_text, model_name)
    """

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

    # --- Attempt 1: Gemini ---
    try:
        log.info(f"Attempting AI interpretation for {symbol} using Gemini...")
        interpretation = await _call_openai_compatible_api(
            GEMINI_API_KEY, GEMINI_API_URL, GEMINI_MODEL_NAME, system_prompt, user_prompt
        )
        log.info(f"Successfully received AI interpretation for {symbol} using Gemini.")
        return interpretation, GEMINI_MODEL_NAME
    except Exception as e:
        log.warning(f"Gemini API failed: {e}. Falling back to DeepSeek.")

    # --- Attempt 2: DeepSeek ---
    try:
        log.info(f"Attempting AI interpretation for {symbol} using DeepSeek...")
        interpretation = await _call_openai_compatible_api(
            DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL_NAME, system_prompt, user_prompt
        )
        log.info(f"Successfully received AI interpretation for {symbol} using DeepSeek.")
        return interpretation, DEEPSEEK_MODEL_NAME
    except Exception as e:
        log.error(f"DeepSeek API also failed: {e}. AI interpretation unavailable.")
        return f"AI interpretation unavailable. (Gemini Error: Check logs, DeepSeek Error: {e})", "None"
