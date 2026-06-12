import sys
import os
import re
import logging
from datetime import datetime, timedelta
from collections import Counter

# 将项目根目录加入 sys.path 以导入 common 模块
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(base_dir)

from common.config import Config
from common.feishu import FeishuBot

# 英文月份映射
MONTH_MAP = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}

# 正则表达式匹配 Privoxy 日志
# 示例: 192.168.2.135 - - [12/Jun/2026:14:34:18 +0800] "CONNECT bytelink100-ws.amemv.com:443 HTTP/1.1" 200 1115
LOG_PATTERN = re.compile(
    r'^(\S+)\s+-\s+-\s+\[([^\]]+)\]\s+"(\S+)\s+([^"\s]+)\s+HTTP/[0-9.]+"\s+(\d+)\s+(\S+)'
)

def parse_log_time(ts_str):
    """
    手动解析类似 "12/Jun/2026:14:34:18 +0800" 的时间字符串，避免 locale 语言包不兼容问题
    """
    try:
        parts = ts_str.split(' ')
        datetime_part = parts[0]  # "12/Jun/2026:14:34:18"
        
        dt_parts = datetime_part.split(':')
        date_part = dt_parts[0]   # "12/Jun/2026"
        time_part = ":".join(dt_parts[1:])  # "14:34:18"
        
        day, month_name, year = date_part.split('/')
        month = MONTH_MAP.get(month_name)
        if not month:
            return None
            
        dt = datetime(
            int(year), 
            month, 
            int(day), 
            *map(int, time_part.split(':'))
        )
        return dt
    except Exception as e:
        logging.debug(f"时间解析失败 ({ts_str}): {e}")
        return None

def analyze_privoxy_log(log_path, cutoff_time):
    """
    非独占式流式读取并解析 Privoxy 日志
    """
    total_errors = 0
    host_counter = Counter()
    host_status_map = {}  # host -> Counter(status_codes)
    sample_errors = []
    
    if not os.path.exists(log_path):
        logging.error(f"日志文件不存在: {log_path}")
        return None, f"日志文件不存在: {log_path}"
        
    try:
        # 以共享只读方式打开文件，不加锁，防止影响 Privoxy 写入
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                    
                match = LOG_PATTERN.match(line_str)
                if not match:
                    continue
                    
                ts_str = match.group(2)
                log_time = parse_log_time(ts_str)
                
                # 过滤掉 24 小时之前的时间戳
                if not log_time or log_time < cutoff_time:
                    continue
                    
                status_code = match.group(5)
                # 状态码非 200 判定为代理请求异常
                if status_code != "200":
                    total_errors += 1
                    host_port = match.group(4)
                    # 提取 host (去除端口)
                    host = host_port.split(':')[0] if ':' in host_port else host_port
                    
                    host_counter[host] += 1
                    if host not in host_status_map:
                        host_status_map[host] = Counter()
                    host_status_map[host][status_code] += 1
                    
                    # 收集前 5 个典型错误日志行
                    if len(sample_errors) < 5:
                        sample_errors.append(line_str)
                        
        result = {
            "total_errors": total_errors,
            "host_counter": host_counter,
            "host_status_map": host_status_map,
            "sample_errors": sample_errors
        }
        return result, None
    except Exception as e:
        logging.error(f"读取日志文件异常: {e}")
        return None, str(e)

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 1. 加载配置
    config = Config()
    log_path = config.get('privoxy.log_path')
    receive_id = config.get('feishu.default_receive_id')

    if not log_path:
        logging.error("未配置 Privoxy 日志路径 (privoxy.log_path)")
        return

    # 初始化飞书 Bot
    bot = FeishuBot(
        app_id=config.feishu_app_id,
        app_secret=config.feishu_app_secret
    )

    # 2. 定位时间范围：过去 24 小时
    now = datetime.now()
    cutoff_time = now - timedelta(hours=24)
    time_window_str = f"{cutoff_time.strftime('%Y-%m-%d %H:%M')} ~ {now.strftime('%Y-%m-%d %H:%M')}"

    logging.info(f"正在扫描日志: {log_path}，时间范围: {time_window_str}")
    
    # 3. 扫描分析日志
    analysis, err_msg = analyze_privoxy_log(log_path, cutoff_time)
    
    # 如果分析出错，发送报警卡片告知用户
    if err_msg:
        if receive_id and bot.client:
            bot.send_card_to_chat(
                receive_id=receive_id,
                title="🚨 Privoxy 监控执行失败",
                fields=[
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"💻 **任务名称**\nprivoxy_monitor"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"⚠️ **失败原因**\n{err_msg}"}}
                ],
                status="error"
            )
        return

    total_errors = analysis["total_errors"]

    # 4. 根据错误数构造卡片发送
    if total_errors == 0:
        logging.info("过去 24 小时内未发现任何异常日志，准备发送正常报告。")
        if receive_id and bot.client:
            title = "🟢 Privoxy 正常运行报告"
            content = f"监控时段：{time_window_str}\n\n过去 24 小时内所有代理请求状态码均为 **200 OK**，无异常连接记录。"
            bot.send_card_to_chat(
                receive_id=receive_id,
                title=title,
                content=content,
                status="success"
            )
    else:
        logging.warning(f"检测到 {total_errors} 个异常请求，发送报警通知。")
        if receive_id and bot.client:
            title = "🚨 Privoxy 代理异常监控报告"
            
            # 格式化 Top 5 域名排行
            top_hosts = analysis["host_counter"].most_common(5)
            host_list_md = []
            for host, count in top_hosts:
                status_counter = analysis["host_status_map"].get(host, Counter())
                # 拼接常见状态码，如 "502(10次)"
                status_detail = ", ".join([f"{code}({c}次)" for code, c in status_counter.most_common(2)])
                host_list_md.append(f"• **{host}**：异常 {count} 次 (状态码: {status_detail})")
            hosts_text = "\n".join(host_list_md) if host_list_md else "无"

            # 格式化典型错误日志
            sample_text = "\n".join([f"`{line}`" for line in analysis["sample_errors"]])
            
            fields = [
                {
                    "is_short": False,
                    "text": {"tag": "lark_md", "content": f"📅 **监控周期**\n{time_window_str}"}
                },
                {
                    "is_short": True,
                    "text": {"tag": "lark_md", "content": f"⚠️ **异常总请求数**\n{total_errors} 次"}
                },
                {
                    "is_short": True,
                    "text": {"tag": "lark_md", "content": f"🛡️ **健康度评估**\n需要关注"}
                },
                {
                    "is_short": False,
                    "text": {"tag": "lark_md", "content": f"📊 **主要故障域名 (Top 5)**\n{hosts_text}"}
                },
                {
                    "is_short": False,
                    "text": {"tag": "lark_md", "content": f"📋 **典型异常日志截取**\n{sample_text}"}
                }
            ]
            
            bot.send_card_to_chat(
                receive_id=receive_id,
                title=title,
                fields=fields,
                status="warning"
            )
    logging.info("分析完成并反馈飞书。")

if __name__ == "__main__":
    main()
