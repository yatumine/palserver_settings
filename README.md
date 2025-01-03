## Setting

```
pip install pyinstaller PySide6 qtawesome pillow requests

```

## build

```
pyinstaller --onedir --windowed --clean --noupx --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets --icon=images/256.ico --add-data "conf/app.json;conf" --add-data "conf/setting_key_map.json;conf" --add-data "images/256.ico;images" --name ServerSetting main.py
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


## pyinstallerのビルドが失敗するとき
Gitからpyinstallerを取得しビルド環境を構築します。
pip uninstall pyinstaller

gitコマンドでPyinstallerをクローン
git clone https://github.com/pyinstaller/pyinstaller

ブートローダーフォルダまで移動。
cd pyinstaller
cd bootloader

環境をクリーン
python ./waf distclean all

pyinstaller直下に移動
cd ../

wheelのインストール
bootloaderを再構築したpyinstallerをインストールするために、wheelをインストールする
pip install wheel

pyinstallerのインストール。
pip install .
