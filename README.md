## Setting

```
pip install pyinstaller PySide6 qtawesome pillow requests

```

## build

```
pyinstaller --onefile --windowed --clean --noupx --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets --icon=images/256.ico --add-data "conf/app.json;conf" --name ServerSetting main.py
```

## アイコンの一覧
Fontawesome のアイコンを一覧で表示するには、コマンドプロンプトで以下を実行する
```
qta-browser
```

##  アプリアイコン
images/icon.svg
256x256のアプリアイコンを作成し、ペイントでBMPファイルとして保存。
ファイル名を.icoにする。
