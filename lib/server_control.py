import os
import subprocess
import psutil
import discord

async def start_server(server_path: str, server_exe: str) -> discord.Embed:
    """
    サーバーを起動する関数
    """
    try:
        # server_pathとserver_exeを結合してサーバーを起動
        server_file = os.path.join(server_path, server_exe)
        subprocess.run(["start", server_file], shell=True)
        return discord.Embed(
            title=f"{server_exe}を起動しました",
            color=0x00ff00
        )
    except Exception as e:
        return discord.Embed(
            title=f"{server_exe}を起動できませんでした",
            description=f"Error: {str(e)}",
            color=0xff0000
        )

async def stop_server(server_cmd_exe: str, server_exe: str) -> discord.Embed:
    """
    サーバーを停止する関数
    """
    try:
        subprocess.run(["taskkill", "/IM", server_cmd_exe, "/F"], shell=True)
        return discord.Embed(
            title=f"{server_exe}を停止しました",
            color=0xff0000
        )
    except Exception as e:
        return discord.Embed(
            title=f"{server_exe}を停止できませんでした",
            description=f"Error: {str(e)}",
            color=0xff0000
        )

async def check_server_status() -> bool:
    """
    サーバーの状態を確認する関数
    """
    return "PalServer.exe" in (p.name() for p in psutil.process_iter())

async def check_memory_usage() -> discord.Embed:
    """
    メモリ使用量を確認する関数
    """
    memory_usage = psutil.virtual_memory().percent
    return discord.Embed(
        title=f"現在のメモリ使用量は{memory_usage}%です",
        color=0x0000ff
    )
