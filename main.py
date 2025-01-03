import os
import sys
import logging
import subprocess
import psutil
import json
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QPushButton, 
    QWidget, QMessageBox, QFileDialog, QMainWindow,
    QToolButton
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
import qtawesome as qta
import requests
import zipfile
import asyncio
from lib.server_control import start_server, stop_server, check_server_status, check_memory_usage
from lib.appconfig import AppConfig
from lib.config import Config
from discord_bot import DiscordBot

# ロギング設定
logging.basicConfig(
    filename="application.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

class SettingsApp(QMainWindow):
    def __init__(self):
        super().__init__()
        logging.info("initializing SettingsApp...")

        # アプリケーションアイコンを設定
        app_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "256.ico")
        icon = QIcon(app_icon_path)
        if icon.isNull():
            QMessageBox.warning(None, "エラー", "アイコンの読み込みに失敗しました: " + app_icon_path)
            logging.warning(f"Failed to load application icon from {app_icon_path}")
        self.setWindowIcon(icon)

        logging.info("loading config...")
        self.server_path = AppConfig.get("install_dir")             # ゲームサーバーのパス（実行ファイルを含まない）
        self.server_exe = AppConfig.get("server_exe")               # EXEファイル名
        self.server_cmd_exe = AppConfig.get("server_cmd_exe")       # EXEファイル名
        self.server_name = self.server_exe.split(".")[0]            # サーバー名（EXEファイル名から拡張子を除いたもの）
        self.discord_bot_thread  = None
        self.internal_config_path = Config.get_config_path()
        self.config = self.load_config()

        # steamcmd の設定を確認
        logging.info("checking and setting up steamcmd...")
        self.check_and_setup_steamcmd()

        logging.info("initializing UI...")
        self.init_ui()

        # 起動時にDiscordBotを起動するが有効なら起動
        if Config.get("discord_autostart", False):
            self.on_start_discord_bot()

        logging.info("SettingsApp initialized.")


    def load_config(self):
        """設定ファイルを読み込む"""
        if os.path.exists(self.internal_config_path):
            try:
                with open(self.internal_config_path, 'r', encoding='utf-8') as f:
                    logging.info("loading config from " + self.internal_config_path)
                    return json.load(f)
            except json.JSONDecodeError:
                logging.error("invalid config file. creating new config...")
                QMessageBox.warning(None, "エラー", "無効な設定ファイルです。新しい設定を作成します。")
        # デフォルトの設定を作成
        default_config = {
            "steamcmd_path": ""
        }
        Config.save_config(default_config)
        QMessageBox.information(None, "成功", "config.json を初期化しました。")
        logging.info("created new config file.")
        return default_config

    def open_settings_window(self):
        """設定画面を開く"""
        try:
            logging.info("opening settings window...")
            from settings_window import SettingsWindow
            self.settings_window = SettingsWindow(parent=self)
            self.settings_window.show()
        except ImportError:
            QMessageBox.critical(self, "エラー", "設定ウィンドウモジュールを読み込めませんでした。")
            logging.error("failed to open settings window.")

    def open_update_window(self):
        logging.info("opening update window...")
        from update_server import ServerUpdateWindow
        update_window = ServerUpdateWindow(self)
        update_window.exec()

    def open_gamesetting_window(self):
        logging.info("opening game settings window...")
        from game_settings import GameSettings
        window = GameSettings(self)
        window.exec()

    def init_ui(self):
        self.setWindowTitle("PalWorld 設定エディタ")
        self.resize(285, 200)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignTop)  # 縦軸の要素を上詰めに設定

        # 設定ボタン
        settings_button = QToolButton()
        icon = qta.icon('ph.gear-six-fill')
        settings_button.setIcon(icon)
        settings_button.clicked.connect(self.open_settings_window)
        layout.addWidget(settings_button)

        update_button = QPushButton("サーバーインストール（アップデート）")
        update_button.clicked.connect(self.open_update_window)
        layout.addWidget(update_button)

        setting_button = QPushButton("ゲーム設定")
        setting_button.clicked.connect(self.open_gamesetting_window)
        layout.addWidget(setting_button)

        # Discord Bot 起動ボタンを追加
        start_bot_button = QPushButton("Discord Bot 起動")
        start_bot_button.clicked.connect(self.on_start_discord_bot)
        layout.addWidget(start_bot_button)

        # サーバー起動ボタンを追加
        start_server_button = QPushButton("サーバーを起動")
        start_server_button.clicked.connect(self.on_start_server_clicked)
        layout.addWidget(start_server_button)

        # サーバー停止ボタンを追加
        stop_server_button = QPushButton("サーバーを停止")
        stop_server_button.clicked.connect(self.on_stop_server_clicked)
        layout.addWidget(stop_server_button)

        self.setCentralWidget(central_widget)

    def check_and_setup_steamcmd(self):
        """SteamCMDのディレクトリを確認し、必要なら設定"""
        steamcmd_path = self.config.get("steamcmd_path", "")

        if not steamcmd_path or not os.path.exists(steamcmd_path):
            reply = QMessageBox.question(
                self,
                "SteamCMD 設定",
                "SteamCMD のディレクトリが設定されていません。\n\nSteamCMDからインストールしますか？\n  「Yes」 を選択すると C:\\steamcmd にインストールされます。\n  「No」 を選択するとディレクトリ選択ダイアログが表示されます。",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.download_and_install_steamcmd()
                steamcmd_path = "C:\\steamcmd"
            else:
                steamcmd_path = self.ask_user_for_steamcmd_path()

            if steamcmd_path:
                self.save_steamcmd_path(steamcmd_path)
            else:
                QMessageBox.warning(None, "警告", "SteamCMD の設定が完了していません。")

    def download_and_install_steamcmd(self):
        """SteamCMD をダウンロードして C:\\steamcmd にインストール"""
        url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
        install_dir = "C:\\steamcmd"

        try:
            response = requests.get(url, stream=True)
            zip_path = os.path.join(install_dir, "steamcmd.zip")
            os.makedirs(install_dir, exist_ok=True)

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(install_dir)

            os.remove(zip_path)
            QMessageBox.information(None, "成功", "SteamCMD をインストールしました！")

        except Exception as e:
            QMessageBox.critical(None, "エラー", f"SteamCMD のインストールに失敗しました: {str(e)}")
            logging.error(f"Failed to download and install SteamCMD: {e}")

    def ask_user_for_steamcmd_path(self):
        """ユーザーに SteamCMD のパスを選択させる"""
        dir_path = QFileDialog.getExistingDirectory(None, "SteamCMD ディレクトリを選択")
        if dir_path:
            return dir_path
        else:
            QMessageBox.warning(None, "警告", "SteamCMD のパスが選択されていません。")
            return None

    def save_steamcmd_path(self, path):
        """SteamCMD のパスを保存"""
        self.config["steamcmd_path"] = path
        Config.save_config(self.config)
        QMessageBox.information(None, "成功", "SteamCMD のパスを保存しました！")

    def is_discord_bot_running(self) -> bool:
        """
        discord_bot.pyが起動しているかを判定する関数
        Returns:
            bool: 起動していればTrue、起動していなければFalse
        """
        for proc in psutil.process_iter(attrs=['cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any("discord_bot.py" in arg for arg in cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    def check_discord_settings(self):
        """
        Discord設定が行われているかチェックする関数
        設定が完了していない場合、エラーメッセージを表示し、設定画面を開く。
        """
        # DiscordトークンとチャンネルIDの取得
        discord_token = Config.get("discord_token")
        discord_channel_id = Config.get("discord_channel_id")
        
        if not discord_token or not discord_channel_id:
            QMessageBox.warning(
                self,
                "エラー",
                "Discordの設定が完了していません。\n設定画面から設定を行ってください。"
            )
            # 設定画面を開く
            self.open_settings_window()

    def on_start_discord_bot(self):
        """Discord Bot を非同期で起動"""
        discord_token = Config.get("discord_token")
        discord_channel_id = Config.get("discord_channel_id")
        server_path = AppConfig.get("install_dir")
        server_exe = AppConfig.get("server_exe")
        server_cmd_exe = AppConfig.get("server_cmd_exe")

        if not discord_token or not discord_channel_id:
            QMessageBox.warning(self, "エラー", "Discordの設定が完了していません。設定画面から設定を行ってください。")
            logging.error("Discord settings are not configured.")
            return

        if self.discord_bot_thread and self.discord_bot_thread.isRunning():
            QMessageBox.warning(self, "エラー", "Discord Bot は既に起動しています。")
            logging.warning("Discord Bot is already running.")
            return

        logging.info("starting Discord Bot...")
        try:
            self.discord_bot_thread = DiscordBotThread(discord_token, discord_channel_id, server_path, server_exe, server_cmd_exe)
            self.discord_bot_thread.error_signal.connect(self.on_discord_bot_error)
            self.discord_bot_thread.start()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"Discord Bot 起動中にエラーが発生しました: {e}")
            logging.error(f"Failed to start Discord Bot: {e}")
        QMessageBox.information(self, "Discord Bot", "Discord Bot を起動しました。")

    def on_discord_bot_error(self, error_message):
        """エラー発生時の処理"""
        QMessageBox.critical(self, "エラー", error_message)
        logging.info("Discord Bot error: " + error_message)

            
    def on_start_server_clicked(self):
        """サーバー起動ボタンがクリックされたときの処理"""
        # Discord設定が行われているかチェックする
        self.check_discord_settings()

        # Discord Botが既に起動しているかチェックする
        if self.is_discord_bot_running():
            QMessageBox.warning(self, "エラー", "Discord Bot は既に起動しています。")
            return

        # discord設定が行われているかチェックする
        if not Config.get("discord_token") or not Config.get("discord_channel_id"):
            QMessageBox.warning(self, "エラー", "Discordの設定が完了していません。\n設定画面から設定を行ってください。")
            # 設定画面を開く
            self.open_settings_window()

        try:
            # サーバーが既に起動しているか確認
            if asyncio.run(check_server_status()):
                QMessageBox.warning(self, "サーバー重複起動", f"{self.server_exe} は既に起動しています。")
                logging.warning(f"{self.server_exe} is already running.")
                return

            # 非同期関数を同期的に実行
            asyncio.run(self.start_server_async())
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"サーバー起動中にエラーが発生しました: {e}")

    async def start_server_async(self):
        """サーバー起動処理"""
        result = await start_server(self.server_path, self.server_exe)
        if result:
            QMessageBox.information(self, "サーバー起動", result.title)
            logging.info(f"Server started successfully: {self.server_exe}")
        else:
            QMessageBox.warning(self, "サーバー起動失敗", f"{self.server_exe} を起動できませんでした。")
            logging.warning(f"Failed to start server: {self.server_exe}")

    def on_stop_server_clicked(self):
        """サーバー起動ボタンがクリックされたときの処理"""
        # Discord設定が行われているかチェックする
        self.check_discord_settings()

        # Discord Botが既に起動しているかチェックする
        if self.is_discord_bot_running():
            QMessageBox.warning(self, "エラー", "Discord Bot は既に起動しています。")
            return
        
        try:
            # 非同期関数を同期的に実行
            asyncio.run(self.stop_server_async())
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"サーバー起動中にエラーが発生しました: {e}")

    async def stop_server_async(self):
        """サーバー起動処理"""
        result = await stop_server(self.server_cmd_exe, self.server_exe)
        QMessageBox.information(self, "サーバー起動", result.title)

class DiscordBotThread(QThread):
    error_signal = Signal(str)

    def __init__(self, token, channel_id, server_path, server_exe, server_cmd_exe):
        super().__init__()
        self.discord_bot = DiscordBot(token, channel_id, server_path, server_exe, server_cmd_exe)

    def run(self):
        try:
            self.discord_bot.start()
        except Exception as e:
            error_message = f"DiscordBotThread error: {e}"
            logging.error(error_message)
            self.error_signal.emit(error_message)


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = SettingsApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        # trace
        logging.error(f"Error occurred: {e}")
        QMessageBox.critical(None, "エラー", f"エラーが発生しました: {e}")
        sys.exit(1)
