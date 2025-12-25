#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Конфигурация
VENV_DIR="venv"
DB_NAME="subscriptions_db"
DB_USER="subscriptions_user"
DB_PASSWORD="secure_password_123"
FLASK_APP="run.py"

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Функция для проверки наличия команды
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 не установлен. Пожалуйста, установите его."
        exit 1
    fi
}

setup_database() {
    print_status "Настройка базы данных PostgreSQL..."
    
    # Проверяем наличие PostgreSQL
    check_command psql
    
    # Создаем базу данных и пользователя
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || print_warning "База данных уже существует"
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || print_warning "Пользователь уже существует"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    
    # Экспортируем переменные окружения
    export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"
    
    print_status "База данных настроена"
}

install_dependencies() {
    print_status "Установка зависимостей..."
    
    # Проверяем наличие Python3 и pip
    check_command python3
    check_command pip3
    
    # Создаем виртуальное окружение
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv $VENV_DIR
        print_status "Виртуальное окружение создано"
    else
        print_warning "Виртуальное окружение уже существует"
    fi
    
    # Активируем виртуальное окружение
    source $VENV_DIR/bin/activate
    
    # Устанавливаем зависимости
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Настраиваем переменные окружения
    if [ ! -f ".env" ]; then
        cat > .env << EOL
FLASK_APP=$FLASK_APP
FLASK_ENV=development
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME
SECRET_KEY=dev-secret-key-change-in-production
EOL
        print_status "Файл .env создан"
    fi
    
    print_status "Зависимости установлены"
}

start_app() {
    print_status "Запуск Flask приложения..."
    
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Виртуальное окружение не найдено. Сначала выполните установку зависимостей."
        exit 1
    fi
    
    source $VENV_DIR/bin/activate
    export $(cat .env | xargs)
    
    # Запускаем приложение в фоновом режиме
    nohup python $FLASK_APP > flask_app.log 2>&1 &
    FLASK_PID=$!
    
    echo $FLASK_PID > flask.pid
    print_status "Приложение запущено (PID: $FLASK_PID)"
    print_status "Логи доступны в файле: flask_app.log"
}

stop_app() {
    print_status "Остановка Flask приложения..."
    
    if [ -f "flask.pid" ]; then
        FLASK_PID=$(cat flask.pid)
        if kill -0 $FLASK_PID 2>/dev/null; then
            kill $FLASK_PID
            rm flask.pid
            print_status "Приложение остановлено"
        else
            print_warning "Процесс не найден"
            rm flask.pid
        fi
    else
        print_warning "PID файл не найден"
    fi
}

run_tests() {
    print_status "Запуск тестов..."
    
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Виртуальное окружение не найдено"
        exit 1
    fi
    
    source $VENV_DIR/bin/activate
    export $(cat .env | xargs)
    
    # Создаем тестовую базу данных
    TEST_DB_NAME="${DB_NAME}_test"
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS $TEST_DB_NAME;" 2>/dev/null
    sudo -u postgres psql -c "CREATE DATABASE $TEST_DB_NAME;" 2>/dev/null
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $TEST_DB_NAME TO $DB_USER;"
    
    # Запускаем тесты
    python -m pytest tests/ -v
    
    print_status "Тесты завершены"
}

# Проверка безопасности кода
check_security() {
    print_status "Проверка безопасности кода с помощью bandit..."
    
    source $VENV_DIR/bin/activate
    bandit -r app/
    
    print_status "Проверка безопасности завершена"
}

# Основное меню
case "$1" in
    setup_db)
        setup_database
        ;;
    install)
        install_dependencies
        ;;
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    test)
        run_tests
        ;;
    security)
        check_security
        ;;
    all)
        setup_database
        install_dependencies
        start_app
        ;;
    *)
        echo "Использование: $0 {setup_db|install|start|stop|test|security|all}"
        echo ""
        echo "Команды:"
        echo "  setup_db    - Настройка базы данных"
        echo "  install     - Установка зависимостей"
        echo "  start       - Запуск приложения"
        echo "  stop        - Остановка приложения"
        echo "  test        - Запуск тестов"
        echo "  security    - Проверка безопасности"
        echo "  all         - Полная установка и запуск"
        exit 1
        ;;
esac