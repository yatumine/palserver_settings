from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QLineEdit, QDialog, QComboBox, QMessageBox
from PySide6.QtCore import Qt
from plugins.plugin_base import PluginBase, PluginSettingsWindow

import socket
import struct
import logging

class RCONPlugin(PluginBase):
    display_name = "RCON Command送信"  # プラグインの表示名を定義

    def __init__(self):
        super().__init__()
        self.client = None
        self.window = None

        # RCON設定を取得
        self.config = self.get_default_config()
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 25575)
        self.password = self.config.get("password", "")

    def initialize(self, main_app):
        """プラグインをアプリケーションに登録"""
        self.main_app = main_app

    def create_window(self):
        """RCONウィンドウを作成"""
        if not self.window:
            self.window = RCONWindow(self)
        return self.window
    
    def create_settings_window(self):
            return PluginSettingsWindow(self)

    def get_default_config(self):
        """
        RCONPlugin用のデフォルトコンフィグ
        """
        return {
            "host": "127.0.0.1",
            "port": 25575,
            "password": ""
        }

    def connect(self):
        """RCONサーバーに接続"""
        try:
            self.client = RCONClient(self.host, self.port, self.password)
            self.client.connect()
            self.client.authenticate()
        except Exception as e:
            raise ConnectionError(f"RCONの接続または認証に失敗しました: {e}")

    def send_command(self, command: str, additional_args: str = "") -> str:
        """RCONコマンドを送信"""
        if not self.client:
            self.connect()

        full_command = f"{command} {additional_args}".strip()
        return self.client.send_command(full_command)

    def close(self):
        """RCON接続を閉じる"""
        if self.client:
            self.client.close()
            self.client = None


class RCONWindow(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin

        self.setWindowTitle("RCONコントロールパネル")
        self.setFixedSize(400, 300)

        # UIの初期化
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        # コマンド入力フィールド
        self.command_selector = QComboBox()
        self.command_selector.addItems(["say", "kick", "ban", "whitelist", "help"])
        layout.addWidget(QLabel("RCONコマンド:"))
        layout.addWidget(self.command_selector)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("追加の引数やテキストを入力してください")
        layout.addWidget(QLabel("追加引数:"))
        layout.addWidget(self.command_input)

        # ボタン
        send_button = QPushButton("送信")
        send_button.clicked.connect(self.on_send_command)
        layout.addWidget(send_button)

        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def on_send_command(self):
        """RCONコマンドを送信"""
        command = self.command_selector.currentText()
        additional_args = self.command_input.text().strip()

        try:
            response = self.plugin.send_command(command, additional_args)
            QMessageBox.information(self, "RCON 結果", response)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"RCONエラー: {str(e)}")

class RCONClient:
    def __init__(self, host, port, password):
        self.host = host
        self.port = int(port)  # ポート番号を整数に変換
        self.password = password
        self.socket = None
        self.request_id = 1

        # RCON専用のロガーを設定
        self.logger = logging.getLogger("RCON")
        rcon_log_handler = logging.FileHandler("rcon.log")  # RCON専用のログファイル
        rcon_log_handler.setLevel(logging.DEBUG)
        rcon_log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(rcon_log_handler)
        self.logger.setLevel(logging.DEBUG)

    def connect(self):
        """サーバーに接続"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.logger.info("Connected to RCON server at %s:%d", self.host, self.port)
        except Exception as e:
            self.logger.error("Failed to connect to RCON server: %s", e)
            raise ConnectionError(f"RCONサーバーへの接続に失敗しました: {e}")

    def authenticate(self):
        """RCON認証"""
        self._send_packet(3, self.password)
        response = self._receive_packet()
        self.logger.debug("Authentication response: %s", response)
        if response["id"] == -1:
            raise PermissionError("RCON認証に失敗しました")

    def send_command(self, command):
        """RCONコマンドを送信"""
        self._send_packet(2, command)
        response = self._receive_packet()
        self.logger.debug("Command response: %s", response)
        return response["body"]

    def close(self):
        """接続を閉じる"""
        if self.socket:
            self.socket.close()
            self.logger.info("Disconnected from RCON server")

    def _send_packet(self, packet_type, body):
        """RCONプロトコルに従いパケットを送信"""
        payload = struct.pack(
            f"<ii{len(body.encode('utf-8')) + 1}sB",
            self.request_id,
            packet_type,
            body.encode("utf-8"),
            0,
        )
        length = struct.pack("<i", len(payload))
        packet = length + payload
        self.socket.send(packet)
        self.logger.debug("Sent packet: %s", packet)

    def _recv_all(self, size):
        """指定サイズ分のデータを受信"""
        buffer = b""
        while len(buffer) < size:
            packet = self.socket.recv(size - len(buffer))
            if not packet:
                raise ConnectionError("Connection closed by the server")
            buffer += packet
        self.logger.debug("Received raw data: %s", buffer)
        return buffer

    def _receive_packet(self):
        """サーバーからの応答を受け取る"""
        length_data = self._recv_all(4)
        length = struct.unpack("<i", length_data)[0]
        self.logger.debug("Received packet length: %d", length)

        if length < 10:  # ヘッダ+最低限のデータサイズ
            raise ValueError(f"Invalid packet length received: {length}")

        data = self._recv_all(length)
        self.logger.debug("Received packet data: %s", data)

        # データ分割
        header_format = "<ii"
        header_size = struct.calcsize(header_format)
        if len(data) < header_size:
            raise ValueError("Received data is smaller than expected header size.")

        request_id, packet_type = struct.unpack(header_format, data[:header_size])
        body = data[header_size:-2]  # 本体部分
        terminator = data[-2:]      # 終端のnullバイト

        if terminator != b'\x00\x00':
            raise ValueError("Packet terminator is invalid or missing.")

        return {
            "id": request_id,
            "type": packet_type,
            "body": body.decode("utf-8") if body else "",  # 空のボディを考慮
        }
