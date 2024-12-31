import os
import sys
import json
import configparser
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout,
    QWidget, QMessageBox, QFileDialog, QScrollArea, QMainWindow, QComboBox,
    QToolTip, QHBoxLayout, QToolButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QDoubleValidator, QIcon
import qtawesome as qta
import requests
import zipfile
import shutil
from lib.appconfig import AppConfig
from lib.config import Config

class SettingsApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # アプリケーションアイコンを設定
        app_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "256.ico")
        icon = QIcon(app_icon_path)
        if icon.isNull():
            QMessageBox.warning(None, "エラー", "アイコンの読み込みに失敗しました: " + app_icon_path)
        self.setWindowIcon(icon)

        self.internal_config_path = Config.get_config_path()
        self.config = self.load_config()

        # steamcmd の設定を確認
        self.check_and_setup_steamcmd()

        # ConfigParser をカスタマイズ
        self.init_ui()

    def load_config(self):
        """設定ファイルを読み込む"""
        if os.path.exists(self.internal_config_path):
            try:
                with open(self.internal_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                QMessageBox.warning(None, "エラー", "無効な設定ファイルです。新しい設定を作成します。")
        # デフォルトの設定を作成
        default_config = {
            "steamcmd_path": ""
        }
        Config.save_config(default_config)
        QMessageBox.information(None, "成功", "config.json を初期化しました。")
        return default_config

    def open_settings_window(self):
        """設定画面を開く"""
        try:
            from settings_window import SettingsWindow
            self.settings_window = SettingsWindow(parent=self)
            self.settings_window.show()
        except ImportError:
            QMessageBox.critical(self, "エラー", "設定ウィンドウモジュールを読み込めませんでした。")

    def open_update_window(self):
        from update_server import ServerUpdateWindow
        update_window = ServerUpdateWindow(self)
        update_window.exec()

    def open_gamesetting_window(self):
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SettingsApp()
    window.show()
    sys.exit(app.exec())
