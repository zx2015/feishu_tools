# VPS 资源监控任务 (vps_monitor)

该任务通过搬瓦工 (BandwagonHost/64clouds) 的 API 接口，定时检查 VPS 的资源使用情况，并将关键指标通过飞书卡片消息推送给用户。

## 功能特性

- **流量监控**：获取本月已用流量与总流量配额。
- **重置提醒**：显示流量计费周期的下一次重置时间。
- **自动单位转换**：自动将字节 (Bytes) 转换为 GB，方便阅读。
- **飞书集成**：使用美化的交互式卡片发送报告，支持状态颜色标识。

## API 引用

- **接口地址**：`https://api.64clouds.com/v1/getServiceInfo`
- **主要参数**：
  - `veid`: VPS 的唯一识别 ID。
  - `api_key`: API 访问密钥。

## 配置要求

在项目根目录的 `config.yaml` 中添加以下配置：

```yaml
vps:
  veid: "YOUR_VEID_HERE"
  api_key: "YOUR_API_KEY_HERE"
  receive_id: "YOUR_RECEIVE_ID_HERE" # 接收消息的飞书 Open ID
```

## 数据处理说明

1. **流量计算**：
   - `plan_monthly_data_gb` = `plan_monthly_data` * `monthly_data_multiplier` / 1024 / 1024 / 1024
   - `data_counter_gb` = `data_counter` * `monthly_data_multiplier` / 1024 / 1024 / 1024
2. **时间格式**：`data_next_reset` (Unix Timestamp) 将被转换为本地时间字符串。

## 运行方式

```bash
/media/data/venv/bin/python tasks/vps_monitor/main.py
```

## 自动化调度 (Crontab)

建议每天早上 9 点执行：
```cron
0 9 * * * /media/data/venv/bin/python /media/data/git/feishu_tools/tasks/vps_monitor/main.py >> /var/log/vps_monitor.log 2>&1
```
