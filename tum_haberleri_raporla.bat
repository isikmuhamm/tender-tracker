@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Yatirimlar Bulten - Raporlama Sistemi
color 0B

:HEADER
cls
echo.
echo  ========================================================================
echo                YATIRIMLAR DERGISI VERITABANI RAPOR SISTEMI
echo  ========================================================================
echo.

:: Python kontrolu
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo   [HATA] Python bulunamadi!
    echo.
    echo   Python kurulu degil veya PATH'e eklenmemis.
    echo   Lutfen python.org adresinden Python yukleyin.
    echo.
    goto :END
)

:: Script dosyasi kontrolu
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_PATH=%SCRIPT_DIR%yatirimlar_bulten.py"

if not exist "%SCRIPT_PATH%" (
    color 0C
    echo   [HATA] Script dosyasi bulunamadi!
    echo.
    echo   Aranan: %SCRIPT_PATH%
    echo   Lutfen bu batch dosyasini script ile ayni klasore koyun.
    echo.
    goto :END
)

:: Veritabani kontrolu
set "DB_PATH=%SCRIPT_DIR%yatirimlar.db"
if not exist "%DB_PATH%" (
    color 0E
    echo   [UYARI] Veritabani dosyasi bulunamadi.
    echo   Ilk calistirmada olusturulacak.
    echo.
)

echo   [OK] Python kurulu
echo   [OK] Script dosyasi mevcut
echo.
echo  ------------------------------------------------------------------------
echo.
echo   TUM HABERLERI HANGI MAIL ADRESINE GONDERMEK ISTERSINIZ?
echo.
echo   (Cikmak icin 'q' yazin)
echo.

:INPUT
set "EMAIL="
set /p "EMAIL=   Mail adresi: "

:: Cikis kontrolu
if /i "%EMAIL%"=="q" goto :EXIT
if /i "%EMAIL%"=="Q" goto :EXIT

:: Bos kontrol
if "%EMAIL%"=="" (
    color 0E
    echo.
    echo   [UYARI] Mail adresi bos olamaz! Tekrar deneyin.
    echo.
    color 0B
    goto :INPUT
)

:: Basit mail format kontrolu
echo %EMAIL% | findstr /r "@.*\." >nul
if errorlevel 1 (
    color 0E
    echo.
    echo   [UYARI] Gecersiz mail formati! Ornek: ornek@mail.com
    echo.
    color 0B
    goto :INPUT
)

:: Onay
echo.
echo  ------------------------------------------------------------------------
echo.
echo   Rapor gonderilecek adres: %EMAIL%
echo.
set /p "CONFIRM=   Onayliyor musunuz? (E/H): "

if /i not "%CONFIRM%"=="E" (
    if /i not "%CONFIRM%"=="e" (
        echo.
        echo   Iptal edildi.
        echo.
        goto :INPUT
    )
)

:: Rapor gonderme
echo.
echo  ------------------------------------------------------------------------
echo.
echo   RAPOR GONDERILIYOR...
echo.
echo   Lutfen bekleyin, bu islem birkac saniye surebilir.
echo.
echo  ========================================================================
echo.

cd /d "%SCRIPT_DIR%"
python "%SCRIPT_PATH%" -reportall -to %EMAIL%
set "RESULT=%errorlevel%"

echo.
echo  ========================================================================
echo.

if %RESULT%==0 (
    color 0A
    echo  ========================================================================
    echo                                                                    
    echo     [BASARILI] Rapor gonderildi.                                  
    echo                                                                    
    echo     Alici: %EMAIL%
    echo                                                                    
    echo  ========================================================================
) else (
    color 0C
    echo  ========================================================================
    echo                                                                    
    echo     [HATA] Rapor gonderilemedi.                                   
    echo                                                                    
    echo     Olasi nedenler:                                                 
    echo     - SMTP ayarlari hatali                                          
    echo     - Internet baglantisi yok                                       
    echo     - Mail sifresi degismis                                         
    echo                                                                    
    echo     Detaylar icin yukaridaki log ciktisini inceleyin.               
    echo                                                                    
    echo  ========================================================================
)

echo.
set /p "AGAIN=   Baska bir mail adresine gondermek ister misiniz? (E/H): "
if /i "%AGAIN%"=="E" (
    color 0B
    goto :HEADER
)

:EXIT
echo.
echo  ------------------------------------------------------------------------
echo.
echo   Gule gule! Yatirimlar Bulten Raporlama Sistemi kapatiliyor...
echo.

:END
echo.
echo   Cikmak icin bir tusa basin...
pause >nul
exit /b
