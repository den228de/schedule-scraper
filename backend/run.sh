#!/bin/bash

echo "🚀 Запускаю скрапер расписания BIiK в Docker..."

# Проверяем, установлен ли Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker Desktop для Windows."
    exit 1
fi

# Проверяем, запущен ли Docker
if ! docker info &> /dev/null; then
    echo "❌ Docker не запущен. Запустите Docker Desktop."
    exit 1
fi

# Останавливаем и удаляем существующие контейнеры
echo "🔄 Останавливаю существующие контейнеры..."
docker-compose down

# Собираем и запускаем
echo "🔨 Собираю Docker образ..."
docker-compose up --build -d

# Ждем запуска
echo "⏳ Жду запуска сервиса..."
sleep 10

# Проверяем статус
echo "📊 Статус сервисов:"
docker-compose ps

echo ""
echo "✅ Скрапер запущен!"
echo "🌐 Веб-интерфейс: http://localhost:8001"
echo "📱 API: http://localhost:8001/api/versions"
echo ""
echo "📋 Логи: docker-compose logs -f scraper"
echo "🛑 Остановка: docker-compose down"
