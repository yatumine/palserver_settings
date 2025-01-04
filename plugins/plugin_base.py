import os
import json
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt

class PluginBase:
    def __init__(self):
        self.config = {}
        self.config_path = self.get_default_config_path()
        self.load_config()

    def get_default_config_path(self):
        """
        デフォルトのコンフィグファイルパスを取得
        """
        plugin_name = self.__class__.__name__
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conf/.plugin_configs/")
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, f"{plugin_name}.json")

    def load_config(self):
        """
        コンフィグファイルをロード
        """
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = self.get_default_config()
            self.save_config()

    def save_config(self):
        """
        コンフィグファイルを保存
        """
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def get_default_config(self):
        """
        プラグインごとのデフォルトコンフィグを提供
        """
        return {}

    def initialize(self, main_app):
        """
        プラグインの初期化（サブクラスで実装）
        """
        raise NotImplementedError("initialize() must be implemented by plugin")

    def execute(self):
        """
        プラグインの実行処理（サブクラスで実装）
        """
        raise NotImplementedError("execute() must be implemented by plugin")

    def create_window(self):
            """
            プラグインの画面を作成して返す（必要に応じてオーバーライド）
            """
            return QDialog()  # デフォルトでは空のダイアログ

    def create_settings_window(self):
        return PluginSettingsWindow(self)

class PluginSettingsWindow(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle(f"{plugin.display_name} 設定")
        self.setFixedSize(400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)

        self.inputs = {}
        for key, value in self.plugin.config.items():
            label = QLabel(key)
            input_field = QLineEdit(str(value))
            self.inputs[key] = input_field
            layout.addWidget(label)
            layout.addWidget(input_field)

        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_config)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def save_config(self):
        try:
            for key, input_field in self.inputs.items():
                self.plugin.config[key] = input_field.text()
            self.plugin.save_config()
            QMessageBox.information(self, "成功", "設定を保存しました。")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")
