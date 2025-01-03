import os
import json
from PySide6.QtWidgets import QMessageBox

class Config:
    """ユーザーが設定したパラメーターを管理するクラス"""
    _config = None

    @staticmethod
    def load_config(config_path = None):
        if Config._config is None:
            if config_path is None:
                config_path = Config.get_config_path()

            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        Config._config = json.load(f)
                except json.JSONDecodeError:
                    QMessageBox.warning(None, "エラー", f"無効な設定ファイルです。\n{config_path}")
                    Config._config = {}
            else:
                Config._config = {}
        return Config._config

    @staticmethod
    def get(key, default=None):
        config = Config.load_config()
        return config.get(key, default)
    
    @staticmethod
    def set(key, value):
        config = Config.load_config()
        config[key] = value
        Config.save_config(config)

    @staticmethod
    def save_config(config=None):
        """設定を保存する"""
        if config is None:
            config = Config._config
        try:
            with open(Config.get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            QMessageBox.critical(None, "エラー", f"設定ファイルの保存に失敗しました: {str(e)}")

    @staticmethod
    def get_config_directory():
        """固定されたディレクトリを取得"""
        try:
            base_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "KMMR_GameServer_Setting")
            if not os.path.exists(base_dir):
                os.makedirs(base_dir, exist_ok=True)
            return base_dir
        except Exception as e:
            QMessageBox.critical(None, "エラー", f"ディレクトリの作成または取得に失敗しました: {str(e)}")

    @staticmethod
    def get_config_path():
        """config.jsonのパスを取得"""
        return os.path.join(Config.get_config_directory(), "config.json")
