import logging
import os
import sys
import json
import importlib.util
from typing import Union
from datetime import datetime
import discord
from discord.ext import tasks
from discord import app_commands
from discord.app_commands import Choice
import psutil
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
from lib.server_control import update_server, start_server, stop_server, check_server_status, check_memory_usage
from lib.config import Config

class DiscordBot:
    def __init__(self, token, channel_id, server_path, server_exe, server_cmd_exe, steamcmd_path, app_id, send_flag = True):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing DiscordBot")
        self.token = token
        self.channel_id = int(channel_id)
        self.server_path = server_path
        self.server_exe = server_exe
        self.server_cmd_exe = server_cmd_exe
        self.server_name = server_exe.split(".")[0]
        self.send_flag = send_flag
        self.app_id = app_id
        self.steamcmd_path = steamcmd_path

        # config読み込み
        self.config = Config.load_config()

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

        # Scheduler初期化
        self.scheduler = AsyncIOScheduler()

        # Discordクライアントを初期化
        self.client = discord.Client(
            intents=discord.Intents.default(),
            activity=discord.Game(self.server_name)
        )
        self.tree = app_commands.CommandTree(self.client)
        self._register_commands()


    async def _send_announcement(self, message: str):
        """アナウンスを送信するヘルパー関数"""
        if self.rest_api_plugin:
            try:
                self.rest_api_plugin.send_command("announce", "POST", {"message": message})
            except Exception as e:
                self.logger.error(f"Failed to send announcement: {e}")

    def _register_commands(self):
        self.logger.info("Registering commands")

        # 曜日選択のオプションを定義
        weekday_choices = [
            Choice(name="Monday", value="mon"),
            Choice(name="Tuesday", value="tue"),
            Choice(name="Wednesday", value="wed"),
            Choice(name="Thursday", value="thu"),
            Choice(name="Friday", value="fri"),
            Choice(name="Saturday", value="sat"),
            Choice(name="Sunday", value="sun"),
        ]

        # コマンドを登録
        @self.tree.command(name="update_server", description=f"SteamCMDとゲームサーバーのアップデートを行います")
        async def update_server_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: update_server by {interaction.user.name}")
            await self._interraction_send(interaction, "SteamCMDとゲームサーバーのアップデートを行います")
            embed = await update_server(self.steamcmd_path, self.server_path, self.app_id)
            await self._interraction_followup_send(interaction, embed)
            self.logger.info(f"Command executed completes: update_server by {interaction.user.name}")

        @self.tree.command(name="start_server", description=f"{self.server_exe}を起動します")
        async def start_server_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: start_server by {interaction.user.name}")
            embed = await start_server(self.server_path, self.server_exe)
            await self._interraction_send(interaction, embed)
            self.logger.info(f"Command executed completes: start_server by {interaction.user.name}")

        @self.tree.command(name="stop_server", description=f"{self.server_exe}を停止します")
        async def stop_server_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: stop_server by {interaction.user.name}")
            embed = await stop_server(self.server_cmd_exe, self.server_exe)
            await self._interraction_send(interaction, embed)
            self.logger.info(f"Command executed completes: stop_server by {interaction.user.name}")

        @self.tree.command(name="restart_server", description="サーバーを再起動します")
        async def restart_server_command(interaction: discord.Interaction, wait_minutes: int, update: bool ):
            self.logger.info(f"Command executed: restart_server by {interaction.user.name}")
            await self._interraction_send(interaction, "サーバーを再起動要求を受け付けました")
            await self._restart_server(wait_minutes, update)
            self.logger.info(f"Command executed completes: restart_server by {interaction.user.name}")

        @self.tree.command(name="add_restart_task", description="サーバー再起動タスクを追加します。指定した曜日、時間にサーバー再起動アナウンスを開始します。")
        @app_commands.describe(
            weekday="タスクを実行する曜日を選択してください。",
            hour="タスクを実行する時間（0～23）",
            minute="タスクを実行する分（0～59）",
            repeat="繰り返し実行する場合はTrue、1回のみ実行する場合はFalseを指定します。"
        )
        @app_commands.choices(weekday=weekday_choices)
        async def add_restart_task(interaction: discord.Interaction, weekday: Choice[str], hour: int, minute: int, repeat: bool):
            task = {
                "name": f"server_restart_{weekday.value}_{hour}_{minute}",
                "weekday": weekday.value,
                "hour": hour,
                "minute": minute,
                "repeat": repeat
            }
            self.logger.info(f"Command executed: add_restart_task by {interaction.user.name}")
            self.logger.info(f"Task: {task}")

            # 既存のタスクをチェックして上書きまたは追加
            tasks = self.config.get("tasks", [])
            updated = False

            for i, existing_task in enumerate(tasks):
                if existing_task["name"] == task["name"]:
                    tasks[i] = task  # 上書き
                    updated = True
                    break

            if not updated:
                tasks.append(task)  # 新規追加

            # 設定ファイルに保存
            try:
                if repeat:
                    # 繰り返しタスクの場合はCronTriggerを使用
                    self.config["tasks"] = tasks
                    Config.set("tasks", tasks)
            except Exception as e:
                await interaction.response.send_message(
                    f"エラー: タスク設定の保存中に問題が発生しました: {e}", ephemeral=True
                )
                return

            # スケジュール登録
            try:
                await self.schedule_task(task)
            except Exception as e:
                await interaction.response.send_message(
                    f"エラー: タスクスケジュールの登録中に問題が発生しました: {e}", ephemeral=True
                )
                return

            # 成功レスポンス
            if updated:
                await interaction.response.send_message(
                    f"タスク '{task['name']}' を更新しました: {weekday.name} {hour}:{minute} 繰り返し: {repeat}"
                )
            else:
                await interaction.response.send_message(
                    f"タスク '{task['name']}' を追加しました: {weekday.name} {hour}:{minute} 繰り返し: {repeat}"
                )
                
        @self.tree.command(name="check_server", description="現在サーバーが起動しているかを調べます")
        async def check_server_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: check_server by {interaction.user.name}")
            status = await check_server_status(self.server_exe)
            embed = discord.Embed(
                title="サーバーは起動中です" if status else "サーバーは停止中です",
                color=0x00ff00 if status else 0xff0000
            )
            await self._interraction_send(interaction, embed, ephemeral=True)
            self.logger.info(f"Command executed completes: check_server by {interaction.user.name}")

        @self.tree.command(name="check_memory", description="現在のサーバーのメモリ使用量を調べます")
        async def check_memory_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: check_memory by {interaction.user.name}")
            embed = await check_memory_usage()
            await self._interraction_send(interaction, embed)
            self.logger.info(f"Command executed completes: check_memory by {interaction.user.name}")

        @self.tree.command(name="help", description="利用可能なコマンド一覧を表示します")
        async def help_command(interaction: discord.Interaction):
            self.logger.info(f"Command executed: help by {interaction.user.name}")
            embed = discord.Embed(
                title="コマンド一覧",
                description="以下は利用可能なコマンドの一覧です。",
                color=0x3498db
            )
            embed.add_field(name="/update_server", value=f"SteamCMDとゲームサーバーのアップデートを行います。", inline=False)
            embed.add_field(name="/start_server", value=f"{self.server_exe}を起動します", inline=False)
            embed.add_field(name="/stop_server", value=f"{self.server_exe}を停止します", inline=False)
            embed.add_field(name="/restart_server", value=f"{self.server_exe}を再起動します", inline=False)
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
            self.logger.info(f"Command executed completes: help by {interaction.user.name}")

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
                    await self._send_announcement(message)
                    await interaction.response.send_message("アナウンスを送信しました。", ephemeral=True)
                    self.logger.info(f"Command executed completes: send_announce by {interaction.user.name}")
                except Exception as e:
                    self.logger.error(f"Error in send_rest_api_announce_command: {e}")
                    await interaction.response.send_message(f"アナウンスの送信に失敗しました: {e}", ephemeral=True)

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
                    self.logger.info(f"Command executed completes: show_player by {interaction.user.name}")
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
                    self.logger.info(f"Command executed completes: show_settings by {interaction.user.name}")
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

                    self.logger.info(f"Command executed completes: show_metrics by {interaction.user.name}")
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

    async def _interraction_send(
        self, 
        interaction, 
        *args: Union[str, discord.Embed],
        ephemeral: bool = False
    ):
        if self.send_flag:
            if len(args) == 1:  # 1つだけ引数が渡された場合
                if isinstance(args[0], discord.Embed):  # Embedの場合
                    await interaction.response.send_message(embed=args[0], ephemeral=ephemeral)
                elif isinstance(args[0], str):  # 文字列の場合
                    await interaction.response.send_message(content=args[0], ephemeral=ephemeral)
                else:
                    raise TypeError("位置引数には文字列または discord.Embed を指定してください。")
            elif len(args) == 0:
                raise ValueError("位置引数が不足しています。content または embed を指定してください。")
            else:
                raise ValueError("複数の位置引数が渡されました。content または embed のみ指定してください。")
        
    async def _interraction_followup_send(
        self, 
        interaction, 
        *args: Union[str, discord.Embed],
        ephemeral: bool = False
    ):
        if self.send_flag:
            if len(args) == 1:  # 1つだけ引数が渡された場合
                if isinstance(args[0], discord.Embed):  # Embedの場合
                    await interaction.followup.send(embed=args[0], ephemeral=ephemeral)
                elif isinstance(args[0], str):  # 文字列の場合
                    await interaction.followup.send(content=args[0], ephemeral=ephemeral)
                else:
                    raise TypeError("位置引数には文字列または discord.Embed を指定してください。")
            elif len(args) == 0:
                raise ValueError("位置引数が不足しています。content または embed を指定してください。")
            else:
                raise ValueError("複数の位置引数が渡されました。content または embed のみ指定してください。")

    async def _restart_server(self, wait_minutes: int, update: bool ):
        self.logger.info(f"Task executed: restart_server")

        channel = self.client.get_channel(self.channel_id)  # チャンネルIDからチャンネルを取得
        # メッセージを投稿する
        embed = discord.Embed(
            title="サーバー再起動アナウンス",
            description="これより、サーバー再起動を開始します。"
        )
        if channel and self.send_flag:
            await channel.send(embed=embed)

        # 再起動処理の進行を報告
        if wait_minutes > 10:
            #10分以上の処理
            for remaining in range(wait_minutes, 0, -10):
                if channel and self.send_flag:
                    await channel.send(
                        embed = discord.Embed(
                            title="サーバー再起動アナウンス",
                            description=f"あと{remaining}分後にサーバーが再起動されます。攻略中や作業中の方はご注意ください。"
                        )
                    )
                if self.rest_api_plugin is not None:
                    await self._send_announcement(f"アナウンス: {remaining}分後にサーバーが再起動されます。攻略中や作業中の方はご注意ください。")
                await asyncio.sleep(600)

            # 残り時間が10分未満の場合の通知
            if wait_minutes % 10 != 0:
                remaining = wait_minutes % 10
                if channel and self.send_flag:
                    await channel.send(
                        embed = discord.Embed(
                            title="サーバー再起動アナウンス",
                            description=f"あと{remaining}分後にサーバーが再起動されます。攻略中や作業中の方はご注意ください。"
                        )
                    )
                if self.rest_api_plugin is not None:
                    await self._send_announcement(f"アナウンス: {remaining}分後にサーバーが再起動されます。攻略中や作業中の方はご注意ください。")
                await asyncio.sleep(remaining * 60)
        else:
            # 10分以下の処理
            if channel and self.send_flag:
                await channel.send(
                    embed = discord.Embed(
                        title="サーバー再起動アナウンス",
                        description=f"あと{wait_minutes}分後にサーバーが再起動されます。攻略中や作業中の方はご注意ください。"
                    )
                )
            if self.rest_api_plugin is not None:
                await self._send_announcement(f"アナウンス: {wait_minutes}分後にサーバーが再起動されます。攻略中や作業中の方はご注意ください。")
            await asyncio.sleep(wait_minutes * 60)

        # サーバー停止
        stop_embed = await stop_server(self.server_cmd_exe, self.server_exe)
        if channel and self.send_flag:
            await channel.send(embed=stop_embed)

        # サーバーアップデート（必要な場合）
        if update:
            if channel and self.send_flag:
                await channel.send(
                    embed = discord.Embed(
                        title="サーバーアップデート",
                        description=f"サーバーのアップデートを開始します。"
                    )
                )
            update_embed = await update_server(self.steamcmd_path, self.server_path, self.app_id)
            if channel and self.send_flag:
                await channel.send(embed = update_embed)

        # サーバー再起動
        start_embed = await start_server(self.server_path, self.server_exe)
        if channel and self.send_flag:
            await channel.send(embed = start_embed)
        self.logger.info(f"Task executed completes: restart_server")

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

    @tasks.loop(seconds=5)  # サーバー状態の監視
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

    async def schedule_task(self, task):
        weekday = task['weekday']
        hour = task['hour']
        minute = task['minute']
        repeat = task['repeat']  # True: 毎回, False: 1回のみ

        # CronTrigger を作成
        trigger = CronTrigger(day_of_week=weekday, hour=hour, minute=minute)

        # 事前にイベントループを取得して保存
        main_loop = asyncio.get_running_loop()

        # タスクの登録
        if repeat:
            # 繰り返しタスク
            self.scheduler.add_job(
                lambda: asyncio.run_coroutine_threadsafe(self._restart_server(60, True), main_loop),
                trigger,
                id=f"{task['name']}_{weekday}_{hour}_{minute}",
                replace_existing=True
            )
            self.logger.info(f"繰り返しタスクをスケジュール: {weekday} {hour}:{minute}")
        else:
            # 1回のみタスク
            self.scheduler.add_job(
                lambda: asyncio.run_coroutine_threadsafe(self._restart_server(60, True), main_loop),
                trigger,
                id=f"{task['name']}_{weekday}_{hour}_{minute}",
                replace_existing=True,
                next_run_time=trigger.get_next_fire_time(datetime.now())  # 次回実行時刻を設定
            )
            self.logger.info(f"1回限りのタスクをスケジュール: {weekday} {hour}:{minute}")

    async def load_scheduled_tasks(self):
        """スケジュールタスクをロード"""
        try:
            tasks = self.config.get('tasks', [])
            for task in tasks:
                self.logger.info(f"タスクのスケジュールを実施... {task}")
                await self.schedule_task(task)
            self.logger.info(f"{len(tasks)}件のタスクをスケジュールしました")
        except Exception as e:
            self.logger.error(f"Error during load_scheduled_tasks: {e}")

    async def _on_ready(self):
        self.logger.info("Bot is ready")
        try:
            await self.tree.sync()  # コマンドを同期
            await self.client.wait_until_ready()
            channel = self.client.get_channel(self.channel_id)  # チャンネルIDからチャンネルを取得

            # スケジューラを開始
            self.logger.info("Starting scheduler")
            self.scheduler.start()

            # スケジュールタスクをロード
            await self.load_scheduled_tasks()

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