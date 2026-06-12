import lark_oapi as lark
from lark_oapi.api.im.v1 import *
import json
import logging
import requests

class FeishuBot:
    """
    飞书机器人集成类。
    支持两种模式：
    1. 应用模式：使用 app_id 和 app_secret，功能更强（发消息给个人、操作文档等）。
    2. Webhook 模式：仅需 webhook_url，用于简单的群组通知。
    """
    def __init__(self, app_id: str = None, app_secret: str = None, webhook_url: str = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.webhook_url = webhook_url
        self.client = None

        if app_id and app_secret:
            self.client = lark.Client.builder() \
                .app_id(app_id) \
                .app_secret(app_secret) \
                .log_level(lark.LogLevel.INFO) \
                .build()

    def send_text_to_chat(self, receive_id: str, content: str, receive_id_type: str = "open_id"):
        """
        应用模式：发送文本消息给指定接收者（用户或群聊）
        """
        if not self.client:
            logging.error("未初始化 App ID/Secret，无法使用应用模式发送消息")
            return None

        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(CreateMessageRequestBody.builder() \
                .receive_id(receive_id) \
                .msg_type("text") \
                .content(json.dumps({"text": content})) \
                .build()) \
            .build()

        response = self.client.im.v1.message.create(request)
        if not response.success():
            logging.error(f"发送消息失败: {response.code}, {response.msg}")
        return response

    def send_card_to_chat(self, receive_id: str, title: str, content: str = None, fields: list = None, status: str = "info", receive_id_type: str = "open_id", elements: list = None):
        """
        应用模式：发送卡片消息给指定接收者。支持内容正文、字段列表或完全自定义的 elements 列表 (支持卡片 2.0 协议)。
        """
        if not self.client:
            logging.error("未初始化 App ID/Secret")
            return None

        colors = {
            "info": "blue",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }
        header_template = colors.get(status, "blue")

        card_elements = []
        if elements is not None:
            card_elements.extend(elements)
        else:
            if content:
                card_elements.append({
                    "tag": "div",
                    "text": {"content": content, "tag": "lark_md"}
                })
            
            if fields:
                card_elements.append({
                    "tag": "div",
                    "fields": fields
                })

        card_elements.append({"tag": "hr"})
        card_elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "<font color='grey'>来自 Feishu Tools 自动化提醒</font>"
            }
        })

        # 使用卡片 2.0 JSON 协议，以支持高阶表格组件
        card_content = {
            "schema": "2.0",
            "header": {
                "template": header_template,
                "title": {"content": title, "tag": "plain_text"}
            },
            "body": {
                "elements": card_elements
            }
        }

        # 调试日志：打印发送给飞书的卡片完整 JSON 结构
        logging.info(f"发送的飞书卡片完整 JSON 结构:\n{json.dumps(card_content, indent=2, ensure_ascii=False)}")

        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(CreateMessageRequestBody.builder() \
                .receive_id(receive_id) \
                .msg_type("interactive") \
                .content(json.dumps(card_content)) \
                .build()) \
            .build()

        response = self.client.im.v1.message.create(request)
        if not response.success():
            logging.error(f"发送卡片消息失败: {response.code}, {response.msg}")
        return response

    def send_webhook_text(self, content: str):
        """
        Webhook 模式：发送纯文本消息
        """
        if not self.webhook_url:
            logging.error("未提供 Webhook URL")
            return None
            
        data = {
            "msg_type": "text",
            "content": {"text": content}
        }
        return self._post_webhook(data)

    def send_webhook_card(self, title: str, content: str, status: str = "info"):
        """
        Webhook 模式：发送卡片消息 (支持卡片 2.0 协议)
        """
        if not self.webhook_url:
            logging.error("未提供 Webhook URL")
            return None

        colors = {
            "info": "blue",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }
        header_template = colors.get(status, "blue")

        card = {
            "schema": "2.0",
            "header": {
                "template": header_template,
                "title": {"content": title, "tag": "plain_text"}
            },
            "body": {
                "elements": [
                    {
                        "tag": "div",
                        "text": {"content": content, "tag": "lark_md"}
                    },
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "<font color='grey'>来自 Feishu Tools 自动化提醒</font>"
                        }
                    }
                ]
            }
        }

        data = {
            "msg_type": "interactive",
            "card": card
        }
        return self._post_webhook(data)

    def _post_webhook(self, data: dict):
        try:
            resp = requests.post(
                self.webhook_url,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'}
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.error(f"Webhook 请求异常: {e}")
            return None
