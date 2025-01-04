from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QLineEdit, QDialog, QComboBox, QTextEdit, QMessageBox
from PySide6.QtCore import Qt
from plugins.plugin_base import PluginBase, PluginSettingsWindow
import requests
import json

class RestAPIPlugin(PluginBase):
    display_name = "REST API送信"

    def __init__(self):
        super().__init__()
        self.base_url = None
        self.window = None

        # 設定を取得
        self.config = self.get_default_config()
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 8212)
        self.base_url = f"http://{self.host}:{self.port}/v1/api/"

    def initialize(self, main_app):
        self.main_app = main_app

    def create_window(self):
        if not self.window:
            self.window = RestAPIWindow(self)
        return self.window

    def create_settings_window(self):
        return PluginSettingsWindow(self)

    def get_default_config(self):
        return {
            "host": "127.0.0.1",
            "port": 8212
        }

    def send_command(self, endpoint: str, params: dict = None) -> dict:
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.post(url, json=params or {})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"APIリクエストエラー: {e}")

class RestAPIWindow(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin

        self.setWindowTitle("REST API コントロールパネル")
        self.setFixedSize(400, 500)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # コマンド選択
        self.command_selector = QComboBox()
        commands = [
            {"endpoint": "info", "display": "サーバー情報取得", "template": "{}"},
            {"endpoint": "players", "display": "プレイヤー一覧取得", "template": "{}"},
            {"endpoint": "announce", "display": "アナウンス送信", "template": "{\n  \"message\": \"Hello, Palworld!\"\n}"}
        ]
        for command in commands:
            self.command_selector.addItem(command["display"], command)

        self.command_selector.currentIndexChanged.connect(self.update_param_template)
        layout.addWidget(QLabel("コマンドを選択:"))
        layout.addWidget(self.command_selector)

        # パラメータ入力
        self.param_input = QTextEdit()
        self.param_input.setPlaceholderText("パラメータをJSON形式で記入してください")
        layout.addWidget(QLabel("パラメータ:"))
        layout.addWidget(self.param_input)

        # パラメータフォーマット表示
        self.param_format_label = QLabel("例: {\"key\": \"value\"}")
        layout.addWidget(QLabel("パラメータフォーマット:"))
        layout.addWidget(self.param_format_label)

        # ボタン
        send_button = QPushButton("送信")
        send_button.clicked.connect(self.on_send_command)
        layout.addWidget(send_button)

        status_button = QPushButton("閉じる")
        status_button.clicked.connect(self.close)
        layout.addWidget(status_button)

        self.setLayout(layout)
        self.update_param_template()  # 初期テンプレート設定

    def update_param_template(self):
        current_command = self.command_selector.currentData()
        if current_command:
            self.param_input.setText(current_command.get("template", ""))

    def on_send_command(self):
        current_command = self.command_selector.currentData()
        if not current_command:
            QMessageBox.critical(self, "エラー", "有効なコマンドを選択してください。")
            return

        endpoint = current_command["endpoint"]
        params_text = self.param_input.toPlainText().strip()

        try:
            params = json.loads(params_text) if params_text else {}
            response = self.plugin.send_command(endpoint, params)
            QMessageBox.information(self, "REST API 結果", json.dumps(response, indent=4))
        except json.JSONDecodeError:
            QMessageBox.critical(self, "エラー", "パラメータはJSON形式で入力してください。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"REST APIエラー: {str(e)}")
