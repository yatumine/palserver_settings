import os
import shutil
import sys
import json
import configparser
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QWidget, QMessageBox, QFileDialog, QScrollArea, QDialog, QComboBox,
    QHBoxLayout, QToolButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QDoubleValidator
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
        """
        初回設定の流れ:
        1. settings_file_pathが空なら初期設定に進む。
        2. ユーザーにINIファイルを指定させる。
        3. AppConfig.get('default_inifile_name')だった場合、指定の場所にコピー。
        4. コピー後にsettings_file_pathを更新する。
        """
        file_path = Config.get("settings_file_path", "")

        if not file_path:
            QMessageBox.information(None, "情報", f"初回起動です。INIファイルを選択してください。\n{AppConfig.get('default_inifile_name')}を選択した場合、PalWorldServerSetting.iniをコピーして作成します。")

            default_directory = AppConfig.get("install_dir", os.path.expanduser("~"))
            file_path, _ = QFileDialog.getOpenFileName(
                None, "INIファイルを選択", default_directory, "INIファイル (*.ini);;すべてのファイル (*)"
            )

            if not file_path:
                QMessageBox.critical(None, "エラー", "ファイルが選択されていません。終了します。")
                exit(1)

        config_subpath = AppConfig.get("config_subpath")
        config_directory = os.path.join(AppConfig.get("install_dir", ""), *config_subpath.split("/"))
        os.makedirs(config_directory, exist_ok=True)

        if os.path.basename(file_path) == AppConfig.get("default_inifile_name"):
            new_file_path = os.path.join(config_directory, AppConfig.get("inifile_name"))
            QMessageBox.information(None, "通知", f"{AppConfig.get('default_inifile_name')}を{new_file_path}にコピーします。")
            try:
                shutil.copy(file_path, new_file_path)
                QMessageBox.information(None, "成功", f"{new_file_path}にコピーしました。")
                settings_file_path = new_file_path
            except Exception as e:
                QMessageBox.critical(None, "エラー", f"INIファイルのコピーに失敗しました: {str(e)}")
                exit(1)
            try:
                Config.set("settings_file_path", settings_file_path)
                QMessageBox.information(None, "成功", "設定ファイルパスが保存されました。")
            except Exception as e:
                QMessageBox.critical(None, "エラー", f"設定の保存に失敗しました: {str(e)}")
                exit(1)
        else:
            settings_file_path = file_path

        return settings_file_path

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

        # 未定義の設定を確認するボタンを追加
        compare_button = QPushButton("未定義の設定を確認する")
        compare_button.clicked.connect(self.open_comparison_window)
        layout.addWidget(compare_button)

        save_button = QPushButton("設定を保存")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.load_settings()


    def open_comparison_window(self):
        """未定義の設定を確認する"""
        try:
            from settings_comparison_window import SettingsComparisonWindow
            comparison_window = SettingsComparisonWindow(parent=self)
            comparison_window.exec()
        except ImportError as e:
            QMessageBox.critical(self, "エラー", f"未定義の設定を確認するウィンドウを開けません: {e}")

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
        except FileNotFoundError:
            QMessageBox.critical(self, "エラー", f"設定ファイルが見つかりません: {self.file_path}") 

        self.update_form()

    def reload_settings(self):
        """設定を再読み込みするメソッド"""
        self.load_settings()  # 既存の設定読み込みロジックを再利用

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameSettings()
    window.exec()
    sys.exit(app.exec())
