@echo off
setlocal enabledelayedexpansion

if "%~1" == "" (
	echo [delete]param is None.
	exit /b
)
set curent_dir=%~dp0
cd !curent_dir!..\src
call :GetNowTime
echo %1-delete !year!/!month!/!day! !hour!:!minute!:!sec!.!ms!
%1 delete --no-prompts
exit /b

rem 現在時刻の取得
:GetNowTime
	set NOW_DATE=%date%
	set NOW_TIME=%time: =0%
	set year=!NOW_DATE:~0,4!
	set month=!NOW_DATE:~5,2!
	set day=!NOW_DATE:~8,2!

	set hour=!NOW_TIME:~0,2!
	set minute=!NOW_TIME:~3,2!
	set sec=!NOW_TIME:~6,2!
	set ms=!NOW_TIME:~9,2!
	exit /b
