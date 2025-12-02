# config.py
import os
from dotenv import load_dotenv
load_dotenv()
# --- API Keys & Webhooks ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# --- Gemini Model Settings ---
# 默认模型名称
GEMINI_MODEL_NAME = "gemini-2.5-flash-lite"
# 代理或自定义API地址 (如果使用官方API，请留空或注释掉)
GEMINI_API_BASE_URL = "https://api.uykb.eu.org/v1"
# --- Monitoring Settings ---
TIMEFRAME = '15m'                # K线周期
DATA_FETCH_LIMIT = 1000          # 每次获取数据条数

# A list of major coins to monitor. If empty, the bot will scan all USDT perpetual futures.
MAJOR_COINS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "DOTUSDT",
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

# --- State Management (Memory) Settings ---
# 信号冷却时间（分钟），在此时间内，相似的信号不会重复发送
SIGNAL_COOLDOWN_PERIOD = 60  # 60分钟 = 1小时

# Z-Score 类信号的显著变化阈值
# 只有当新的 Z-Score 与上次发送的 Z-Score 差值的绝对值大于此阈值时，才被视为新信号
Z_SCORE_CHANGE_THRESHOLD = 0.5

# 百分比类信号的显著变化阈值 (例如 OI 变化)
# 只有当新的百分比与上次发送的百分比差值的绝对值大于此阈值时，才被视为新信号
PERCENTAGE_CHANGE_THRESHOLD = 0.05 # 5%
