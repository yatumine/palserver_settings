from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QDialog, QMessageBox
import subprocess

class ServerUpdateWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("サーバーアップデート")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()
        
        self.status_label = QLabel("サーバーのアップデートを開始します。")
        layout.addWidget(self.status_label)

        update_button = QPushButton("アップデート開始")
        update_button.clicked.connect(self.run_update)
        layout.addWidget(update_button)

        self.setLayout(layout)

    def run_update(self):
        """サーバーのアップデート処理を実行"""
        try:
            steamcmd_path = "C:\\steamcmd\\steamcmd.exe"
            install_dir = "C:\\palworld\\"
            app_id = "2394010"
            steam_login_id = "anonymous"

            cmd = [
                steamcmd_path,
                "+login", steam_login_id,
                "+force_install_dir", install_dir,
                "+app_update", app_id,
                "validate",
                "+quit"
            ]

            self.status_label.setText("アップデート中...")
            subprocess.run(cmd, check=True)
            QMessageBox.information(self, "成功", "サーバーアップデートが完了しました！")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "エラー", f"アップデートに失敗しました: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"予期しないエラーが発生しました: {str(e)}")
