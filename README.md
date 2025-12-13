# Crypto Signal Bot

A sophisticated cryptocurrency trading signal bot that monitors Binance Futures market data, detects Fair Value Gap (FVG) signals, analyzes them using DeepSeek AI, and sends real-time alerts via Lark (Feishu) and WeChat (WXPush).

## Features

*   **Real-time Monitoring**: Tracks major cryptocurrencies (BTC, ETH, SOL, HYPE, AVAX) on Binance Futures.
*   **Fair Value Gap (FVG) Strategy**: Detects bullish and bearish FVG formations and subsequent price rebalancing with reversal confirmation (Hammer/Shooting Star).
*   **AI Analysis**: Integrates with DeepSeek AI to provide in-depth market sentiment and technical analysis for each detected signal.
*   **Dual Notification System**:
    *   **Lark (Feishu)**: Rich interactive cards with color-coded headers and formatted metrics.
    *   **WeChat (WXPush)**: Template messages via Cloudflare Workers with "click-to-view" details.
*   **Deduplication & Cooldown**: Smart filtering to prevent spam, ensuring distinct signals are sent with a 15-minute cooldown period.
*   **Async Core**: Built on Python `asyncio` for efficient, non-blocking data fetching and processing.

## Configuration

The bot is configured via `config.py` and environment variables.

### Monitored Assets
Currently configured to monitor: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `HYPEUSDT`, `AVAXUSDT`.

### Environment Variables (.env)
Create a `.env` file in the root directory:

```bash
# Binance (Optional, for higher rate limits)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_secret

# DeepSeek AI
DEEPSEEK_API_KEY=your_deepseek_key

# Notifications
LARK_WEBHOOK_URL=your_lark_webhook_url
```

### Notification Setup

#### 1. Lark (Feishu)
1.  Create a custom bot in a Lark group.
2.  Copy the Webhook URL to `LARK_WEBHOOK_URL` in `.env`.

#### 2. WeChat (WXPush)
The project includes Cloudflare Worker scripts (`worker_api.js` and `worker_view.js`) to bridge the bot with WeChat.

1.  **Deploy Workers**: Deploy the API and View workers as described in the worker scripts.
2.  **Configure Config**: Update `config.py` with your Worker URL and Auth token.
    ```python
    WX_WEBHOOK_URL = "https://your-api-worker.workers.dev/wxsend"
    WX_WEBHOOK_AUTH = "your_api_token"
    ```

## Running the Bot

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure `pandas`, `pandas_ta`, `ccxt`, `aiohttp`, `python-dotenv` are installed)*

2.  **Start the Bot**:
    ```bash
    python main.py
    ```

## Project Structure

*   `main.py`: Entry point, runs the async event loop and schedules checks.
*   `indicators.py`: Contains the `FairValueGapSignal` logic.
*   `data_fetcher.py`: Handles async fetching of OHLCV data from Binance.
*   `ai_interpreter.py`: Sends signal data to DeepSeek AI for analysis.
*   `alerter.py`: Manages sending notifications to Lark and WeChat.
*   `state_manager.py`: Handles signal deduplication and cooldown state persistence.
*   `config.py`: Central configuration file.

## Strategy Details

**Fair Value Gap (FVG) Rebalance**
*   **Detection**: Identifies a 3-candle pattern where the 1st candle's high/low does not overlap with the 3rd candle's low/high.
*   **Trigger**: Price retraces into this gap zone.
*   **Confirmation**: A reversal candlestick pattern (Hammer for Bullish, Shooting Star for Bearish) forms after entering the gap.