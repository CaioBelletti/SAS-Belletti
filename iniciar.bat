@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d %~dp0

echo ===============================================
echo   Belletti Cards Universe - PDV
echo ===============================================
echo.

set PYTHON_CMD=

rem Tenta primeiro o "py launcher" (mais confiavel no Windows, nao
rem sofre com o atalho falso da Microsoft Store).
py -3 --version >nul 2>nul
if not errorlevel 1 (
    set PYTHON_CMD=py -3
    goto :python_ok
)

rem Tenta o comando "python" e confere se nao e o atalho falso da Store.
for /f "delims=" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo !PYVER! | findstr /C:"Microsoft Store" >nul
if not errorlevel 1 goto :python_ausente
echo !PYVER! | findstr /C:"Python" >nul
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :python_ok
)

:python_ausente
echo [ERRO] O Python nao esta instalado corretamente neste computador.
echo.
echo Siga estes passos:
echo   1. Baixe o Python em https://www.python.org/downloads/
echo   2. Na instalacao, marque a caixa "Add Python to PATH"
echo   3. Se aparecer uma tela pedindo pra abrir a Microsoft Store ao
echo      rodar este arquivo, va em:
echo      Configuracoes ^> Aplicativos ^> Configuracoes avancadas do
echo      aplicativo ^> Aliases de execucao do aplicativo
echo      E desative "python.exe" e "python3.exe"
echo   4. Depois disso, execute este arquivo novamente.
echo.
pause
exit /b 1

:python_ok
echo Python encontrado, usando: %PYTHON_CMD%
echo.

if not exist venv (
    echo [1/5] Primeira execucao detectada. Criando ambiente virtual...
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        pause
        exit /b 1
    )
) else (
    echo [1/5] Ambiente virtual ja existe, pulando esta etapa.
)

call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERRO] Falha ao ativar o ambiente virtual.
    pause
    exit /b 1
)

echo [2/5] Verificando dependencias instaladas...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERRO] Falha ao instalar as dependencias. Veja a mensagem acima.
    pause
    exit /b 1
)

echo [3/5] Aplicando atualizacoes no banco de dados...
python manage.py migrate --noinput
if errorlevel 1 (
    echo [ERRO] Falha ao aplicar as migracoes. Veja a mensagem acima.
    pause
    exit /b 1
)
python manage.py criar_perfis_padrao >nul 2>nul

echo [4/5] Verificando usuario administrador...
python scripts\verificar_admin.py
if errorlevel 1 (
    echo.
    echo Nenhum usuario administrador encontrado.
    echo Vamos criar o seu agora ^(preencha usuario, e-mail e senha^):
    echo.
    python manage.py createsuperuser
)

echo [5/5] Iniciando o sistema...
echo.
echo O sistema vai abrir no navegador em alguns segundos.
echo Para PARAR o sistema, feche esta janela ou aperte Ctrl+C.
echo.
echo Para acessar pelo CELULAR: conecte o celular na MESMA rede Wi-Fi
echo deste computador, e digite no navegador do celular um dos enderecos abaixo:
echo.
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    echo   http://%%a:8000/ ^(troque os espacos do inicio se precisar^)
)
echo.

start "" http://127.0.0.1:8000/
python manage.py runserver 0.0.0.0:8000

pause
