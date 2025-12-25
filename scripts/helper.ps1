# scripts/helper.ps1 - ТОЛЬКО ДЛЯ ТЕСТИРОВАНИЯ НА WINDOWS
param(
    [string]$Action = "help"
)

$VENV_DIR = "venv"
$DB_NAME = "subscriptions_db"
$DB_USER = "subscriptions_user" 
$DB_PASSWORD = "secure_password_123"
$FLASK_APP = "run.py"

function Write-Status { Write-Host "[✓] $($args[0])" -ForegroundColor Green }
function Write-ErrorMsg { Write-Host "[✗] $($args[0])" -ForegroundColor Red }
function Write-WarningMsg { Write-Host "[!] $($args[0])" -ForegroundColor Yellow }

function SetupDatabase {
    Write-Status "Настройка базы данных PostgreSQL..."
    
    # Проверяем наличие PostgreSQL
    if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
        Write-ErrorMsg "PostgreSQL не найден. Для Windows используйте pgAdmin"
        return
    }
    
    # Создаем базу данных
    try {
        & psql -U postgres -c "CREATE DATABASE $DB_NAME;" 2>$null
        Write-Status "База данных создана"
    } catch { Write-WarningMsg "База данных уже существует" }
    
    # Создаем пользователя
    try {
        & psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>$null
        Write-Status "Пользователь создан"
    } catch { Write-WarningMsg "Пользователь уже существует" }
    
    # Даем права
    & psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>$null
    
    Write-Status "Настройка базы данных завершена"
}

function InstallDependencies {
    Write-Status "Установка зависимостей..."
    
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-ErrorMsg "Python не найден"
        return
    }
    
    # Создаем виртуальное окружение
    if (-not (Test-Path $VENV_DIR)) {
        python -m venv $VENV_DIR
        Write-Status "Виртуальное окружение создано"
    } else {
        Write-WarningMsg "Виртуальное окружение уже существует"
    }
    
    # Активируем и устанавливаем
    & "$VENV_DIR\Scripts\Activate.ps1"
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Создаем .env если нет
    if (-not (Test-Path ".env")) {
        @"
FLASK_APP=$FLASK_APP
FLASK_ENV=development
DATABASE_URL=postgresql://$DB_USER`:$DB_PASSWORD@localhost/$DB_NAME
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=jwt-secret-key-change-me-too
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Write-Status "Файл .env создан"
    }
    
    Write-Status "Зависимости установлены"
}

function StartApp {
    Write-Status "Запуск Flask приложения..."
    
    if (-not (Test-Path $VENV_DIR)) {
        Write-ErrorMsg "Сначала выполните установку зависимостей"
        return
    }
    
    & "$VENV_DIR\Scripts\Activate.ps1"
    
    # Загружаем .env
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
            }
        }
    }
    
    # Запускаем
    $process = Start-Process python -ArgumentList $FLASK_APP -PassThru -NoNewWindow
    $processId = $process.Id
    $processId | Out-File "flask.pid"
    
    Write-Status "Приложение запущено (PID: $processId)"
    Write-Status "Доступно по адресу: http://localhost:5000"
}

function StopApp {
    Write-Status "Остановка приложения..."
    
    if (Test-Path "flask.pid") {
        $processId = Get-Content "flask.pid"
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Remove-Item "flask.pid" -Force
        Write-Status "Приложение остановлено"
    } else {
        Write-WarningMsg "PID файл не найден"
    }
}

function RunTests {
    Write-Status "Запуск тестов..."
    
    if (-not (Test-Path $VENV_DIR)) {
        Write-ErrorMsg "Сначала выполните установку зависимостей"
        return
    }
    
    & "$VENV_DIR\Scripts\Activate.ps1"
    
    # Запускаем тесты
    python -m pytest tests/ -v
    
    Write-Status "Тесты завершены"
}

function CheckSecurity {
    Write-Status "Проверка безопасности с помощью bandit..."
    
    if (-not (Test-Path $VENV_DIR)) {
        Write-ErrorMsg "Сначала выполните установку зависимостей"
        return
    }
    
    & "$VENV_DIR\Scripts\Activate.ps1"
    bandit -r app/
    
    Write-Status "Проверка безопасности завершена"
}

# Основная логика
switch ($Action) {
    "setup_db" { SetupDatabase }
    "install" { InstallDependencies }
    "start" { StartApp }
    "stop" { StopApp }
    "test" { RunTests }
    "security" { CheckSecurity }
    "all" { SetupDatabase; InstallDependencies; StartApp }
    default {
        Write-Host "Использование: .\scripts\helper.ps1 {setup_db|install|start|stop|test|security|all}" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Команды:" -ForegroundColor Yellow
        Write-Host "  setup_db    - Настройка базы данных"
        Write-Host "  install     - Установка зависимостей"
        Write-Host "  start       - Запуск приложения"
        Write-Host "  stop        - Остановка приложения"
        Write-Host "  test        - Запуск тестов"
        Write-Host "  security    - Проверка безопасности"
        Write-Host "  all         - Полная установка и запуск"
    }
}