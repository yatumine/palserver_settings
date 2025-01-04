from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QLineEdit, QDialog, QComboBox, QMessageBox
from PySide6.QtCore import Qt
from plugins.plugin_base import PluginBase, PluginSettingsWindow
import requests
import json

class RestAPIPlugin(PluginBase):
    display_name = "REST API送信"  # クラスに表示名を定義

    def __init__(self):
        super().__init__()
        self.base_url = None
        self.window = None

        # 設定を取得
        self.config = self.get_default_config()
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 8212)
        self.base_url = f"http://{self.host}:{self.port}"

    def initialize(self, main_app):
        """プラグインをアプリケーションに登録"""
        self.main_app = main_app

    def create_window(self):
        """REST APIウィンドウを作成"""
        if not self.window:
            self.window = RestAPIWindow(self)
        return self.window
    
    def create_settings_window(self):
            return PluginSettingsWindow(self)
    
    def get_default_config(self):
        """
        RestAPIPlugin用のデフォルトコンフィグ
        """
        return {
            "host": "127.0.0.1",
            "port": 8212
        }

    def send_command(self, command: str, params: dict = None) -> dict:
        """
        REST APIを介してコマンドを送信
        :param command: 実行するコマンド
        :param params: コマンドに付随する追加パラメータ（オプション）
        :return: サーバーのレスポンス
        """
        try:
            url = f"{self.base_url}/command"
            payload = {
                "command": command,
                "params": params or {}
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"APIリクエストエラー: {e}")

    def get_status(self) -> dict:
        """
        サーバーの現在の状態を取得
        :return: サーバーの状態情報
        """
        try:
            url = f"{self.base_url}/status"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"APIリクエストエラー: {e}")

class RestAPIWindow(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin

        self.setWindowTitle("REST API コントロールパネル")
        self.setFixedSize(400, 300)

        # UIの初期化
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # コマンド入力フィールド
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("コマンドを入力してください")
        layout.addWidget(QLabel("コマンド:"))
        layout.addWidget(self.command_input)

        self.param_input = QLineEdit()
        self.param_input.setPlaceholderText("追加のパラメータ(JSON形式)を入力してください")
        layout.addWidget(QLabel("パラメータ:"))
        layout.addWidget(self.param_input)

        # ボタン
        send_button = QPushButton("送信")
        send_button.clicked.connect(self.on_send_command)
        layout.addWidget(send_button)

        status_button = QPushButton("ステータス取得")
        status_button.clicked.connect(self.on_get_status)
        layout.addWidget(status_button)

        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def on_send_command(self):
        """REST APIコマンドを送信"""
        command = self.command_input.text().strip()
        params_text = self.param_input.text().strip()

        try:
            params = json.loads(params_text) if params_text else {}
            response = self.plugin.send_command(command, params)
            QMessageBox.information(self, "REST API 結果", json.dumps(response, indent=4))
        except json.JSONDecodeError:
            QMessageBox.critical(self, "エラー", "パラメータはJSON形式で入力してください。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"REST APIエラー: {str(e)}")

    def on_get_status(self):
        """サーバーのステータスを取得"""
        try:
            status = self.plugin.get_status()
            QMessageBox.information(self, "サーバーステータス", json.dumps(status, indent=4))
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"ステータス取得エラー: {str(e)}")
