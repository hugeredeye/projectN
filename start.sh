#!/bin/bash

# Определяем платформу
PLATFORM=$(uname -s)
echo "Запуск на платформе: $PLATFORM"

# Получаем значения переменных окружения
MAC_MODE=${MAC_MODE:-false}
WINDOWS_MODE=${WINDOWS_MODE:-false}

# Настройки в зависимости от платформы
if [ "$PLATFORM" == "Darwin" ] || [ "$MAC_MODE" == "true" ]; then
    echo "Используем конфигурацию для macOS..."
    VPN_TIMEOUT=20
    NETWORK_SETUP="mac"
    ROUTE_METHOD="mac"
elif [[ "$PLATFORM" == MINGW* ]] || [[ "$PLATFORM" == MSYS* ]] || [ "$WINDOWS_MODE" == "true" ]; then
    echo "Используем конфигурацию для Windows..."
    VPN_TIMEOUT=5
    NETWORK_SETUP="windows"
    ROUTE_METHOD="windows"
else
    echo "Используем конфигурацию для Linux..."
    VPN_TIMEOUT=10
    NETWORK_SETUP="linux"
    ROUTE_METHOD="linux"
fi

# Функция настройки сети для разных ОС
setup_network() {
    if [ "$NETWORK_SETUP" == "mac" ]; then
        echo "Настройка сети для macOS..."
        # Специфичные настройки для macOS
        sysctl -w net.inet.tcp.delayed_ack=0 2>/dev/null || true
    elif [ "$NETWORK_SETUP" == "windows" ]; then
        echo "Настройка сети для Windows..."
        # Нет специфичных настроек для Windows в этой функции
    else
        echo "Настройка сети для Linux..."
        # Нет специфичных настроек для Linux в этой функции
    fi
}

# Функция восстановления маршрутов
restore_routes() {
    # Сохраняем текущие маршруты для сети Docker
    echo "Сохраняем маршруты для сети Docker..."
    DOCKER_NETWORK=$(ip route | grep "172." | head -n 1)
    echo "Маршруты Docker: $DOCKER_NETWORK"

    if [ "$ROUTE_METHOD" == "mac" ]; then
        echo "Восстановление маршрутов для macOS..."
        if [ ! -z "$DOCKER_NETWORK" ]; then
            echo "Восстанавливаем маршруты для Docker-сети (macOS)..."
            ip route add $DOCKER_NETWORK || true
            echo "Добавляем маршрут к host.docker.internal..."
            ip route add 192.168.65.2 dev eth0 || true
        fi
    elif [ "$ROUTE_METHOD" == "windows" ]; then
        echo "Восстановление маршрутов для Windows..."
        if [ ! -z "$DOCKER_NETWORK" ]; then
            echo "Восстанавливаем маршруты для Docker-сети (Windows)..."
            ip route add $DOCKER_NETWORK || true
        fi
    else
        echo "Восстановление маршрутов для Linux..."
        if [ ! -z "$DOCKER_NETWORK" ]; then
            echo "Восстанавливаем маршруты для Docker-сети (Linux)..."
            ip route add $DOCKER_NETWORK || true
        fi
    fi
}

# Настройка сети для соответствующей ОС
setup_network

# Запускаем OpenVPN
echo "Запуск OpenVPN..."
openvpn --config /etc/openvpn/turk5_247479803.ovpn --script-security 2 --up /etc/openvpn/vpn-up.sh --daemon --log /var/log/openvpn.log

echo "Ожидание установки VPN-соединения... ($VPN_TIMEOUT секунд)"
sleep $VPN_TIMEOUT

# Проверяем сетевые интерфейсы
echo "Проверка сетевых интерфейсов:"
ip addr | grep tun

# Восстанавливаем маршруты
restore_routes

echo "Текущие маршруты:"
ip route

# Проверка доступности сервиса базы данных
echo "Проверяем доступность базы данных..."
getent hosts db || echo "Ошибка: не удалось разрешить имя 'db'"

# Запуск приложения
echo "Запуск приложения..."
uvicorn main:app --host 0.0.0.0 --port 8000 