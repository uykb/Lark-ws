import aiohttp
import json
from datetime import datetime
from config import LARK_WEBHOOK_URL
from logger import log

async def send_lark_alert(symbol: str, signal_data: dict, ai_interpretation: str):
    """
    构建并发送一个 Lark (飞书) 交互式卡片消息
    """
    webhook_url = LARK_WEBHOOK_URL
    if not webhook_url:
        log.warning("Lark webhook URL not set. Cannot send alert.")
        return
    
    # 从新的数据结构中提取主要触发信号
    primary_signal = signal_data.get('primary_signal', {})
    indicator_name = primary_signal.get('indicator', 'N/A')
    
    # 根据指标类型设置卡片标题颜色
    # Lark card templates: blue, wathet, turquoise, green, yellow, orange, red, carmine, violet, purple, indigo, grey
    header_template = "blue"
    if "Open Interest" in indicator_name:
        header_template = "blue"
    elif "Volume" in indicator_name:
        header_template = "orange"
    elif "Ratio" in indicator_name:
        header_template = "red"
    elif "Gap" in indicator_name:
        header_template = "violet"

    # 构建主要信号详情
    details_md = ""
    for key, value in primary_signal.items():
        if key not in ['indicator', 'signal_type']:
            details_md += f"**{key.replace('_', ' ').title()}:** {value}\n"
    
    # 构建卡片内容
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**Indicator:** {indicator_name}\n**Type:** {primary_signal.get('signal_type', 'N/A')}"
            }
        },
        {
            "tag": "hr"
        },
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": details_md.strip()
            }
        }
    ]

    # 添加 AI 解读
    if ai_interpretation:
        elements.append({"tag": "hr"})
        
        # 简单解析 AI 解读，或者直接作为一大段文本放入
        # Lark Markdown 支持基本的加粗等
        ai_content = ai_interpretation
        
        # 尝试美化分段
        formatted_ai = ""
        sections = ai_interpretation.split('【')
        for section in sections:
            if '】' in section:
                parts = section.split('】', 1)
                title = parts[0]
                content = parts[1].strip()
                formatted_ai += f"**🤖 {title}**\n{content}\n\n"
            else:
                if section.strip():
                    formatted_ai += section.strip() + "\n"
        
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": formatted_ai if formatted_ai else ai_content
            }
        })

    # 添加底部时间和版权
    elements.append({
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"Bot by YourName | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }
        ]
    })

    card = {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": f"🚨 {symbol} 市场异动告警"
            },
            "template": header_template
        },
        "elements": elements
    }

    payload = {
        "msg_type": "interactive",
        "card": card
    }
    
    try:
        async with aiohttp.ClientSession() as session:
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