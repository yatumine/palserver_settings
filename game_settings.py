import os
import sys
import json
import configparser
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout,
    QWidget, QMessageBox, QFileDialog, QScrollArea, QDialog, QComboBox,
    QToolTip, QHBoxLayout, QToolButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QDoubleValidator, QIcon
import qtawesome as qta
from lib.appconfig import AppConfig
from lib.config import Config

class GameSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PalWorld 設定エディタ")
        self.setFixedSize(800, 600)
        self.setModal(True)  # モーダルウィンドウに設定

        self.key_map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conf", "setting_key_map.json")
        self.file_path = self.load_settings_file_path()

        self.setting_section = AppConfig.get("setting_section")
        self.option_settings_key = AppConfig.get("option_settings_key")

        # ConfigParser をカスタマイズ
        self.config = configparser.RawConfigParser()
        self.config.optionxform = str  # キーの小文字変換を無効化
        self.key_map = self.load_key_map()
        self.inputs = {}
        self.filtered_keys = []  # 検索フィルタされたキー
        self.init_ui()

    def load_settings_file_path(self):
        """設定ファイルパスを内部設定から読み込む。存在しない場合はユーザーに選択させる。"""
        try:
            file_path = Config.get("settings_file_path")
            # 空文字か判定する
            if file_path:
                return file_path
        except json.JSONDecodeError:
            QMessageBox.warning(self, "エラー", "無効な設定ファイルが検出されました。設定をリセットします。")

        QMessageBox.information(self, "情報", f"初回起動です。{AppConfig.get('inifile_name', 'INI')}ファイルを選択してください。")
        return self.ask_user_for_file_path()

    def ask_user_for_file_path(self):
        """ユーザーにファイルパスを指定させ、内部設定に保存する。"""
        default_directory = AppConfig.get('install_dir', os.path.expanduser("~"))  # 初期ディレクトリを指定
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"{AppConfig.get('inifile_name', 'INI')}ファイルを選択",
            default_directory,  # 初期ディレクトリ
            "INI Files (*.ini);;All Files (*)"
        )
        if file_path:
            self.save_settings_file_path(file_path)
            return file_path
        else:
            QMessageBox.critical(self, "エラー", "ファイルが選択されていません。終了します。")
            exit(1)

    def save_settings_file_path(self, file_path):
        """指定された設定ファイルパスを内部設定に保存する。"""
        try:
            Config.set("settings_file_path", file_path)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {str(e)}")

    def load_key_map(self):
        """Keyマッピングファイルを読み込む。存在しない場合は空の辞書を返す。"""
        if os.path.exists(self.key_map_path):
            try:
                with open(self.key_map_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "エラー", "無効な setting_key_map.json が検出されました。キーのマッピングなしで続行します。")
        return {}

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)  # 縦軸の要素を上詰めに設定

        search_layout = QHBoxLayout()
        search_label = QLabel("検索:")
        self.search_field = QLineEdit()
        self.search_field.textChanged.connect(self.apply_filter)

        settings_button = QToolButton()
        icon = qta.icon('ph.gear-six-fill')
        settings_button.setIcon(icon)
        settings_button.clicked.connect(self.open_settings_window)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_field)
        search_layout.addWidget(settings_button)
        layout.addLayout(search_layout)

        self.scroll_area = QScrollArea()
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)  # 縦軸の要素を上詰めに設定
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)

        layout.addWidget(self.scroll_area)

        save_button = QPushButton("設定を保存")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.load_settings()

    def open_settings_window(self):
        """設定画面を開く"""
        try:
            from settings_window import SettingsWindow
            self.settings_window = SettingsWindow(parent=self)
            self.settings_window.show()
        except ImportError:
            QMessageBox.critical(self, "エラー", "設定ウィンドウモジュールを読み込めませんでした。")

    def apply_filter(self):
        """検索フィルタを適用"""
        self.update_form()

    def update_form(self):
        """フォームを更新"""
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.inputs.clear()

        if self.setting_section in self.config:
            settings = self.config[self.setting_section]
            option_settings = settings.get(self.option_settings_key, None)

            if option_settings:
                option_items = option_settings.strip('()').split(',')
                self.filtered_keys = []
                for item in option_items:
                    if '=' in item:
                        key, value = item.split('=')
                        key = key.strip()
                        key_info = self.key_map.get(key, {})
                        if key_info.get("hidden", False):
                            continue  # 非表示設定をスキップ
                        display_label = key_info.get("name", key)
                        if self.search_field.text().lower() in display_label.lower():
                            self.filtered_keys.append((key, value.strip()))

                for key, value in self.filtered_keys:
                    value = value.strip('"')
                    key_info = self.key_map.get(key, {})
                    display_label = key_info.get("name", key)
                    description = key_info.get("description", "")

                    label = QLabel(display_label)
                    label.setFixedHeight(30)
                    label.setStyleSheet("font-size: 14px;")

                    if "select" in key_info:
                        select_options = key_info["select"]
                        input_field = QComboBox()
                        for option_key, option_label in select_options.items():
                            input_field.addItem(option_label, option_key)
                        input_field.setCurrentText(select_options.get(value, value))
                        input_field.setFixedHeight(30)
                    elif value in ['True', 'False']:
                        input_field = QComboBox()
                        input_field.addItems(['True', 'False'])
                        input_field.setCurrentText(value)
                        input_field.setFixedHeight(30)
                    elif value.replace('.', '', 1).isdigit() and '.' in value:
                        input_field = QLineEdit(value)
                        input_field.setValidator(QDoubleValidator())
                        input_field.setFixedHeight(30)
                    elif value.isdigit():
                        input_field = QLineEdit(value)
                        input_field.setValidator(QIntValidator())
                        input_field.setFixedHeight(30)
                    else:
                        input_field = QLineEdit(value)
                        input_field.setFixedHeight(30)

                    self.scroll_layout.addWidget(label)
                    self.scroll_layout.addWidget(input_field)

                    self.inputs[key] = input_field

    def save_settings(self):
        if self.setting_section not in self.config:
            return

        settings = self.config[self.setting_section]

        original_option_settings = settings.get(self.option_settings_key, "").strip("()")
        original_items = {}
        if original_option_settings:
            for item in original_option_settings.split(","):
                if "=" in item:
                    key, value = item.split("=")
                    original_items[key.strip()] = value.strip()

        for key, input_field in self.inputs.items():
            if isinstance(input_field, QComboBox):
                value = input_field.currentData() if input_field.currentData() else input_field.currentText()
            else:
                value = input_field.text()

            if value in ['True', 'False']:
                original_items[key] = value
            elif value.isdigit():
                original_items[key] = value
            elif value.replace('.', '', 1).isdigit():
                original_items[key] = value
            else:
                original_items[key] = f"\"{value}\""

        updated_option_settings = [f"{key}={value}" for key, value in original_items.items()]
        settings[self.option_settings_key] = f"({','.join(updated_option_settings)})"

        try:
            with open(self.file_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            QMessageBox.information(self, "保存完了", "設定を正常に保存しました！")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定ファイルの保存に失敗しました: {str(e)}")

    def load_settings(self):
        """設定をロードして表示"""
        try:
            with open(self.file_path, 'r', encoding='utf-8-sig') as f:
                self.config.read_file(f)
        except UnicodeDecodeError:
            QMessageBox.critical(self, "エラー", "設定ファイルのデコードに失敗しました。UTF-8エンコードを確認してください。")
            exit(1)

        self.update_form()

    def reload_settings(self):
        """設定を再読み込みするメソッド"""
        self.load_settings()  # 既存の設定読み込みロジックを再利用

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameSettings()
    window.exec()
    sys.exit(app.exec())
