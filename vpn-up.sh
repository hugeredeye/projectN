#!/bin/bash

# Скрипт запускается после успешного подключения VPN

# Создаем резервную копию resolv.conf
echo "Создаем резервную копию resolv.conf..."
cp /etc/resolv.conf /etc/resolv.conf.backup

# Получаем DNS от VPN
if [ -n "$1" ] && [ -n "$2" ] && [ -n "$3" ]; then
  echo "Получены DNS серверы от VPN: $3"
  # Сохраняем оригинальный DNS сервер для Docker
  DOCKER_DNS=$(grep "nameserver" /etc/resolv.conf | head -n 1 | awk '{print $2}')
  echo "DNS сервер Docker: $DOCKER_DNS"
  
  # Добавляем и DNS от VPN, и DNS от Docker
  cat > /etc/resolv.conf << EOF
nameserver $3
nameserver $DOCKER_DNS
nameserver 8.8.8.8
nameserver 1.1.1.1
EOF
fi

# Выводим информацию о сетевых интерфейсах для диагностики
echo "Сетевые интерфейсы после подключения VPN:"
ip addr

echo "Таблица маршрутизации после подключения VPN:"
ip route

exit 0 