#!/bin/bash

# Определяем операционную систему
OS_TYPE=$(uname -s)
echo "Определена операционная система: $OS_TYPE"

# Определяем нужный файл конфигурации
case "$OS_TYPE" in
  "Darwin")
    echo "Обнаружена macOS, использую оптимизированную конфигурацию для macOS"
    COMPOSE_FILE="docker-compose.mac.yml"
    ;;
  "MINGW"*|"MSYS"*|"CYGWIN"*)
    echo "Обнаружена Windows, использую оптимизированную конфигурацию для Windows"
    COMPOSE_FILE="docker-compose.windows.yml"
    ;;
  *)
    echo "Обнаружена Linux или другая ОС, использую стандартную конфигурацию"
    COMPOSE_FILE="docker-compose.linux.yml"
    ;;
esac

# Проверяем наличие файла конфигурации
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "ОШИБКА: Файл конфигурации $COMPOSE_FILE не найден!"
  exit 1
fi

echo "Выбран файл конфигурации: $COMPOSE_FILE"

# Проверяем, передан ли параметр (например, up, down, build и т.д.)
if [ $# -eq 0 ]; then
  echo "Запускаю Docker с выбранной конфигурацией..."
  docker-compose -f "$COMPOSE_FILE" up
else
  echo "Выполняю команду docker-compose $@ с выбранной конфигурацией..."
  docker-compose -f "$COMPOSE_FILE" "$@"
fi 