import json
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QMessageBox, QHBoxLayout, QDialog, QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt
import os
from lib.appconfig import AppConfig
from lib.config import Config

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setFixedSize(600, 175)  # ウィンドウサイズを固定
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
        layout.addSpacing(20)

        # 未定義の設定を確認するボタンを追加
        compare_button = QPushButton("未定義の設定を確認する")
        compare_button.clicked.connect(self.open_comparison_window)
        layout.addWidget(compare_button)

        # 保存ボタン
        save_button = QPushButton("保存して戻る")
        save_button.clicked.connect(self.save_and_return)
        layout.addWidget(save_button)

        self.setLayout(layout)
        self.load_current_path()

    def load_current_path(self):
        """設定ファイルから表示用データを読み込む"""
        self.file_path_field.setText(Config.get("settings_file_path", ""))

    def select_file(self):
        """ファイル選択ダイアログを表示"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "設定ファイルを選択", "", "INIファイル (*.ini);;すべてのファイル (*)"
        )
        if file_path:
            self.file_path_field.setText(file_path)

    def save_and_return(self):
        """設定ファイルのパスを保存し、ウィンドウを閉じる"""
        new_path = self.file_path_field.text()
        if not new_path:
            QMessageBox.warning(self, "エラー", "有効なファイルパスを選択または入力してください。")
            return

        try:
            Config.set("settings_file_path", new_path)
            QMessageBox.information(self, "成功", "設定が正常に保存されました。")

            # 親ウィンドウをリロード
            if self.parent():
                self.parent().load_config()

            self.accept()  # モーダルダイアログを閉じる
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")

    def open_comparison_window(self):
        """未定義の設定を確認する"""
        try:
            from settings_comparison_window import SettingsComparisonWindow
            comparison_window = SettingsComparisonWindow(parent=self)
            comparison_window.exec()
        except ImportError as e:
            QMessageBox.critical(self, "エラー", f"未定義の設定を確認するウィンドウを開けません: {e}")


    def closeEvent(self, event):
        """ウィンドウが閉じられるときに実行される処理"""
        """親画面をリロードする"""
        if self.parent():
            self.parent().reload_settings()
        else:
            QMessageBox.warning(self, "エラー", "親ウィンドウが設定されていません！")

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    main_window = SettingsWindow()
    main_window.show()
    sys.exit(app.exec())
