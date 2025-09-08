# 🚀 Скрапер расписания BIiK

Скрапер для автоматического отслеживания изменений в расписании группы на сайте BIiK.

## 🐳 Запуск в Docker

### Предварительные требования

1. **Docker Desktop** - установлен и запущен
2. **Git** - для клонирования репозитория

### Быстрый запуск

#### Windows (PowerShell)
```powershell
.\run.ps1
```

#### Linux/macOS (Bash)
```bash
chmod +x run.sh
./run.sh
```

#### Ручной запуск
```bash
# Сборка и запуск
docker-compose up --build -d

# Просмотр логов
docker-compose logs -f scraper

# Остановка
docker-compose down
```

### 🔧 Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
GROUP_CODE=cg389
GROUP_PAGE_URL=https://biik.ru/rasp/cg389.htm
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_ID=your_admin_id_here
```

### 📱 Доступ к приложению

- **Веб-интерфейс**: http://localhost:8001
- **API**: http://localhost:8001/api/versions
- **Swagger документация**: http://localhost:8001/docs

### 📊 Мониторинг

```bash
# Статус сервисов
docker-compose ps

# Логи в реальном времени
docker-compose logs -f scraper

# Использование ресурсов
docker stats
```

### 🛠️ Разработка

```bash
# Запуск в режиме разработки (с монтированием кода)
docker-compose -f docker-compose.dev.yml up

# Пересборка после изменений
docker-compose up --build
```

### 🧹 Очистка

```bash
# Остановка и удаление контейнеров
docker-compose down

# Удаление образов
docker-compose down --rmi all

# Полная очистка (включая volumes)
docker-compose down -v --rmi all
```

## 📁 Структура проекта

```
backend/
├── app.py              # FastAPI приложение
├── scraper.py          # Логика скрапинга
├── db.py              # Работа с базой данных
├── notifier.py        # Telegram уведомления
├── diff.py            # Сравнение версий
├── requirements.txt    # Python зависимости
├── Dockerfile         # Docker образ
├── docker-compose.yml # Docker Compose
├── run.ps1           # PowerShell скрипт запуска
└── run.sh            # Bash скрипт запуска
```

## 🔍 Возможные проблемы

### Порт 8001 занят
```bash
# Измените порт в docker-compose.yml
ports:
  - "8002:8000"  # Внешний порт 8002
```

### Проблемы с правами доступа
```bash
# В Windows убедитесь, что Docker Desktop запущен
# В Linux может потребоваться sudo
```

### Ошибки сборки
```bash
# Очистите кэш Docker
docker system prune -a
```

## 📞 Поддержка

При возникновении проблем проверьте:
1. Логи контейнера: `docker-compose logs scraper`
2. Статус Docker: `docker info`
3. Доступность портов: `netstat -an | findstr 8000`
