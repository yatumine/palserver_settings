# PalWorldServerSetting

![MainMenu](https://github.com/yatumine/palserver_settings/blob/main/docs/images/main_menu.png) 


## Overview
Windows Server（またはWindows）でのパルワールドサーバー構築とサーバー設定が行えます。  
[Discord Developer Portal](https://discord.com/developers/applications)にてDiscordBotを作成し、設定を行うことでDiscordから各種コマンド実行が行えます。  
DiscordBotでは、1分に1回のサーバーのメモリ監視が行われます。  


## Requirement
Windows Server(または、Windows)

## Usage
[Releases](https://github.com/yatumine/palserver_settings/releases) からzipをダウンロードし、ServerSetting.exeを実行してください。

または、このリポジトリをCloneしてビルドすることもできます。  
[ビルド方法](#Build)

プラグインでの拡張機能があり、標準でRCONプラグインとRestAPIプラグインが同梱されています。  
利用するには、パッケージ展開後プラグインディレクトリに配置することでプラグインマネージャーで有効化し利用できます。  
[プラグイン](#Plugin)

## Reference

## Author

[X(twitter)](https://x.com/KmmrTech)

## Licence

[MIT](https://github.com/yatumine/palserver_settings?tab=MIT-1-ov-file)


# Build

```
pip install -r requirements.txt
```

PowerShellで、以下のコマンドを実行することでビルドが行えます。  
```
.\make.ps1
```

# Plugin
拡張機能をpyファイルで作成し、exeと同階層のpluginsディレクトリに配置することで動作させることができます。
_internal/plugins配下に、RCONのコマンド送信プラグインとRestAPIの送信プラグインが同梱されています。
このファイルをexe側のpluginsディレクトリにコピーすることでプラグインを利用することができます。

## Plugin開発
プラグインは、PluginBaseクラスを継承した<プラグイン名>_plugin.pyというファイルを作成することでプラグインマネージャから有効化できるようになります。
プラグインファイルはビルドの必要はなく、pyファイルをpluginsディレクトリにコピーすることで利用可能になります。
注意:プラグインファイルでライブラリを新たに追加する場合は別途パッケージビルドが必要です。

## pyinstallerのビルドが失敗するとき
Gitからpyinstallerを取得しビルド環境を構築します。  
```
pip uninstall pyinstaller
```

gitコマンドでPyinstallerをクローン  
```
git clone https://github.com/pyinstaller/pyinstaller
```

ブートローダーフォルダまで移動。  
```
cd pyinstaller/bootloader
```

環境をクリーン  
```
python ./waf distclean all
```

pyinstaller直下に移動  
```
cd ../
```

wheelのインストール  
bootloaderを再構築したpyinstallerをインストールするために、wheelをインストールする  
```
pip install wheel
```

pyinstallerのインストール  
```
pip install .
```
