#!/bin/bash

# Сохраняем текущие маршруты для сети Docker
echo "Сохраняем маршруты для сети Docker..."
DOCKER_NETWORK=$(ip route | grep "172." | head -n 1)
echo "Маршруты Docker: $DOCKER_NETWORK"

# Запускаем OpenVPN
echo "Запуск OpenVPN..."
openvpn --config /etc/openvpn/turk5_247479803.ovpn --script-security 2 --up /etc/openvpn/vpn-up.sh --daemon --log /var/log/openvpn.log

echo "Ожидание установки VPN-соединения..."
sleep 10

# Проверяем сетевые интерфейсы
echo "Проверка сетевых интерфейсов:"
ip addr | grep tun

# Восстанавливаем маршруты для Docker-сети
if [ ! -z "$DOCKER_NETWORK" ]; then
    echo "Восстанавливаем маршруты для Docker-сети..."
    ip route add $DOCKER_NETWORK
    echo "Текущие маршруты:"
    ip route
fi

# Проверка доступности сервиса базы данных
echo "Проверяем доступность базы данных..."
getent hosts db || echo "Ошибка: не удалось разрешить имя 'db'"

# Запуск приложения
echo "Запуск приложения..."
uvicorn main:app --host 0.0.0.0 --port 8000 