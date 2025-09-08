Write-Host "🚀 Запускаю скрапер расписания BIiK в Docker..." -ForegroundColor Green

# Проверяем, установлен ли Docker
try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Docker не установлен. Установите Docker Desktop для Windows." -ForegroundColor Red
    exit 1
}

# Проверяем, запущен ли Docker
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker не запущен. Запустите Docker Desktop." -ForegroundColor Red
    exit 1
}

# Останавливаем и удаляем существующие контейнеры
Write-Host "🔄 Останавливаю существующие контейнеры..." -ForegroundColor Yellow
docker-compose down

# Собираем и запускаем
Write-Host "🔨 Собираю Docker образ..." -ForegroundColor Yellow
docker-compose up --build -d

# Ждем запуска
Write-Host "⏳ Жду запуска сервиса..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Проверяем статус
Write-Host "📊 Статус сервисов:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "✅ Скрапер запущен!" -ForegroundColor Green
Write-Host "🌐 Веб-интерфейс: http://localhost:8001" -ForegroundColor Cyan
Write-Host "📱 API: http://localhost:8001/api/versions" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Логи: docker-compose logs -f scraper" -ForegroundColor Yellow
Write-Host "🛑 Остановка: docker-compose down" -ForegroundColor Yellow
