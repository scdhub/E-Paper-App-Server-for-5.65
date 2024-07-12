@echo off
setlocal enabledelayedexpansion

rem LocalStackの起動
docker start a0216993f560
localstack start -d
