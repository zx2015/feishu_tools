import yaml
import os
import logging

class Config:
    """
    统一配置加载类
    """
    def __init__(self, config_path: str = None):
        # 默认定位到项目根目录下的 config.yaml
        if config_path is None:
            # 获取当前文件所在目录的上一级目录（即项目根目录）
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config.yaml")
        
        self.config_path = config_path
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.config_path):
            logging.warning(f"配置文件不存在: {self.config_path}，尝试检查模板文件。")
            template_path = self.config_path + ".template"
            if os.path.exists(template_path):
                logging.info(f"发现模板文件: {template_path}，请根据模板创建 config.yaml")
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logging.error(f"加载配置文件出错: {e}")
            return {}

    def get(self, key, default=None):
        """
        支持嵌套 key 读取，例如 get('feishu.app_id')
        """
        keys = key.split('.')
        value = self.data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    @property
    def feishu_app_id(self):
        return self.get('feishu.app_id')

    @property
    def feishu_app_secret(self):
        return self.get('feishu.app_secret')

    @property
    def feishu_webhook_url(self):
        return self.get('feishu.webhook_url')

    @property
    def log_level(self):
        return self.get('settings.log_level', 'INFO')
