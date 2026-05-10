# 飞书自动化工具集 (Feishu Tools)

本项目是一系列基于飞书（Lark）的自动化应用工具。主要功能是自动完成特定任务，并利用飞书机器人的接口向用户发送执行结果反馈。

## 项目架构与规范

### 1. 目录结构

```text
/media/data/git/feishu_tools/
├── common/             # 公共组件与工具函数
│   ├── __init__.py
│   ├── feishu.py       # 飞书机器人接口封装
│   └── config.py       # 配置加载逻辑
├── tasks/              # 自动化任务集（每个任务独立目录）
│   ├── task_example/   # 任务示例
│   │   ├── README.md   # 任务说明与配置指南
│   │   └── main.py     # 任务入口脚本
│   └── ...
├── config.yaml         # 统一配置文件（包含机器人 Webhook、API Key 等）
├── requirements.txt    # 项目依赖
├── GEMINI.md           # 代理指令与规范（本文件）
├── TODO.md             # 任务清单
└── .learnings/         # 知识沉淀（本地，不入库）
```

### 2. 开发规范

- **任务独立性**：每个任务必须拥有自己的独立目录，并在目录下包含 `README.md`，说明任务功能、执行逻辑及特定配置。
- **公共代码复用**：所有跨任务共用的函数（如飞书消息发送、统一日志处理、配置文件读取等）必须放在 `common/` 目录下。
- **配置管理**：项目使用根目录下的 `config.yaml` 进行统一配置。严禁在代码中硬编码敏感信息（如 Webhook 地址、Token 等）。
- **反馈机制**：任务执行完成后，**必须**调用 `common/feishu.py` 中的接口，向指定的飞书群组或用户发送任务报告。
- **消息格式**：所有反馈消息**必须优先使用卡片消息 (Interactive Card)** 发送，以提供更好的视觉展示（如颜色标识状态、结构化内容等），严禁使用纯文本发送关键通知。

### 3. 运行环境

- **Python 版本**：Python 3.x
- **虚拟环境**：统一使用 `/media/data/venv` 下的虚拟环境。
- **安装依赖**：
  ```bash
  /media/data/venv/bin/pip install -r requirements.txt
  ```
- **执行任务**：
  ```bash
  /media/data/venv/bin/python tasks/task_name/main.py
  ```

### 4. 自动调度 (Crontab)

任务支持通过 `crontab` 进行自动调度。配置示例：
```cron
# 每天早上 9 点运行某个任务
0 9 * * * /media/data/venv/bin/python /media/data/git/feishu_tools/tasks/task_name/main.py >> /var/log/feishu_tools_task.log 2>&1
```

## 代理特殊指令

- **创建新任务**：当用户要求添加新功能时，应在 `tasks/` 下新建目录，并同步编写 `README.md`。
- **环境检查**：在运行或测试代码前，优先确认 `/media/data/venv` 环境是否可用。
- **知识沉淀**：严格遵守全局 `GEMINI.md` 中的知识沉淀规则，将飞书 API 调用经验、配置技巧记录在 `.learnings/` 中。
