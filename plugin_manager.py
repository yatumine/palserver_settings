import os
import sys
import json
import logging
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QCheckBox, QWidget, QMainWindow, QMessageBox
from PySide6.QtCore import Qt, Signal
from plugins.plugin_base import PluginBase
import importlib.util

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conf", "plugin_config.json")

class PluginManager(QMainWindow):
    plugins_updated = Signal()  # プラグイン更新を通知するシグナル

    def __init__(self, parent=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        super().__init__(parent)
        self.plugins = {}
        self.logger.info("Initializing PluginManager...")
        self.load_plugins()
        self.enabled_plugins = self.load_enabled_plugins()  # 有効化情報をロード
        self.init_ui()

    def init_ui(self):
        """
        UIの初期化
        """
        self.setWindowTitle("プラグインマネージャー")
        self.resize(400, 300)

        central_widget = QWidget()
        self.layout = QVBoxLayout(central_widget)
        self.layout.setAlignment(Qt.AlignTop)

        # プラグイン一覧のチェックボックスを作成
        self.plugin_checkboxes = {}
        for plugin_name, plugin_instance in self.plugins.items():
            checkbox = QCheckBox(plugin_name)
            checkbox.setChecked(plugin_name in self.enabled_plugins)
            checkbox.stateChanged.connect(self.update_plugin_state)
            self.layout.addWidget(checkbox)
            self.plugin_checkboxes[plugin_name] = checkbox

            settings_button = QPushButton(f"{plugin_name} の設定を編集")
            settings_button.clicked.connect(lambda _, p=plugin_instance: self.open_settings_window(p))
            self.layout.addWidget(settings_button)
            self.layout.addSpacing(10)

        # 保存ボタン
        self.layout.addSpacing(30)        # 保存ボタン
        save_button = QPushButton("設定を保存")
        save_button.clicked.connect(self.save_enabled_plugins)
        self.layout.addWidget(save_button)

        # プラグイン再ロードボタンを追加
        reload_button = QPushButton("プラグインを再ロード")
        reload_button.clicked.connect(self.reload_plugins)
        self.layout.addWidget(reload_button)

        self.setCentralWidget(central_widget)

    def reload_plugins(self):
        """
        プラグインを再ロードし、有効な設定を引き継ぐ
        """
        # 現在の有効なプラグインを保存
        current_enabled_plugins = list(self.enabled_plugins)  # リストをコピーしておく

        self.plugins.clear()
        self.load_plugins()

        # 有効なプラグインを復元
        self.enabled_plugins = [
            plugin for plugin in current_enabled_plugins if plugin in self.plugins
        ]

        # UIを再初期化して更新
        QMessageBox.information(self, "再ロード完了", "プラグインが再ロードされました。")
        self.init_ui()

    def open_settings_window(self, plugin_instance):
        settings_window = plugin_instance.create_settings_window()
        settings_window.exec()

    def load_plugins(self):
        """
        plugins/ディレクトリ内のプラグインをロード
        """
        if getattr(sys, 'frozen', False):  # PyInstallerでビルドされた場合
            exe_dir = os.path.dirname(sys.executable)  # exeファイルの場所
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))  # スクリプトの場所

        plugin_dir = os.path.join(exe_dir, "plugins")
        self.logger.info("Loading plugins from %s...", plugin_dir)
        if not os.path.exists(plugin_dir):
            os.mkdir(plugin_dir)
            self.logger.info("Created plugin directory: %s", plugin_dir)

        for file_name in os.listdir(plugin_dir):
            if file_name.endswith("_plugin.py"):
                plugin_path = os.path.join(plugin_dir, file_name)
                module_name = file_name[:-3]
                spec = importlib.util.spec_from_file_location(module_name, plugin_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr in dir(module):
                    cls = getattr(module, attr)
                    if isinstance(cls, type) and issubclass(cls, PluginBase) and cls is not PluginBase:
                        plugin_name = getattr(cls, "display_name", cls.__name__)
                        if plugin_name in self.plugins:
                            self.logger.warning(f"Plugin '{plugin_name}' is already registered. Skipping...")
                            continue
                        plugin_instance = cls()
                        plugin_instance.initialize(self)
                        self.register_plugin(plugin_name, plugin_instance)
                        self.logger.info(f"Plugin '{plugin_name}' registered with config: {plugin_instance.config}")

        # デバッグ: プラグイン一覧をログ出力
        self.logger.debug(f"Loaded plugins: {list(self.plugins.keys())}")
        
    def register_plugin(self, name, plugin_instance):
        """
        プラグインを登録
        :param name: プラグイン名
        :param plugin_instance: プラグインインスタンス
        """
        if name in self.plugins:
            self.logger.warning(f"Plugin '{name}' is already registered. Skipping...")
            return
        self.plugins[name] = plugin_instance

    def execute_plugin(self, name):
        """
        指定したプラグインを実行
        :param name: プラグイン名
        """
        plugin = self.plugins.get(name)
        if plugin:
            plugin.execute()
        else:
            self.logger.warning(f"プラグイン '{name}' が見つかりません。")

    def load_enabled_plugins(self):
        """
        config.jsonから有効化されたプラグインをロード
        """
        self.logger.info("Loading enabled plugins....\n Plugin path = %s", CONFIG_PATH)
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                enabled_plugins = config.get("enabled_plugins", [])
                valid_plugins = [name for name in enabled_plugins if name in self.plugins]
                self.logger.debug(f"Enabled plugins loaded: {valid_plugins}")
                return valid_plugins
        return []

    def save_enabled_plugins(self):
        """
        有効化されたプラグインをconfig.jsonに保存
        """
        self.enabled_plugins = [name for name, checkbox in self.plugin_checkboxes.items() if checkbox.isChecked()]
        config = {"enabled_plugins": self.enabled_plugins}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        self.logger.info("有効化されたプラグインを保存しました。")

        # 保存後にシグナルを発信
        self.plugins_updated.emit()

    def update_plugin_state(self):
        """
        チェックボックスの状態に応じてプラグインを有効化/無効化
        """
        for plugin_name, checkbox in self.plugin_checkboxes.items():
            if checkbox.isChecked() and plugin_name not in self.enabled_plugins:
                self.enabled_plugins.append(plugin_name)
                self.logger.info(f"プラグイン '{plugin_name}' が有効化されました。")
            elif not checkbox.isChecked() and plugin_name in self.enabled_plugins:
                self.enabled_plugins.remove(plugin_name)
                self.logger.info(f"プラグイン '{plugin_name}' が無効化されました。")

    def get_enabled_plugins(self):
        """
        有効化されたプラグインのインスタンスを返す
        """
        return {name: self.plugins[name] for name in self.enabled_plugins if name in self.plugins}
