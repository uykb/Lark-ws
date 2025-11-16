# config.py
import os
from dotenv import load_dotenv
load_dotenv()
# --- API Keys & Webhooks ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# --- Gemini Model Settings ---
# 默认模型名称
GEMINI_MODEL_NAME = "gemini-2.5-flash" 
# 代理或自定义API地址 (如果使用官方API，请留空或注释掉)
GEMINI_API_BASE_URL = "https://api.uykb.eu.org/v1" 
# --- Monitoring Settings ---
DEFAULT_TIMEFRAME = '15m'        # 默认K线周期 (用于 "Catch the Rise" 等)
FVG_TIMEFRAME = '1h'             # FVG信号的K线周期
DATA_FETCH_LIMIT = 200           # 每次获取数据条数
# --- Indicator Thresholds ---
# Rule 1: Catch the Rise
RISE_OI_CHANGE_THRESHOLD = 0.05    # OI a single period change threshold (5%)
RISE_PRICE_CHANGE_THRESHOLD = 0.02 # Price a single period change threshold (2%)

# Rule 2: FVG Trend Catch
# (No specific thresholds needed here, logic is pattern-based)

# --- State Management (Memory) Settings ---
# 信号冷却时间（分钟），在此时间内，相似的信号不会重复发送
SIGNAL_COOLDOWN_PERIOD = 60  # 60分钟 = 1小时

# Z-Score 类信号的显著变化阈值
# 只有当新的 Z-Score 与上次发送的 Z-Score 差值的绝对值大于此阈值时，才被视为新信号
Z_SCORE_CHANGE_THRESHOLD = 0.5

# 百分比类信号的显著变化阈值 (例如 OI 变化)
# 只有当新的百分比与上次发送的百分比差值的绝对值大于此阈值时，才被视为新信号
PERCENTAGE_CHANGE_THRESHOLD = 0.05 # 5%
