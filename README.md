## Setting

```
pip install pyinstaller PySide6 qtawesome pillow requests

```

## build

PowerShellで、以下のコマンドを実行することでビルドが行えます。  
```
.\make.ps1
```

# Plugin
拡張機能をpyファイルで作成し、exeと同階層のpluginsディレクトリに配置することで動作させることができます。
_internal/plugins配下に、RCONのコマンド送信プラグインとRestAPIの送信プラグインが同梱されています。
このファイルをexe側のpluginsディレクトリにコピーすることでプラグインを利用することができます。

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
