@echo off
setlocal enabledelayedexpansion

set curent_dir=%~dp0
call :GetNowTime
echo !year!/!month!/!day! !hour!:!minute!:!sec!.!ms!
call :Call_SAM_function .\_00_sam_del.bat
call :Call_SAM_function .\_01_sam_build.bat
call :Call_SAM_function .\_02_sam_dep.bat
rem pause

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

rem SAM処理のbatファイル呼び出し
:Call_SAM_function
	call !curent_dir!%1 samlocal
	cd !curent_dir!
	exit /b
