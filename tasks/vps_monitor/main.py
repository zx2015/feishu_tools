import sys
import os
import requests
import logging
from datetime import datetime

# 将项目根目录加入 sys.path 以导入 common 模块
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(base_dir)

from common.config import Config
from common.feishu import FeishuBot

def format_bytes_to_gb(bytes_val):
    """将字节转换为 GB，保留两位小数"""
    return round(bytes_val / (1024**3), 2)

def format_timestamp(ts):
    """将 Unix 时间戳转换为本地时间字符串"""
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def fetch_vps_info(veid, api_key):
    """从 64clouds API 获取 VPS 信息"""
    url = f"https://api.64clouds.com/v1/getServiceInfo?veid={veid}&api_key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"获取 VPS 信息失败: {e}")
        return None

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 1. 加载配置
    config = Config()
    veid = config.get('vps.veid')
    api_key = config.get('vps.api_key')
    
    # 优先使用 VPS 任务特有的 receive_id，若无则使用全局默认 default_receive_id
    receive_id = config.get('vps.receive_id') or config.get('feishu.default_receive_id')

    if not veid or not api_key:
        logging.error("未配置 VPS veid 或 api_key")
        return

    # 初始化飞书 Bot
    bot = FeishuBot(
        app_id=config.feishu_app_id,
        app_secret=config.feishu_app_secret
    )

    # 2. 获取数据
    logging.info(f"正在获取 VPS ({veid}) 的运行状态...")
    data = fetch_vps_info(veid, api_key)
    
    if not data or data.get('error') != 0:
        error_msg = data.get('message', '未知错误') if data else '请求失败'
        logging.error(f"API 返回错误: {error_msg}")
        
        # 增强容错通知：发送错误通知卡片到飞书
        if receive_id and bot.client:
            logging.info("正在发送飞书错误警报卡片...")
            err_title = "🚨 VPS 状态监控失败"
            err_fields = [
                {
                    "is_short": True,
                    "text": {"tag": "lark_md", "content": f"💻 **VPS ID**\n{veid}"}
                },
                {
                    "is_short": True,
                    "text": {"tag": "lark_md", "content": f"⚠️ **错误原因**\n{error_msg}"}
                }
            ]
            bot.send_card_to_chat(
                receive_id=receive_id,
                title=err_title,
                fields=err_fields,
                status="error"
            )
        return

    # 3. 解析数据
    hostname = data.get('hostname')
    multiplier = data.get('monthly_data_multiplier', 1)
    
    # 流量计算 (需要乘以 multiplier)
    total_data_gb = format_bytes_to_gb(data.get('plan_monthly_data', 0) * multiplier)
    used_data_gb = format_bytes_to_gb(data.get('data_counter', 0) * multiplier)
    remaining_data_gb = round(total_data_gb - used_data_gb, 2)
    usage_percent = round((used_data_gb / total_data_gb) * 100, 1) if total_data_gb > 0 else 0
    
    # 避免 Unix 时间戳为 0 导致转换错误
    next_reset = data.get('data_next_reset', 0)
    if next_reset > 0:
        reset_datetime = datetime.fromtimestamp(next_reset)
        reset_date = reset_datetime.strftime('%Y-%m-%d')
        
        # 计算距离重置日期的天数/小时数
        delta = reset_datetime - datetime.now()
        if delta.total_seconds() > 0:
            if delta.days > 0:
                days_left_str = f"{delta.days} 天"
            else:
                hours_left = int(delta.total_seconds() / 3600)
                days_left_str = f"{hours_left} 小时"
        else:
            days_left_str = "已重置"
    else:
        reset_date = "未知"
        days_left_str = "未知"
        
    location = data.get('node_location', 'Unknown')
    plan = data.get('plan', 'Unknown')

    # 4. 构造卡片内容
    title = f"🖥️ VPS 状态报告: {hostname or 'US-Cloud'}"
    
    fields = [
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"📍 **位置**\n{location}"}
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"📦 **套餐**\n{plan}"}
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"📊 **流量消耗 ({usage_percent}%)**\n{used_data_gb} GB / {total_data_gb} GB"}
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"🔋 **剩余流量**\n{remaining_data_gb} GB"}
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"📅 **重置日期**\n{reset_date}"}
        },
        {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"⏳ **距离重置**\n{days_left_str}"}
        }
    ]

    # 根据使用量决定卡片颜色
    status = "success"
    if usage_percent > 80:
        status = "warning"
    if usage_percent > 95:
        status = "error"

    # 5. 发送消息
    logging.info("正在发送飞书卡片消息...")
    bot.send_card_to_chat(
        receive_id=receive_id,
        title=title,
        fields=fields,
        status=status
    )
    logging.info("报告发送完成。")

if __name__ == "__main__":
    main()
