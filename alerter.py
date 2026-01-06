import aiohttp
import json
import ssl
import certifi
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from config import LARK_WEBHOOK_URL, WX_WEBHOOK_URL, WX_WEBHOOK_AUTH
from logger import log

async def send_wx_alert(symbol: str, timeframe: str, signal_data: dict, ai_interpretation: str, model_name: str = "Unknown AI", timestamp: datetime = None):
    """
    Sends a simple text alert to the WX webhook.
    """
    webhook_url = WX_WEBHOOK_URL
    if not webhook_url:
        log.warning("WX webhook URL not set. Skipping WX alert.")
        return

    alert_time = timestamp if timestamp else datetime.utcnow()
    primary = signal_data.get('primary_signal', {})
    signal_type = primary.get('signal_type', 'N/A')
    indicator = primary.get('indicator', 'N/A')
    
    title = f"{symbol} [{timeframe}] {signal_type}"
    
    # Format metrics
    metrics = []
    excluded_keys = ['indicator', 'signal_type', 'thresholds_used', 'confirmation_candle']
    for k, v in primary.items():
        if k not in excluded_keys:
            metrics.append(f"{k}: {v}")
    
    metrics_str = "\n".join(metrics)
    
    # Construct content
    content = f"Timeframe: {timeframe}\nStrategy: {indicator}\n\nMetrics:\n{metrics_str}\n\nAI Analysis ({model_name}):\n{ai_interpretation}\n\nTime: {alert_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    
    payload = {
        "title": title,
        "content": content
    }
    
    headers = {
        "Authorization": WX_WEBHOOK_AUTH,
        "Content-Type": "application/json"
    }
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(webhook_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    log.info(f"WX alert for {symbol} sent successfully.")
                else:
                    log.error(f"Error sending WX alert: HTTP {response.status}")
    except Exception as e:
        log.error(f"Exception sending WX alert for {symbol}: {e}")

async def send_all_alerts(symbol: str, timeframe: str, signal_data: dict, ai_interpretation: str, model_name: str = "Unknown AI", timestamp: datetime = None):
    """
    Wrapper to send alerts to all configured channels.
    """
    tasks = []
    
    # Lark Alert
    if LARK_WEBHOOK_URL:
        tasks.append(send_lark_alert(symbol, timeframe, signal_data, ai_interpretation, model_name, timestamp))
        
    # WX Alert
    if WX_WEBHOOK_URL:
        tasks.append(send_wx_alert(symbol, timeframe, signal_data, ai_interpretation, model_name, timestamp))
        
    if tasks:
        await asyncio.gather(*tasks)

async def send_lark_alert(symbol: str, timeframe: str, signal_data: dict, ai_interpretation: str, model_name: str = "Unknown AI", timestamp: datetime = None):
    """
    构建并发送一个美化后的 Lark (飞书) 交互式卡片消息
    """
    webhook_url = LARK_WEBHOOK_URL
    if not webhook_url:
        log.warning("Lark webhook URL not set. Cannot send alert.")
        return
    
    alert_time = timestamp if timestamp else datetime.utcnow()
    # 提取数据
    primary = signal_data.get('primary_signal', {})
    indicator_name = primary.get('indicator', 'N/A')
    signal_type = primary.get('signal_type', 'N/A')
    
    # 1. 颜色与 Emoji 逻辑
    if 'Bullish' in signal_type:
        header_template = 'green'
        title_emoji = "🟢"
    elif 'Bearish' in signal_type:
        header_template = 'red'
        title_emoji = "🔴"
    else:
        header_template = 'blue'
        title_emoji = "🔵"

    # 2. 构建核心指标列 (Column Set)
    # 筛选出一些关键字段展示在网格中
    key_metrics = []
    excluded_keys = ['indicator', 'signal_type', 'thresholds_used', 'confirmation_candle']
    
    for k, v in primary.items():
        if k not in excluded_keys:
            key_metrics.append(f"**{k.replace('_', ' ').title()}**\n{v}")
            
    # 如果有 thresholds_used，单独放一行
    threshold_info = primary.get('thresholds_used', '')

    # 将指标分为两列
    col1_text = ""
    col2_text = ""
    for i, metric in enumerate(key_metrics):
        if i % 2 == 0:
            col1_text += metric + "\n\n"
        else:
            col2_text += metric + "\n\n"

    # Get current time in Asia/Shanghai timezone
    shanghai_tz = ZoneInfo("Asia/Shanghai")
    # Convert alert_time (assumed UTC) to Shanghai time
    current_shanghai_time = alert_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(shanghai_tz).strftime('%Y-%m-%d %H:%M:%S')

    # 3. 构建卡片元素
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**Timeframe:** {timeframe}\n**Signal Type:** {signal_type}\n**Time[UTC+8]:** {current_shanghai_time}"
            }
        },
        {
            "tag": "hr"
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "📊 **Signal Metrics**"
            }
        },
        {
            "tag": "column_set",
            "flex_mode": "none",
            "background_style": "grey",
            "columns": [
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "vertical_align": "top",
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": col1_text.strip()
                            }
                        }
                    ]
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "vertical_align": "top",
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": col2_text.strip()
                            }
                        }
                    ]
                }
            ]
        }
    ]

    # 如果有阈值信息，补充在后面
    if threshold_info:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"ℹ️ *Thresholds: {threshold_info}*"
            }
        })

    # 4. AI 解读部分
    if ai_interpretation:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"🤖 **{model_name} Analysis**"
            }
        })
        
        # 美化 AI 文本
        formatted_ai = ""
        sections = ai_interpretation.split('【')
        for section in sections:
            if '】' in section:
                parts = section.split('】', 1)
                title = parts[0]
                content = parts[1].strip()
                formatted_ai += f"**📌 {title}**\n{content}\n\n"
            else:
                if section.strip():
                    formatted_ai += section.strip() + "\n"
        
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": formatted_ai if formatted_ai else ai_interpretation
            }
        })

    # 5. 底部按钮 (跳转到 Binance)
    binance_url = f"https://www.binance.com/en/futures/{symbol}"
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "📈 View on Binance"
                },
                "type": "primary",
                "url": binance_url
            }
        ]
    })

    # 底部时间
    elements.append({
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"Bot: {model_name} | Time: {alert_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }
        ]
    })

    # 组装最终 Card
    card = {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"{title_emoji} {symbol} Market Alert"
            },
            "template": header_template
        },
        "elements": elements
    }

    payload = {
        "msg_type": "interactive",
        "card": card
    }

    # Create SSL context with certifi
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("code") == 0:
                        log.info(f"Lark alert for {symbol} sent successfully.")
                    else:
                        log.error(f"Lark API returned error: {data}")
                else:
                    log.error(f"Error sending Lark alert: HTTP {response.status}")
    except Exception as e:
        log.error(f"Exception sending Lark alert for {symbol}: {e}")
