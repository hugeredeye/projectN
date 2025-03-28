# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app
COPY . /app

# Настройка репозиториев и установка пакетов
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries \
    && echo "deb http://mirror.yandex.ru/debian/ bookworm main" > /etc/apt/sources.list \
    && echo "deb http://mirror.yandex.ru/debian-security/ bookworm-security main" >> /etc/apt/sources.list \
    && echo "deb http://mirror.yandex.ru/debian/ bookworm-updates main" >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y \
        antiword \
        build-essential \
        python3-dev \
        libpq-dev \
        postgresql-client \
        openvpn \
        iptables \
        net-tools \
        iproute2 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Создаем необходимые директории
RUN mkdir -p uploads logs vector_db

# Копируем конфигурационный файл VPN и даем разрешения
COPY turk5_247479803.ovpn /etc/openvpn/
RUN chmod 600 /etc/openvpn/turk5_247479803.ovpn

# Копируем скрипт для настройки DNS и даем разрешения
COPY vpn-up.sh /etc/openvpn/vpn-up.sh
RUN chmod +x /etc/openvpn/vpn-up.sh

# Создаем файл для логов OpenVPN
RUN touch /var/log/openvpn.log && chmod 666 /var/log/openvpn.log

# Копируем скрипт запуска и даем ему права на выполнение
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV GROQ_API_KEY=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

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["/app/start.sh"] 