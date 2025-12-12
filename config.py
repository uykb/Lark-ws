# config.py
import os
from dotenv import load_dotenv
load_dotenv()

# --- API Keys & Webhooks ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

LARK_WEBHOOK_URL = os.getenv("LARK_WEBHOOK_URL")

# --- AI Model Settings ---
DEEPSEEK_MODEL_NAME = "deepseek-chat"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# --- Monitoring Settings ---
TIMEFRAME = '15m'               # K线周期
DATA_FETCH_LIMIT = 1000          # 每次获取数据条数

# A list of major coins to monitor.
# Only the coins listed here will be monitored.
MAJOR_COINS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "AVAXUSDT",
]
# --- Indicator Thresholds ---
# Rule 1: Catch the Rise
RISE_OI_CHANGE_THRESHOLD = 0.03    # OI a single period change threshold (3%)
RISE_PRICE_CHANGE_THRESHOLD = 0.01 # Price a single period change threshold (1%)

# Rule 2: Catch the Trend (FVG)
FVG_REBALANCE_THRESHOLD = 0.5      # Price must retrace at least 50% into the FVG
FVG_CONFIRMATION_CANDLE_TYPE = 'hammer' # 'hammer', 'shooting_star', 'engulfing', etc.

# --- Active Signals ---
# A list of signal class names to be activated.
ACTIVE_SIGNALS = [
    "MomentumSpikeSignal",
    "FairValueGapSignal",
]

# --- Per-Coin Configuration Overrides ---
# Define specific thresholds for major coins.
# If a coin is not listed here, it will use the default global thresholds defined above.
COIN_CONFIGS = {
    "BTCUSDT": {
        "rise_oi_change_threshold": 0.015,   # 1.5% for BTC (Lower due to lower volatility)
        "rise_price_change_threshold": 0.008 # 0.8%
    },
    "ETHUSDT": {
        "rise_oi_change_threshold": 0.02,    # 2.0%
        "rise_price_change_threshold": 0.01
    },
    # Default fallback for unlisted coins (conceptually matches global settings)
    "DEFAULT": {
        "rise_oi_change_threshold": 0.03,
        "rise_price_change_threshold": 0.01
    }
}

# --- State Management (Memory) Settings ---
# 信号冷却时间（分钟），在此时间内，相似的信号不会重复发送
# 设置为 0 表示禁用冷却时间，每次触发都发送
SIGNAL_COOLDOWN_PERIOD = 0  

# FVG 信号的专属冷却时间（分钟）。
# 在此时间内，如果 FVG 的价格区间与上次触发的 FVG 价格区间相近，则不会重复发送。
FVG_COOLDOWN_PERIOD_MINUTES = 60 # e.g., 60 minutes

# FVG 信号的价格容忍度百分比。
# 如果新的 FVG 的 fvg_top 和 fvg_bottom 与上次的 FVG 的 top/bottom 都相差小于此百分比，则视为“相同”的 FVG。
FVG_PRICE_TOLERANCE_PERCENT = 0.05 # e.g., 0.05%

# Z-Score 类信号的显著变化阈值
# 只有当新的 Z-Score 与上次发送的 Z-Score 差值的绝对值大于此阈值时，才被视为新信号
Z_SCORE_CHANGE_THRESHOLD = 0.5

# 百分比类信号的显著变化阈值 (例如 OI 变化)
# 只有当新的百分比与上次发送的百分比差值的绝对值大于此阈值时，才被视为新信号
PERCENTAGE_CHANGE_THRESHOLD = 0.05 # 5%
