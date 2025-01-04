# PyInstallerのビルドと圧縮を行うスクリプト

# ビルド用の変数定義
$scriptName = "main.py"
$outputName = "ServerSetting"
$distDir = "dist"
$buildDir = "build"
$outputDir = "$distDir\$outputName"
$zipFileName = "$outputName.zip"

# 現在の作業ディレクトリを保存
$originalDir = Get-Location

# ビルドコマンド 
$pyInstallerCommand = @(
    "pyinstaller",
    "--onedir",
    "--windowed",
    "--clean",
    "--noupx",
    "--noconfirm",
    "--hidden-import=PySide6.QtGui",
    "--hidden-import=PySide6.QtWidgets",
    "--icon=images/256.ico",
    "--add-data 'conf/app.json;conf'",
    "--add-data 'conf/setting_key_map.json;conf'",
    "--add-data 'images/256.ico;images'",
    "--add-data 'plugins/rcon_plugin.py;plugins'",
    "--add-data 'plugins/rest_api_plugin.py;plugins'",
    "--name ServerSetting main.py"
) -join " "

# ビルドプロセス開始
Write-Host "Starting build process..."
Invoke-Expression $pyInstallerCommand

# ビルド成功確認
if (-Not (Test-Path $outputDir)) {
    Write-Host "Build failed or output directory not found." -ForegroundColor Red
    Set-Location $originalDir  # ディレクトリを元に戻す
    exit 1
}

Write-Host "Build successful. Proceeding to compression..."

# distディレクトリに移動して中身を圧縮
Set-Location $outputDir

if (Test-Path "$distDir\$zipFileName") {
    Remove-Item "$distDir\$zipFileName"
}

Compress-Archive -Path * -DestinationPath "../$zipFileName" -Force

# 圧縮成功確認
if (Test-Path "../$zipFileName") {
    Write-Host "Compression successful: $zipFileName" -ForegroundColor Green
} else {
    Write-Host "Compression failed." -ForegroundColor Red
    Set-Location $originalDir  # ディレクトリを元に戻す
    exit 1
}

# ディレクトリを元に戻す
Set-Location $originalDir

# 後処理（任意でビルドディレクトリを削除）
Write-Host "Cleaning up build files..."
if (Test-Path $buildDir) {
    Remove-Item -Recurse -Force $buildDir
}

Write-Host "Script execution completed."
