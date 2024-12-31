import os
import sys
import json
from PySide6.QtWidgets import QMessageBox

class AppConfig:
    """アプリケーション全体で共有される設定を管理するクラス"""
    _config = None

    @staticmethod
    def load_config():
        if AppConfig._config is None:
            internal_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../conf", "app.json")
            if os.path.exists(internal_config_path):
                try:
                    with open(internal_config_path, 'r', encoding='utf-8') as f:
                        AppConfig._config = json.load(f)
                except json.JSONDecodeError:
                    QMessageBox.warning(None, "エラー", "無効な設定ファイルです。")
                    AppConfig._config = {}
            else:
                AppConfig._config = {}
        return AppConfig._config

    @staticmethod
    def get(key, default=None):
        config = AppConfig.load_config()
        return config.get(key, default)

    @staticmethod
    def resource_path(relative_path):
        """PyInstallerで同梱されたリソースファイルの絶対パスを取得"""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.getcwd(), relative_path)