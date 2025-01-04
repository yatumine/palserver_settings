import logging
import os
import json
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QDialog, QMessageBox, QTextEdit
from PySide6.QtCore import Qt, QThread, Signal
import subprocess
from lib.appconfig import AppConfig
from lib.config import Config

class ServerUpdateWindow(QDialog):
    def __init__(self, parent=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        super().__init__(parent)
        self.setWindowTitle("サーバー設定")
        self.setFixedSize(400, 200)

        # config.json のパスを取得
        self.internal_config_path = Config.get_config_path()
        self.config = self.load_config()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)  # 縦軸の要素を上詰めに設定
        
        self.install_dir = AppConfig.get("install_dir", "")
        self.app_id = AppConfig.get("app_id", "")

        # インストールディレクトリの設定
        if os.path.exists(self.install_dir):
            self.status_label = QLabel("サーバーのアップデートを開始します。")
        else:
            self.status_label = QLabel("サーバーの新規インストールを開始します。")
        layout.addWidget(self.status_label)

        server_info = QLabel(f"■サーバー情報\nサーバーディレクトリ: {self.install_dir}\nアプリID: {self.app_id}")
        layout.addWidget(server_info)

        layout.addSpacing(20)
        update_button = QPushButton("処理開始")
        update_button.clicked.connect(self.run_update)
        layout.addWidget(update_button)

        self.setLayout(layout)

    def load_config(self):
        """config.json を読み込む"""
        if os.path.exists(self.internal_config_path):
            try:
                with open(self.internal_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "エラー", "無効な設定ファイルです。")
        return {}

    def run_update(self):
        """サーバーのアップデート処理を実行"""
        try:
            # 必要な設定値を取得
            steamcmd_path = self.config.get("steamcmd_path", "")
            if not steamcmd_path or not os.path.exists(os.path.join(steamcmd_path, "steamcmd.exe")):
                QMessageBox.critical(self, "エラー", "SteamCMD のパスが無効です。設定を確認してください。")
                return

            self.status_label.setText("処理中...")
            steamcmd_exe = os.path.join(steamcmd_path, "steamcmd.exe")
            cmd = f"{steamcmd_exe} +force_install_dir {self.install_dir} +login anonymous +app_update {self.app_id} validate +quit"
            QMessageBox.warning(None, "Notice", "cmd: " + cmd)
            subprocess.run(cmd, check=True)
        except Exception as e:
            if e.returncode == 7:
                QMessageBox.warning(None, "警告", "SteamCMD でエラーが発生しました: ステータスコード 7")
            else:
                QMessageBox.critical(None, "エラー", f"コマンドが失敗しました: ステータスコード {e.returncode}")

        QMessageBox.information(None, "成功", "コマンドが正常に実行されました！")


    def run_update_with_output_window(self):
        """コマンドを実行し、リアルタイムで別ウィンドウに出力"""
        # 必要な設定値を取得
        steamcmd_path = self.config.get("steamcmd_path", "")
        if not steamcmd_path or not os.path.exists(os.path.join(steamcmd_path, "steamcmd.exe")):
            QMessageBox.critical(self, "エラー", "SteamCMD のパスが無効です。設定を確認してください。")
            return

        steamcmd_exe = os.path.join(steamcmd_path, "steamcmd.exe")
        cmd = f"\"{steamcmd_exe}\" +force_install_dir \"{self.install_dir}\" +login anonymous +app_update {self.app_id} validate +quit"
        QMessageBox.warning(None, "Notice", "cmd: " + cmd)

        # 出力用ウィンドウを表示
        output_window = OutputWindow(self)
        output_window.show()

        # コマンドを非同期で実行
        self.command_thread = CommandThread(cmd, self)
        self.command_thread.output_received.connect(output_window.append_output)
        self.command_thread.finished_signal.connect(lambda code: self.handle_process_finished(code, output_window))
        self.command_thread.start()

class OutputWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("コマンド出力")
        self.resize(600, 400)

        layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)
        self.setLayout(layout)

    def append_output(self, text):
        self.output_text.append(text)

class CommandThread(QThread):
    output_received = Signal(str)  # 出力用シグナル
    finished_signal = Signal(int)  # 終了時のシグナル

    def __init__(self, cmd, parent=None):
        super().__init__(parent)
        self.cmd = cmd

    def run(self):
        try:
            process = subprocess.Popen(
                self.cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.output_received.emit(line.strip())

            self.finished_signal.emit(process.returncode)

        except Exception as e:
            self.output_received.emit(f"エラー: {str(e)}")
            self.finished_signal.emit(-1)
