from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu
from PySide6.QtWidgets import (
     QLabel, QApplication
)
from PySide6.QtCore import Qt

class CopyableLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)  # テキストを選択可能にする
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("コピー", self)
        copy_action.triggered.connect(self.copy_text)
        menu.addAction(copy_action)
        menu.exec(self.mapToGlobal(pos))

    def copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text())
