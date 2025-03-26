#!/bin/bash

# Скрипт для настройки VPN на хост-машине для macOS
# ===================================================

echo "Настройка VPN для хост-машины (macOS)"
echo "======================================"

# Проверяем ОС
if [ "$(uname)" != "Darwin" ]; then
    echo "Этот скрипт предназначен только для macOS!"
    exit 1
fi

# Проверяем наличие файла конфигурации VPN
VPN_CONFIG="turk5_247479803.ovpn"
if [ ! -f "$VPN_CONFIG" ]; then
    echo "ОШИБКА: Файл конфигурации VPN ($VPN_CONFIG) не найден!"
    echo "Должен находиться в текущей директории."
    exit 1
fi

# Проверяем установлен ли Tunnelblick
if [ ! -d "/Applications/Tunnelblick.app" ]; then
    echo "Tunnelblick не установлен. Рекомендуется установить Tunnelblick для управления VPN."
    echo "Установите Tunnelblick с сайта: https://tunnelblick.net/downloads.html"
    
    # Или можно использовать Homebrew для установки
    if command -v brew &> /dev/null; then
        echo "Хотите установить Tunnelblick через Homebrew? (y/n)"
        read -r install_choice
        if [ "$install_choice" == "y" ]; then
            brew install --cask tunnelblick
        fi
    fi
    
    # Предлагаем использовать встроенный OpenVPN, если Tunnelblick не доступен
    echo "Альтернативно, вы можете использовать встроенный OpenVPN клиент."
    echo "Установить OpenVPN через Homebrew? (y/n)"
    read -r install_openvpn
    if [ "$install_openvpn" == "y" ]; then
        brew install openvpn
    fi
fi

# Копируем файл VPN в папку пользователя
USER_VPN_DIR="$HOME/OpenVPN"
mkdir -p "$USER_VPN_DIR"
cp "$VPN_CONFIG" "$USER_VPN_DIR/"
echo "Файл конфигурации VPN скопирован в $USER_VPN_DIR/$VPN_CONFIG"

# Создаем скрипт для запуска VPN через терминал
LAUNCH_SCRIPT="$USER_VPN_DIR/start-vpn.sh"
cat > "$LAUNCH_SCRIPT" << EOF
#!/bin/bash
# Запуск VPN через OpenVPN
sudo openvpn --config "$USER_VPN_DIR/$VPN_CONFIG" --daemon
echo "VPN запущен в фоновом режиме. Для проверки статуса используйте: ps aux | grep openvpn"
EOF
chmod +x "$LAUNCH_SCRIPT"

# Информация для пользователя
echo ""
echo "======================================"
echo "Настройка VPN завершена!"
echo ""
echo "Для запуска VPN перед работой с Docker:"
echo ""
if [ -d "/Applications/Tunnelblick.app" ]; then
    echo "Вариант 1: Использовать Tunnelblick"
    echo "- Импортируйте файл $USER_VPN_DIR/$VPN_CONFIG в Tunnelblick"
    echo "- Запустите VPN через интерфейс Tunnelblick"
fi
echo ""
echo "Вариант 2: Использовать терминал"
echo "- Выполните команду: $LAUNCH_SCRIPT"
echo ""
echo "Убедитесь, что VPN активен перед запуском Docker!"
echo "======================================" 