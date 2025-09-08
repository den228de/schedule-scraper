# 🚀 BIiK Schedule Scraper

> Автоматический скрапер расписания для BIiK с Telegram ботом и веб-интерфейсом

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://telegram.org)

## 📋 Описание

Система автоматического отслеживания изменений в расписании учебных занятий BIiK с уведомлениями в Telegram и удобным веб-интерфейсом.

### ✨ Возможности

- 🔄 **Автоматический скрапинг** каждые 20 минут
- 📱 **Telegram бот** с командами для просмотра расписания
- 🌐 **Веб-интерфейс** с современным дизайном
- 📊 **API endpoints** для интеграции
- 🐳 **Docker контейнеризация** для простого развертывания
- 🔔 **Уведомления** при изменениях расписания
- 📅 **Поддержка нескольких групп** и недель

## 🏗️ Архитектура

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   BIiK Website  │───▶│   Scraper Bot    │───▶│  SQLite DB      │
│  (biik.ru)      │    │   (Python)       │    │  (Schedule)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Telegram Bot    │
                       │  (Notifications) │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Web Interface   │
                       │  (FastAPI)       │
                       └──────────────────┘
```

## 🚀 Быстрый старт

### Предварительные требования

- Docker Desktop
- Git

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/den228de/biik-schedule-scraper.git
cd biik-schedule-scraper
```

2. **Настройте переменные окружения:**
```bash
cd backend
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

3. **Запустите через Docker:**
```bash
# Windows (PowerShell)
.\run.ps1

# Linux/macOS (Bash)
chmod +x run.sh
./run.sh
```

4. **Откройте веб-интерфейс:**
```
http://localhost:8001
```

## ⚙️ Конфигурация

### Переменные окружения

Создайте файл `.env` в папке `backend/`:

```env
# Основные настройки
GROUP_CODE=cg389
GROUP_PAGE_URL=https://biik.ru/rasp/cg389.htm
TZ=Asia/Irkutsk

# База данных
DATABASE_URL=sqlite:///./data/schedule.db

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_ID=your_admin_id_here,second_admin_id_here
```

### Настройка Telegram бота

1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Получите токен бота
3. Добавьте бота в группу с правами администратора
4. Укажите ID чата в `TELEGRAM_ADMIN_ID`

## 📱 Telegram Bot

### Команды

- `/start` - Начать работу с ботом
- `/schedule` - Показать расписание на сегодня/завтра
- `/date ДД.ММ.ГГГГ` - Показать расписание на конкретную дату
- `/status` - Статус работы скрапера
- `/help` - Справка

### Примеры

```
/schedule
/date 15.09.2025
/status
```

## 🌐 API Endpoints

### Основные endpoints

- `GET /` - Веб-интерфейс
- `GET /api/status` - Статус системы
- `GET /api/versions` - Список версий расписания
- `GET /api/schedule/{version_id}` - Расписание по версии
- `POST /api/force-update` - Принудительное обновление

### Примеры запросов

```bash
# Статус системы
curl https://your-domain.com/api/status

# Принудительное обновление
curl -X POST https://your-domain.com/api/force-update

# Список версий
curl https://your-domain.com/api/versions
```

## 🐳 Docker

### Команды Docker

```bash
# Сборка и запуск
docker-compose up --build -d

# Просмотр логов
docker-compose logs -f scraper

# Остановка
docker-compose down

# Перезапуск
docker-compose restart scraper
```

### Мониторинг

```bash
# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats

# Логи в реальном времени
docker-compose logs -f scraper
```

## 🛠️ Разработка

### Структура проекта

```
biik-schedule-scraper/
├── backend/                 # Основной код
│   ├── app.py              # FastAPI приложение
│   ├── scraper.py          # Логика скрапинга
│   ├── notifier.py         # Telegram бот
│   ├── db.py               # Работа с БД
│   ├── diff.py             # Сравнение версий
│   ├── static/             # Статические файлы
│   │   ├── style.css       # Стили
│   │   └── app.js          # JavaScript
│   ├── data/               # База данных
│   ├── docker-compose.yml  # Docker конфигурация
│   ├── Dockerfile          # Docker образ
│   └── requirements.txt    # Python зависимости
├── anf1project.ru/         # Дополнительные файлы (исключено из Git)
└── README.md               # Документация
```

### Локальная разработка

```bash
# Установка зависимостей
cd backend
pip install -r requirements.txt

# Запуск в режиме разработки
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## 📊 Мониторинг и логи

### Просмотр логов

```bash
# Все логи
docker-compose logs scraper

# Последние 50 строк
docker-compose logs --tail=50 scraper

# Логи в реальном времени
docker-compose logs -f scraper

# Фильтрация по ключевым словам
docker-compose logs scraper | grep -E "(ERROR|WARN|✅|❌)"
```

### Типичные проблемы

1. **Ошибка базы данных**: `attempt to write a readonly database`
   - **Решение**: Проверьте права доступа к папке `data/`

2. **Бот не отвечает в чате**
   - **Решение**: Дайте боту права администратора в группе

3. **Расписание не обновляется**
   - **Решение**: Проверьте доступность сайта biik.ru

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature ветку (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 👨‍💻 Автор

**Andrey Fedorov** ([@den228de](https://github.com/den228de))

- 🌐 Website: [anf1project.ru](https://anf1project.ru)
- 📧 Email: a.lng56@yandex.ru
- 📧 Telegram: [@nvrbe4](https://t.me/nvrbe4)
- 📍 Location: Russia, Kazan

## 🙏 Благодарности

- [FastAPI](https://fastapi.tiangolo.com) - современный веб-фреймворк
- [aiogram](https://aiogram.dev) - Telegram Bot API
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - парсинг HTML
- [SQLModel](https://sqlmodel.tiangolo.com) - работа с базой данных

---

⭐ **Если проект был полезен, поставьте звезду!** ⭐