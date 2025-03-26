#!/bin/bash

# Скрипт запуска приложения без VPN (VPN должен быть запущен на хост-машине)
echo "Запуск приложения без инициализации VPN (VPN должен работать на хосте)"

# Определяем платформу
PLATFORM=$(uname -s)
echo "Запуск на платформе: $PLATFORM"

# Получаем значения переменных окружения
MAC_MODE=${MAC_MODE:-false}
VPN_MODE=${VPN_MODE:-container}

echo "Режим VPN: $VPN_MODE"

if [ "$VPN_MODE" != "host" ]; then
    echo "ВНИМАНИЕ: VPN должен быть запущен на хост-машине!"
    echo "Для macOS рекомендуется запустить Tunnelblick или другой OpenVPN клиент"
fi

# Для macOS добавляем специальные настройки для доступа к хосту
if [ "$PLATFORM" == "Darwin" ] || [ "$MAC_MODE" == "true" ]; then
    echo "Применяем оптимизации для macOS..."
    
    # Проверяем доступ к хосту
    ping -c 1 host.docker.internal || echo "Предупреждение: Не могу пинговать хост"
    
    # Настраиваем DNS для работы с хостом
    echo "Настройка DNS для работы с хост-машиной..."
    cat > /etc/resolv.conf << EOF
nameserver 8.8.8.8
nameserver 1.1.1.1
EOF
fi

# Проверка доступности сервиса базы данных
echo "Проверяем доступность базы данных..."
getent hosts db || echo "Ошибка: не удалось разрешить имя 'db'"

# Подготовка к запуску
echo "Подготовка к запуску..."
mkdir -p /app/uploads /app/logs /app/vector_db

# Запуск приложения
echo "Запуск приложения..."
uvicorn main:app --host 0.0.0.0 --port 8000 