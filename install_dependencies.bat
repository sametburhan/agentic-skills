@echo off
chcp 65001 >nul
echo ========================================================
echo Agentic Skills ve MCP Sunucuları Bağımlılık Yükleyicisi
echo ========================================================
echo.

echo Python ve Pip kontrol ediliyor...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadı! Lütfen Python'un kurulu ve PATH'e ekli olduğundan emin olun.
    pause
    exit /b 1
)

echo Bağımlılıklar yükleniyor (requirements.txt)...
pip install -r requirements.txt

echo.
echo ========================================================
echo [BAŞARILI] Tüm Python bağımlılıkları yüklendi!
echo LM Studio ayarlarından mcp_config.json dosyasını bağlayabilirsiniz.
echo ========================================================
pause
