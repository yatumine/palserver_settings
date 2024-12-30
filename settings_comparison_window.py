import json
import os
from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QPushButton, QWidget, QMessageBox, QScrollArea, QGridLayout, QDialog
)
from PySide6.QtCore import Qt
import configparser
from lib.copyable_label import CopyableLabel
from game_settings import GameSettings

class SettingsComparisonWindow(QDialog):
    SETTINGS_SECTION = '/Script/Pal.PalGameWorldSettings'
    OPTION_SETTINGS_KEY = 'OptionSettings'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("設定比較")
        self.setFixedSize(800, 600)
        self.setModal(True)

        self.internal_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.key_map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conf", "setting_key_map.json")
        self.file_path = self.load_settings_file_path()

        # ConfigParser をカスタマイズ
        self.config = configparser.RawConfigParser()
        self.config.optionxform = str  # キーの小文字変換を無効化
        self.key_map = self.load_key_map()
        self.missing_keys = []
        self.init_ui()

    def load_settings_file_path(self):
        if os.path.exists(self.internal_config_path):
            with open(self.internal_config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("settings_file_path", "")
        return ""

    def load_key_map(self):
        if os.path.exists(self.key_map_path):
            with open(self.key_map_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)  # 縦軸の要素を上詰めに設定

        add_all_button = QPushButton("すべての未定義設定を追加")
        add_all_button.clicked.connect(self.add_all_missing_keys)
        layout.addWidget(add_all_button)

        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)
        self.compare_settings()

    def compare_settings(self):
        """設定を比較し、レイアウトを更新"""
        if not os.path.exists(self.file_path):
            QMessageBox.critical(self, "エラー", "設定ファイルが見つかりませんでした。")
            return

        # 設定を再読み込み
        self.config.read(self.file_path, encoding='utf-8')

        # 現在のキーを取得
        option_settings = self.config.get(self.SETTINGS_SECTION, self.OPTION_SETTINGS_KEY, fallback="")
        current_keys = {item.split('=')[0].strip() for item in option_settings.strip('()').split(',') if '=' in item}

        # 未定義キーを計算
        self.missing_keys = [key for key in self.key_map if key not in current_keys]

        # すべての QScrollArea を削除
        self.remove_all_scroll_areas()

        # 新しい QScrollArea を作成
        self.scroll_area = QScrollArea()
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)  # 縦軸の要素を上詰めに設定
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)

        # レイアウトに追加
        self.layout().addWidget(self.scroll_area)

        # 以下は未定義キーを追加する処理
        self.scroll_layout.addWidget(QLabel("現在設定ファイルに定義されていないもの（デフォルト値の設定）"))

        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        # グリッドヘッダー
        grid_layout.addWidget(QLabel("キー"), 0, 0, alignment=Qt.AlignLeft)
        grid_layout.addWidget(QLabel("名前"), 0, 1, alignment=Qt.AlignLeft)
        grid_layout.addWidget(QLabel("デフォルト"), 0, 2, alignment=Qt.AlignLeft)
        grid_layout.addWidget(QLabel("アクション"), 0, 3, alignment=Qt.AlignLeft)

        row = 1
        for key in self.missing_keys:
            key_label = CopyableLabel(key)
            name_label = QLabel(self.key_map[key].get('name', ''))

            # デフォルト値を取得
            default_value = self.key_map[key].get('default', None)
            if default_value is None:  # None の場合のみ代替処理を適用
                select_options = self.key_map[key].get('select', {})
                default_value = next(iter(select_options.values()), '') if select_options else ''
            if isinstance(default_value, (int, float)):
                default_value = str(default_value)

            default_label = QLabel(default_value)

            add_button = QPushButton("追加")
            add_button.clicked.connect(lambda _, k=key: self.add_key(k))

            grid_layout.addWidget(key_label, row, 0, alignment=Qt.AlignLeft)
            grid_layout.addWidget(name_label, row, 1, alignment=Qt.AlignLeft)
            grid_layout.addWidget(default_label, row, 2, alignment=Qt.AlignLeft)
            grid_layout.addWidget(add_button, row, 3, alignment=Qt.AlignLeft)
            row += 1

        self.scroll_layout.addLayout(grid_layout)
        self.scroll_content.adjustSize()  # レイアウトのサイズを調整
        self.scroll_area.ensureVisible(0, 0)  # スクロールをトップに移動

    def add_key(self, key):
        if self.SETTINGS_SECTION not in self.config:
            self.config.add_section(self.SETTINGS_SECTION)

        current_values = self.config.get(self.SETTINGS_SECTION, self.OPTION_SETTINGS_KEY, fallback="")
        updated_values = current_values.strip('()')

        # デフォルト値を決定
        key_info = self.key_map.get(key, {})
        default_value = key_info.get('default', None)
        if default_value is None:
            select_options = key_info.get('select', {})
            default_value = next(iter(select_options.values()), 'UNDEFINED') if select_options else 'UNDEFINED'

        # デフォルト値を文字列に変換
        if isinstance(default_value, (int, float)):
            default_value = str(default_value)

        updated_values = f"{updated_values},{key}={default_value}" if updated_values else f"{key}={default_value}"

        self.config.set(self.SETTINGS_SECTION, self.OPTION_SETTINGS_KEY, f"({updated_values})")

        with open(self.file_path, 'w', encoding='utf-8') as f:
            self.config.write(f)

        QMessageBox.information(self, "成功", f"キー '{key}' を追加しました。")
        self.compare_settings()

        # 親ウィンドウを遡ってリロード
        parent = self.parent()
        while parent:
            if isinstance(parent, GameSettings):
                parent.reload_settings()  # 親ウィンドウの関数を呼び出す
                break
            parent = parent.parent()  # 次の親を取得

    def add_all_missing_keys(self):
        if self.SETTINGS_SECTION not in self.config:
            self.config.add_section(self.SETTINGS_SECTION)

        current_values = self.config.get(self.SETTINGS_SECTION, self.OPTION_SETTINGS_KEY, fallback="")
        updated_values = current_values.strip('()')

        for key in self.missing_keys:
            # デフォルト値を決定
            key_info = self.key_map.get(key, {})
            default_value = key_info.get('default', None)
            if default_value is None:
                select_options = key_info.get('select', {})
                default_value = next(iter(select_options.values()), 'UNDEFINED') if select_options else 'UNDEFINED'

            # デフォルト値を文字列に変換
            if isinstance(default_value, (int, float)):
                default_value = str(default_value)

            updated_values = f"{updated_values},{key}={default_value}" if updated_values else f"{key}={default_value}"

        self.config.set(self.SETTINGS_SECTION, self.OPTION_SETTINGS_KEY, f"({updated_values})")

        with open(self.file_path, 'w', encoding='utf-8') as f:
            self.config.write(f)

        QMessageBox.information(self, "成功", "すべての定義されていない項目を追加しました。")
        self.compare_settings()

        # 親ウィンドウを遡ってリロード
        parent = self.parent()
        while parent:
            if isinstance(parent, GameSettings):
                parent.reload_settings()  # 親ウィンドウの関数を呼び出す
                break
            parent = parent.parent()  # 次の親を取得
        self.accept()  # モーダルダイアログを閉じる

    def remove_all_scroll_areas(self):
        """レイアウトに追加されたすべての QScrollArea を削除"""
        main_layout = self.layout()
        if main_layout is None:
            return

        # レイアウト内のすべてのアイテムを確認
        for i in reversed(range(main_layout.count())):
            item = main_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, QScrollArea):  # QScrollArea のみ削除
                main_layout.takeAt(i)
                widget.deleteLater()  # メモリ解放

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    comparison_window = SettingsComparisonWindow()
    comparison_window.show()
    sys.exit(app.exec())
