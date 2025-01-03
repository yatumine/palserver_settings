import logging
import discord
from discord.ext import tasks
from discord import app_commands
import psutil
from lib.server_control import start_server, stop_server, check_server_status, check_memory_usage

class DiscordBot:
    def __init__(self, token, channel_id, server_path, server_exe, server_cmd_exe):
        logging.info("Initializing DiscordBot")
        self.token = token
        self.channel_id = int(channel_id)
        self.server_path = server_path
        self.server_exe = server_exe
        self.server_cmd_exe = server_cmd_exe
        self.server_name = server_exe.split(".")[0]

        # 状態を追跡するための変数を初期化
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
        logging.info("Registering commands")

        # 既存のコマンドを登録
        @self.tree.command(name="start_server", description=f"{self.server_exe}を起動します")
        async def start_server_command(interaction: discord.Interaction):
            embed = await start_server(self.server_path, self.server_exe)
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="stop_server", description=f"{self.server_exe}を停止します")
        async def stop_server_command(interaction: discord.Interaction):
            embed = await stop_server(self.server_cmd_exe, self.server_exe)
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="check_server", description="現在サーバーが起動しているかを調べます")
        async def check_server_command(interaction: discord.Interaction):
            status = await check_server_status()
            embed = discord.Embed(
                title="サーバーは起動中です" if status else "サーバーは停止中です",
                color=0x00ff00 if status else 0xff0000
            )
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="check_memory", description="現在のサーバーのメモリ使用量を調べます")
        async def check_memory_command(interaction: discord.Interaction):
            embed = await check_memory_usage()
            await interaction.response.send_message(embed=embed)

        # ヘルプコマンドを追加
        @self.tree.command(name="help", description="利用可能なコマンド一覧を表示します")
        async def help_command(interaction: discord.Interaction):
            embed = discord.Embed(
                title="コマンド一覧",
                description="以下は利用可能なコマンドの一覧です。",
                color=0x3498db
            )
            embed.add_field(name="/start_server", value=f"{self.server_exe}を起動します", inline=False)
            embed.add_field(name="/stop_server", value=f"{self.server_exe}を停止します", inline=False)
            embed.add_field(name="/check_server", value="現在サーバーが起動しているかを調べます", inline=False)
            embed.add_field(name="/check_memory", value="現在のサーバーのメモリ使用量を調べます", inline=False)
            embed.add_field(name="/help", value="利用可能なコマンド一覧を表示します", inline=False)
            await interaction.response.send_message(embed=embed)

        logging.info("Commands registered")

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

            if channel:
                await channel.send(embed=embed)

    @tasks.loop(minutes=1)  # サーバー状態の監視
    async def server_status_check_task(self):
        current_status = await check_server_status()

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

            if channel:
                await channel.send(embed=embed)

    async def _on_ready(self):
        logging.info("Bot is ready")
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
            await channel.send(embed=embed)

            # メモリ使用量を監視
            logging.info("Starting memory check task")
            self.memory_check_task.start()

            # サーバー状態を監視
            logging.info("Starting server status check task")
            self.server_status_check_task.start()
        except Exception as e:
            logging.error(f"Error during on_ready: {e}")

    def start(self):
        """Botを起動"""
        @self.client.event
        async def on_ready():
            await self._on_ready()

        @self.client.event
        async def on_disconnect():
            # Botが切断された時の処理
            channel = self.client.get_channel(self.channel_id)
            embed = discord.Embed(
                title="Botが停止しました",
                description="Botが正常に停止されました。",
                color=0xff0000
            )
            await channel.send(embed=embed)

        try:
            self.client.run(self.token)
        except Exception as e:
            logging.error(f"Bot failed to start: {e}")
