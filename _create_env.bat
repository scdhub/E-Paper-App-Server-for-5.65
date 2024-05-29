@echo off
setlocal enabledelayedexpansion

set curent_dir=%~dp0
cd !curent_dir!

set VENV_DIR=.venv
rem python仮想環境フォルダが存在しない
if not exist !VENV_DIR! (
	rem python仮想環境を作成
	py -m venv !VENV_DIR!
)
rem 仮想環境アクティブ化
call !VENV_DIR!\Scripts\activate.bat
rem ビルドに必要なライブラリをインストール
py -m pip install -r .\bat\requirements.txt
py -m pip install -r .\src\requirements.txt
rem python仮想環境起動
start !VENV_DIR!\Scripts\activate.bat
exit /b
