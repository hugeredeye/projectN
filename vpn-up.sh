#!/bin/bash

# Скрипт запускается после успешного подключения VPN

# Определяем платформу
PLATFORM=$(uname -s)
echo "VPN скрипт запущен на платформе: $PLATFORM"

# Получаем значения переменных окружения
MAC_MODE=${MAC_MODE:-false}
WINDOWS_MODE=${WINDOWS_MODE:-false}

# Выбираем конфигурацию в зависимости от ОС
if [ "$PLATFORM" == "Darwin" ] || [ "$MAC_MODE" == "true" ]; then
  echo "Применяем конфигурацию VPN для macOS..."
  OS_MODE="mac"
elif [[ "$PLATFORM" == MINGW* ]] || [[ "$PLATFORM" == MSYS* ]] || [ "$WINDOWS_MODE" == "true" ]; then
  echo "Применяем конфигурацию VPN для Windows..."
  OS_MODE="windows"
else
  echo "Применяем конфигурацию VPN для Linux..."
  OS_MODE="linux"
fi

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
  if [ "$OS_MODE" == "mac" ]; then
    # Конфигурация DNS для macOS
    cat > /etc/resolv.conf << EOF
nameserver $3
nameserver $DOCKER_DNS
nameserver 8.8.8.8
nameserver 1.1.1.1
options timeout:1
EOF
  elif [ "$OS_MODE" == "windows" ]; then
    # Конфигурация DNS для Windows
    cat > /etc/resolv.conf << EOF
nameserver $3
nameserver $DOCKER_DNS
nameserver 8.8.8.8
EOF
  else
    # Конфигурация DNS для Linux
    cat > /etc/resolv.conf << EOF
nameserver $3
nameserver $DOCKER_DNS
nameserver 8.8.8.8
nameserver 1.1.1.1
EOF
  fi
fi

# Применяем специфичные настройки для разных ОС
if [ "$OS_MODE" == "mac" ]; then
  echo "Применяем специфичные настройки для macOS..."
  # Дополнительные настройки для улучшения производительности на macOS
  sysctl -w net.inet.tcp.delayed_ack=0 2>/dev/null || true
  # Добавляем маршрут к внутреннему хосту Docker для macOS
  ip route add 192.168.65.2 dev eth0 2>/dev/null || true
elif [ "$OS_MODE" == "windows" ]; then
  echo "Применяем специфичные настройки для Windows..."
  # Нет специфичных настроек для Windows
else
  echo "Применяем специфичные настройки для Linux..."
  # Нет специфичных настроек для Linux
fi

# Выводим информацию о сетевых интерфейсах для диагностики
echo "Сетевые интерфейсы после подключения VPN:"
ip addr

echo "Таблица маршрутизации после подключения VPN:"
ip route

exit 0 