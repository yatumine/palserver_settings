from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QLineEdit, QDialog, QComboBox, QTextEdit, QMessageBox
from PySide6.QtCore import Qt
from plugins.plugin_base import PluginBase, PluginSettingsWindow
import requests
import json
import base64
import logging

class RestAPIPlugin(PluginBase):
    display_name = "REST API送信"

    def __init__(self):
        super().__init__()
        self.base_url = None
        self.window = None

        # 設定を取得
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 8212)
        self.admin_password = self.config.get("admin_password", None)
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
            "port": 8212,
            "admin_password": None
        }

    def send_command(self, endpoint: str, method: str, params: dict = None) -> dict:
        try:
            url = f"{self.base_url}{endpoint}"
            headers = {
                'Accept': 'application/json'
            }

            if self.admin_password:
                auth_string = f"admin:{self.admin_password}"
                auth_encoded = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
                headers['Authorization'] = f"Basic {auth_encoded}"

            self.logger.info(f"Sending REST API request to {url} with method {method} and params {params} and headers {headers}")
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=params or {})
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()

            # レスポンスが空かどうかをチェック
            if not response.text.strip():
                return {"message": "空のレスポンスが返されました"}

            # JSON形式かどうかを判定
            try:
                # responseがOKだけの場合、メッセージのみ返す
                self.logger.info(f"レスポンス: {response.text.strip()}", exc_info=True)
                if response.text.strip() == "OK":
                    return {"message": "OK"}
                return response.json()
            except json.JSONDecodeError:
                self.logger.error(f"レスポンスがJSON形式ではありません: {response.text}", exc_info=True)
                return {"message": "レスポンスがJSON形式ではありません", "raw_response": response.text}

        except requests.exceptions.RequestException as e:
            self.logger.error(f"REST APIリクエストエラー: {str(e)}", exc_info=True)
            raise ConnectionError(f"APIリクエストエラー: {e}")

class RestAPIWindow(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin

        # 専用のロガーを設定
        self.logger = logging.getLogger("RESTAPI")
        rcon_log_handler = logging.FileHandler("restapi.log")  # 専用のログファイル
        rcon_log_handler.setLevel(logging.DEBUG)
        rcon_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(rcon_log_handler)
        self.logger.setLevel(logging.DEBUG)

        self.setWindowTitle("REST API コントロールパネル")
        self.setFixedSize(400, 500)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # コマンド選択
        self.command_selector = QComboBox()
        commands = [
            {"endpoint": "info", "display": "サーバー情報を取得", "template": "{}", "method": "GET"},
            {"endpoint": "players", "display": "プレイヤー一覧を取得", "template": "{}", "method": "GET"},
            {"endpoint": "settings", "display": "サーバー設定を取得", "template": "{}", "method": "GET"},
            {"endpoint": "metrics", "display": "サーバー メトリックを取得", "template": "{}", "method": "GET"},
            {"endpoint": "announce", "display": "アナウンス送信", "template": "{\n  \"message\": \"アナウンス：\"\n}", "method": "POST"}
        ]
        for command in commands:
            self.command_selector.addItem(f"{command['display']}({command['method']})", command)

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
        method = current_command["method"]
        params_text = self.param_input.toPlainText().strip()

        try:
            params = json.loads(params_text) if params_text else {}
            response = self.plugin.send_command(endpoint, method, params)
            QMessageBox.information(self, "REST API 結果", json.dumps(response, indent=4, ensure_ascii=False))
            self.logger.info(f"REST API response: {response.get('message', response)}")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "エラー", "パラメータはJSON形式で入力してください。")
        except Exception as e:
            # エラー行情報をログに記録
            self.logger.error(f"REST APIエラー: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "エラー", f"REST APIエラー: {str(e)}")
