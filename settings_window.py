import logging
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QMessageBox, QHBoxLayout, QDialog, QLineEdit, QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt
from lib.appconfig import AppConfig
from lib.config import Config
from game_settings import GameSettings

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.setWindowTitle("設定")
        self.setFixedSize(600, 550)  # ウィンドウサイズを固定
        self.setModal(True)  # モーダルウィンドウに設定

        # 親ウィンドウの中央に配置
        if parent:
            parent_geometry = parent.geometry()
            x = parent_geometry.x() + (parent_geometry.width() - self.width()) // 2
            y = parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            self.move(x, y)

        # 設定ファイルのパスを保存するための内部変数
        self.internal_config_path = Config.get_config_path()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)  # 縦軸の要素を上詰めに設定

        # ラベルを追加
        self.current_path_label = QLabel("設定ファイルのパス")
        self.current_path_label.setMargin(0)
        layout.addWidget(self.current_path_label)

        # ファイルパスフィールドとボタンを水平レイアウトにまとめる
        field_button_layout = QHBoxLayout()

        self.file_path_field = QLineEdit()
        self.file_path_field.setPlaceholderText("設定ファイルのパスを入力または選択")
        field_button_layout.addWidget(self.file_path_field)

        file_select_button = QPushButton("ファイル選択")
        file_select_button.clicked.connect(self.select_file)
        field_button_layout.addWidget(file_select_button)
        layout.addLayout(field_button_layout)
        layout.addSpacing(10)

        # Discord設定
        discord_label = QLabel("Discord Bot設定")
        discord_label.setMargin(0)
        font = discord_label.font()
        font.setPointSize(12)
        font.setBold(True)
        discord_label.setFont(font)
        layout.addWidget(discord_label)

        # discord_tokenのテキスト入力フィールドを追加
        self.discord_token_label = QLabel("Discord Botのトークン")
        self.discord_token_label.setMargin(0)
        layout.addWidget(self.discord_token_label)
        self.discord_token_field = QLineEdit()
        self.discord_token_field.setPlaceholderText("Discord Botのトークンを入力")
        layout.addWidget(self.discord_token_field)

        # discord_channel_idのテキスト入力フィールドを追加
        self.discord_channel_id_label = QLabel("Discord チャンネルID")
        self.discord_channel_id_label.setMargin(0)
        layout.addWidget(self.discord_channel_id_label)
        self.discord_channel_id_field = QLineEdit()
        self.discord_channel_id_field.setPlaceholderText("Discord チャンネルIDを入力")
        layout.addWidget(self.discord_channel_id_field)

        # DiscordBot起動時設定
        self.discord_autostart_label = QLabel("起動時にDiscordBotを起動する")
        self.discord_autostart_label.setMargin(0)
        layout.addWidget(self.discord_autostart_label)
        self.discord_autostart_checkbox = QCheckBox("起動する")
        layout.addWidget(self.discord_autostart_checkbox)
        layout.addSpacing(20)

        # 保存ボタン
        layout.addSpacing(30)
        save_button = QPushButton("保存して戻る")
        save_button.clicked.connect(self.save_and_return)
        layout.addWidget(save_button)

        self.setLayout(layout)
        self.load_settings()

    def load_settings(self):
        """設定ファイルからデータを読み込む"""
        self.file_path_field.setText(Config.get("settings_file_path", ""))
        self.discord_token_field.setText(Config.get("discord_token", ""))
        self.discord_channel_id_field.setText(Config.get("discord_channel_id", ""))
        self.discord_autostart_checkbox.setChecked(Config.get("discord_autostart", False))

    def select_file(self):
        """ファイル選択ダイアログを表示"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "設定ファイルを選択", "", "INIファイル (*.ini);;すべてのファイル (*)"
        )
        if file_path:
            self.file_path_field.setText(file_path)

    def save_and_return(self):
        """設定ファイルへ保存し、ウィンドウを閉じる"""
        # Discord設定を保存
        Config.set("discord_token", self.discord_token_field.text())
        Config.set("discord_channel_id", self.discord_channel_id_field.text())
        Config.set("discord_autostart", self.discord_autostart_checkbox.isChecked())

        # ファイルパスを保存
        new_path = self.file_path_field.text()
        if not new_path:
            QMessageBox.warning(self, "エラー", "有効なファイルパスを選択または入力してください。")
            return

        try:
            Config.set("settings_file_path", new_path)
            QMessageBox.information(self, "成功", "設定が正常に保存されました。")

            # 親ウィンドウをリロード
            if self.parent():
                if isinstance(self.parent(), GameSettings):
                    self.parent().reload_settings()

            self.accept()  # モーダルダイアログを閉じる
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")

    def closeEvent(self, event):
        """ウィンドウが閉じられるときに実行される処理"""
        if self.parent():
            if isinstance(self.parent(), GameSettings):
                self.parent().reload_settings()

if __name__ == "__main__":
    try:
        from PySide6.QtWidgets import QApplication
        import sys

        app = QApplication(sys.argv)
        main_window = SettingsWindow()
        main_window.show()
        sys.exit(app.exec())
    except Exception as e:
        # trace
        logging.error(f"Error occurred: {e}")
        QMessageBox.critical(None, "エラー", f"エラーが発生しました: {e}")
