import requests
import json
from datetime import datetime
from config import DISCORD_WEBHOOK_URL
def send_discord_alert(symbol: str, signal_data: dict, ai_interpretation: str):
    """
    构建并发送一个精美的 Discord embed 消息
    """
    webhook_url = DISCORD_WEBHOOK_URL
    if not webhook_url:
        print("Discord webhook URL not set.")
        return
    
    # 从新的数据结构中提取主要触发信号
    primary_signal = signal_data.get('primary_signal', {})
    indicator_name = primary_signal.get('indicator', 'N/A')
    signal_type = primary_signal.get('signal_type', 'N/A')
    # 根据指标类型设置颜色
    color_map = {
        "Volume": 15844367, # Gold
        "Open Interest": 3447003, # Blue
        "Long/Short Ratio": 15158332 # Red
    }
    embed = {
        "title": f"🚨检测到市场异常: {symbol} 🚨",
        "description": f"**Indicator:** `{indicator_name}`\n**Signal:** `{signal_type}`",
        "color": color_map.get(indicator_name, 5814783), # Default grey
        "fields": [],
        "footer": {
            "text": f"Data from Binance Futures | Bot by YourName | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        }
    }
    
    # 添加具体指标数据
    for key, value in primary_signal.items():
        if key not in ['indicator', 'signal_type']:
            embed['fields'].append({"name": key.replace('_', ' ').title(), "value": str(value), "inline": True})
    # 添加 AI 解读
    if ai_interpretation:
        embed['fields'].append({
            "name": "🤖 Gemini AI Analyst Insight",
            "value": ai_interpretation,
            "inline": False 
        })
    
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        print("Discord alert sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord alert: {e}")
