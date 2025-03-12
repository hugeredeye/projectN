# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Настройка репозиториев и установка пакетов
RUN echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries \
    && echo "deb http://mirror.yandex.ru/debian/ bookworm main" > /etc/apt/sources.list \
    && echo "deb http://mirror.yandex.ru/debian-security/ bookworm-security main" >> /etc/apt/sources.list \
    && echo "deb http://mirror.yandex.ru/debian/ bookworm-updates main" >> /etc/apt/sources.list \
    && apt-get update && apt-get install -y antiword && rm -rf /var/lib/apt/lists \
    && apt-get update \
    && apt-get install -y \
        build-essential \
        python3-dev \
        libpq-dev \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Создаем необходимые директории
RUN mkdir -p uploads logs vector_db

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 