FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Настройка репозиториев и установка пакетов в один слой
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        antiword \
        build-essential \
        python3-dev \
        libpq-dev \
        postgresql-client \
        openvpn \
        iptables \
        net-tools \
        iproute2 \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Копируем конфигурационные файлы VPN
COPY turk5_247479803.ovpn /etc/openvpn/
COPY vpn-up.sh /etc/openvpn/
RUN chmod 600 /etc/openvpn/turk5_247479803.ovpn && \
    chmod +x /etc/openvpn/vpn-up.sh && \
    touch /var/log/openvpn.log && \
    chmod 666 /var/log/openvpn.log

# Копируем файлы зависимостей
COPY requirements.txt /app/

# Устанавливаем зависимости Python
# Используем pip 24.0 для совместимости с textract 1.6.5
RUN pip install --no-cache-dir pip==24.0 && \
    pip install --no-cache-dir -r requirements.txt

# Создаем необходимые директории
RUN mkdir -p /app/uploads /app/logs /app/vector_db

# Копируем файлы проекта
COPY . /app/
COPY start.sh /app/
RUN chmod +x /app/start.sh

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GROQ_API_KEY=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

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["/app/start.sh"] 