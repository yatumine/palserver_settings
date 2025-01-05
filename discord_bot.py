import logging
import os
import sys
import json
import importlib.util
import discord
from discord.ext import tasks
from discord import app_commands
import psutil
from lib.server_control import start_server, stop_server, check_server_status, check_memory_usage

class DiscordBot:
    def __init__(self, token, channel_id, server_path, server_exe, server_cmd_exe, send_flag = True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing DiscordBot")
        self.token = token
        self.channel_id = int(channel_id)
        self.server_path = server_path
        self.server_exe = server_exe
        self.server_cmd_exe = server_cmd_exe
        self.server_name = server_exe.split(".")[0]
        self.send_flag = send_flag

        # pluginsフォルダ内のプラグインを読み込む
        self._import_plugins()

        # RCONプラグインの使用例
        if "RCONPlugin" in self.plugins:
            self.rcon_plugin = self.plugins["RCONPlugin"]

        # REST API プラグインの使用例
        if "RestAPIPlugin" in self.plugins:
            self.rest_api_plugin = self.plugins["RestAPIPlugin"]

        # 状態を追跡するための変数を初期化
        self.is_first_run = True
        self.last_alert_level = None
        self.last_server_status = None

        # Discordクライアントを初期化
        self.client = discord.Client(
            intents=discord.Intents.default(),
            activity=discord.Game(self.server_name)
        )
        self.tree = app_commands.CommandTree(self.client)
        self._register_commands()


    def _register_commands(self):
        self.logger.info("Registering commands")

        # 既存のコマンドを登録
        @self.tree.command(name="start_server", description=f"{self.server_exe}を起動します")
        async def start_server_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: start_server by {interaction.user.name}")
            embed = await start_server(self.server_path, self.server_exe)
            await self._interraction_send(interaction, embed)

        @self.tree.command(name="stop_server", description=f"{self.server_exe}を停止します")
        async def stop_server_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: stop_server by {interaction.user.name}")
            embed = await stop_server(self.server_cmd_exe, self.server_exe)
            await self._interraction_send(interaction, embed)

        @self.tree.command(name="check_server", description="現在サーバーが起動しているかを調べます")
        async def check_server_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: check_server by {interaction.user.name}")
            status = await check_server_status(self.server_exe)
            embed = discord.Embed(
                title="サーバーは起動中です" if status else "サーバーは停止中です",
                color=0x00ff00 if status else 0xff0000
            )
            await self._interraction_send(interaction, embed, ephemeral=True)

        @self.tree.command(name="check_memory", description="現在のサーバーのメモリ使用量を調べます")
        async def check_memory_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: check_memory by {interaction.user.name}")
            embed = await check_memory_usage()
            await self._interraction_send(interaction, embed)

        @self.tree.command(name="help", description="利用可能なコマンド一覧を表示します")
        async def help_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: help by {interaction.user.name}")
            embed = discord.Embed(
                title="コマンド一覧",
                description="以下は利用可能なコマンドの一覧です。",
                color=0x3498db
            )
            embed.add_field(name="/start_server", value=f"{self.server_exe}を起動します", inline=False)
            embed.add_field(name="/stop_server", value=f"{self.server_exe}を停止します", inline=False)
            embed.add_field(name="/check_server", value="現在サーバーが起動しているかを調べます", inline=False)
            embed.add_field(name="/check_memory", value="現在のサーバーのメモリ使用量を調べます", inline=False)
            embed.add_field(name="/reset_commands", value="全てのスラッシュコマンドをリセット", inline=False)
            if self.rest_api_plugin is not None:
                embed.add_field(name="/send_announce", value="REST APIを使用してアナウンスを送信します", inline=False)
                embed.add_field(name="/show_player", value="REST APIを使用してログイン中のプレイヤーを取得します", inline=False)
                embed.add_field(name="/show_settings", value="REST APIを使用してサーバー設定を取得します", inline=False)
                embed.add_field(name="/show_metrics", value="REST APIを使用してサーバー メトリックを取得します", inline=False)
            embed.add_field(name="/help", value="利用可能なコマンド一覧を表示します", inline=False)
            await self._interraction_send(interaction, embed, ephemeral=True)

        @self.tree.command(name="reset_commands", description="全てのスラッシュコマンドをリセット")
        async def reset_commands(interaction: discord.Interaction):
            await self.tree.sync(guild=None)  # 全てのコマンドを削除
            await interaction.response.send_message("全てのスラッシュコマンドをリセットしました")

        if self.rest_api_plugin is not None:
            # パルワールドのみの処理
            @self.tree.command(name="send_announce", description="REST APIを使用してアナウンスを送信します")
            async def send_rest_api_announce_command(interaction: discord.Interaction, message: str):
                """
                スラッシュコマンドを処理し、REST APIを使用してメッセージを送信
                :param interaction: Discordのコマンドのインタラクション
                :param message: アナウンスとして送信するメッセージ
                """
                try:
                    self.logger.info(f"Command executed: send_announce by {interaction.user.name}")
                    
                    # REST API プラグインの send_command メソッドを使用
                    response = self.rest_api_plugin.send_command("announce", "POST",{"message": message})

                    # レスポンスを解析して送信
                    await self._send_response(interaction, response, title="アナウンス", ephemeral=True)
                except Exception as e:
                    self.logger.error(f"Error in send_rest_api_announce_command: {e}")
                    await interaction.response.send_message(f"アナウンスに失敗しました: {e}", ephemeral=True)

            @self.tree.command(name="show_player", description="REST APIを使用してログイン中のプレイヤーを取得します")
            async def send_rest_api_show_player_command(interaction: discord.Interaction):
                """
                スラッシュコマンドを処理し、REST APIを使用してログイン中のプレイヤーを取得
                :param interaction: Discordのコマンドのインタラクション
                """
                try:
                    self.logger.info(f"Command executed: show_player by {interaction.user.name}")
                    
                    # REST API プラグインの send_command メソッドを使用
                    response = self.rest_api_plugin.send_command("players", "GET", {})

                    # レスポンスを解析して送信
                    await self._send_response(interaction, response, title="ログイン中のプレイヤー", ephemeral=True)
                except Exception as e:
                    self.logger.error(f"Error in send_rest_api_show_player_command: {e}")
                    await interaction.response.send_message(f"ログイン中のプレイヤー取得に失敗しました: {e}", ephemeral=True)

            @self.tree.command(name="show_settings", description="REST APIを使用してサーバー設定を取得します")
            async def send_rest_api_show_settings_command(interaction: discord.Interaction):
                """
                スラッシュコマンドを処理し、REST APIを使用してサーバー設定を取得
                :param interaction: Discordのコマンドのインタラクション
                """
                try:
                    self.logger.info(f"Command executed: show_settings by {interaction.user.name}")
                    
                    # REST API プラグインの send_command メソッドを使用
                    response = self.rest_api_plugin.send_command("settings", "GET", {})
                    
                    # レスポンスを解析して送信
                    await self._send_response(interaction, response, title="サーバー設定", ephemeral=True)
                except Exception as e:
                    self.logger.error(f"Error in send_rest_api_show_settings_command: {e}")
                    await interaction.response.send_message(f"サーバー設定取得に失敗しました: {e}", ephemeral=True)

            @self.tree.command(name="show_metrics", description="REST APIを使用してサーバー メトリックを取得します")
            async def send_rest_api_show_metrics_command(interaction: discord.Interaction):
                """
                スラッシュコマンドを処理し、REST APIを使用してサーバー メトリックを取得
                :param interaction: Discordのコマンドのインタラクション
                """
                try:
                    self.logger.info(f"Command executed: show_metrics by {interaction.user.name}")
                    
                    # REST API プラグインの send_command メソッドを使用
                    response = self.rest_api_plugin.send_command("metrics", "GET", {})
                    
                    # レスポンスを解析して送信
                    await self._send_response(interaction, response, title="サーバー メトリック", ephemeral=True)
                except Exception as e:
                    self.logger.error(f"Error in send_rest_api_show_metrics_command: {e}")
                    await interaction.response.send_message(f"サーバー メトリック取得に失敗しました: {e}", ephemeral=True)

        self.logger.info("Commands registered")

    async def _send_response(self, interaction: discord.Interaction, response_data, title="レスポンス", ephemeral=False):
        """
        Discordメッセージとしてレスポンスを送信する汎用関数。
        """
        try:
            # 応答を保留
            await interaction.response.defer(ephemeral=ephemeral)

            # JSONデータの整形
            if isinstance(response_data, dict):
                formatted_response = json.dumps(response_data, indent=4, ensure_ascii=False)
            elif isinstance(response_data, str):
                formatted_response = response_data
            else:
                formatted_response = str(response_data)

            # Discordメッセージ制限（2000文字）を確認
            chunk_size = 1990  # 安全マージンを取って1990文字に設定
            if len(formatted_response) > chunk_size:
                # 長いメッセージを分割して送信
                chunks = [formatted_response[i:i + chunk_size] for i in range(0, len(formatted_response), chunk_size)]

                # フォローアップメッセージとして分割メッセージを送信
                await interaction.followup.send(f"{title}が複数メッセージに分割されます:", ephemeral=ephemeral)
                for i, chunk in enumerate(chunks):
                    try:
                        await interaction.followup.send(f"```\n{chunk}\n```", ephemeral=ephemeral)
                    except Exception as e:
                        self.logger.error(f"Failed to send followup message (chunk {i+1}/{len(chunks)}): {e}")
                        await interaction.followup.send(
                            f"フォローアップ送信中にエラーが発生しました (chunk {i+1}/{len(chunks)}): {e}",
                            ephemeral=True
                        )
            else:
                # 短いメッセージの場合
                await interaction.followup.send(f"{title}:\n```\n{formatted_response}\n```", ephemeral=ephemeral)
        except Exception as e:
            # フォローアップでエラーを送信
            self.logger.error(f"Failed to send response: {e}")
            await interaction.followup.send(f"レスポンス送信中にエラーが発生しました: {e}", ephemeral=True)

    async def _interraction_send(self, interaction, embed, ephemeral=False):
        if self.send_flag:
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @tasks.loop(minutes=1)  # 毎分チェック
    async def memory_check_task(self):
        memory_usage = psutil.virtual_memory().percent
        alert_level = None

        # メモリ使用率に応じてアラートレベルを設定
        if memory_usage > 90:
            alert_level = "critical"
        elif memory_usage > 80:
            alert_level = "warning_high"
        elif memory_usage > 70:
            alert_level = "warning_low"
        else:
            alert_level = "normal"

        # 状態が変わった場合のみメッセージを送信
        if alert_level != self.last_alert_level:
            self.last_alert_level = alert_level
            channel = self.client.get_channel(self.channel_id)

            if self.is_first_run:
                self.is_first_run = False
                if channel and self.send_flag:
                    embed = discord.Embed(
                        title="メモリ使用量監視開始",
                        description="メモリ使用量の監視を開始しました。\nサーバーの状態を監視しています。",
                        color=0x00ff00
                    )
                    await channel.send(embed=embed)
                return  # 初回実行時は何もしない
            
            if alert_level == "critical":
                embed = discord.Embed(
                    title="高負荷警告",
                    description=f"サーバーのメモリ使用率が {memory_usage}% を超えました。\nサーバーの状態を確認してください。",
                    color=0xff0000
                )
            elif alert_level == "warning_high":
                embed = discord.Embed(
                    title="メモリ使用量警告",
                    description=f"サーバーのメモリ使用率が {memory_usage}% を超えました。",
                    color=0xffa500
                )
            elif alert_level == "warning_low":
                embed = discord.Embed(
                    title="メモリ使用量警告",
                    description=f"サーバーのメモリ使用率が {memory_usage}% を超えました。",
                    color=0xffff00
                )
            elif alert_level == "normal":

                embed = discord.Embed(
                    title="メモリ使用量正常",
                    description="サーバーのメモリ使用率が正常な範囲に戻りました。",
                    color=0x00ff00
                )
            else:
                return  # その他のケースでは何もしない

            if channel and self.send_flag:
                await channel.send(embed=embed)

    @tasks.loop(minutes=1)  # サーバー状態の監視
    async def server_status_check_task(self):
        current_status = await check_server_status(self.server_exe)

        # サーバーの状態が変化した場合のみ通知
        if current_status != self.last_server_status:
            self.last_server_status = current_status
            channel = self.client.get_channel(self.channel_id)

            if current_status:
                embed = discord.Embed(
                    title="サーバー起動",
                    description="サーバーが正常に起動しています。",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="サーバー停止",
                    description="サーバーが停止しました。確認してください。",
                    color=0xff0000
                )

            if channel and self.send_flag:
                await channel.send(embed=embed)

    def _import_plugins(self):
        """
        plugins/ディレクトリ内の特定プラグインをインポートし、インスタンスを作成する
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

        import_plugins = {"rcon_plugin", "rest_api_plugin"}  # インポート対象プラグイン名（拡張子なし）
        self.plugins = {}  # ロードしたプラグインインスタンスを保持する辞書

        for file_name in os.listdir(plugin_dir):
            if file_name.endswith("_plugin.py"):
                plugin_name = file_name[:-3]  # ファイル名から拡張子を除去

                if plugin_name not in import_plugins:
                    continue

                # クラス名を推測（例: rcon_plugin → RconPlugin）
                class_name = ''.join(word.capitalize() for word in plugin_name.split('_'))

                # プラグインをインポート
                plugin_path = os.path.join(plugin_dir, file_name)
                self.logger.info("Loading plugin: %s", plugin_name)
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # モジュールからクラスを探索（大文字小文字を無視して一致を確認）
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type) and
                            attr.__module__ == module.__name__ and
                            attr_name.lower() == class_name.lower()
                        ):
                            # 一致するクラスが見つかった場合にインスタンス化
                            plugin_instance = attr()
                            self.plugins[attr_name] = plugin_instance
                            self.logger.info(f"Successfully loaded plugin: {plugin_name}")
                            break
                    else:
                        self.logger.warning(f"プラグイン {plugin_name} に対応するクラス {class_name} が見つかりません")
                except Exception as e:
                    self.logger.error(f"プラグイン {plugin_name} のロードに失敗しました: {e}")

    async def _on_ready(self):
        self.logger.info("Bot is ready")
        try:
            await self.tree.sync()  # コマンドを同期
            await self.client.wait_until_ready()
            channel = self.client.get_channel(self.channel_id)  # チャンネルIDからチャンネルを取得
            # メッセージを投稿する
            embed = discord.Embed(
                title="Botが起動しました",
                description="コマンドの準備が整いました。必要なコマンドを入力してください。(/helpでコマンド一覧を表示)",
                color=0x00ff00
            )
            if channel and self.send_flag:
                await channel.send(embed=embed)

            # メモリ使用量を監視
            self.logger.info("Starting memory check task")
            self.memory_check_task.start()

            # サーバー状態を監視
            self.logger.info("Starting server status check task")
            self.server_status_check_task.start()
        except Exception as e:
            self.logger.error(f"Error during on_ready: {e}")

    def start(self):
        """Botを起動"""
        @self.client.event
        async def on_ready():
            await self._on_ready()

        try:
            self.client.run(self.token)
        except Exception as e:
            self.logger.error(f"Bot failed to start: {e}")
