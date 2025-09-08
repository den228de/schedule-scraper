# backend/app.py
import os, asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from db import init_db, list_versions
try:
    from diff import check_and_store
except ImportError as e:
    print(f"Warning: diff module import failed: {e}")
    # Fallback функция
    async def check_and_store(group_code: str, url: str):
        print(f"DIFF CHECK: {group_code} - {url}")
        return None
try:
    from notifier import notify_admin, close as bot_close
except ImportError:
    # Fallback если notifier не работает
    async def notify_admin(text: str):
        print(f"NOTIFICATION: {text}")
    async def bot_close():
        pass

GROUP_CODE = os.getenv("GROUP_CODE", "cg389")
GROUP_URL  = os.getenv("GROUP_PAGE_URL", "https://biik.ru/rasp/cg389.htm")

app = FastAPI(title="BIiK Timetable Scraper")

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def on_startup():
    init_db()
    
    # Запускаем Telegram бот в фоне
    try:
        from notifier import start_bot
        asyncio.create_task(start_bot())
        print("✅ Telegram бот запущен")
    except Exception as e:
        print(f"⚠️ Telegram бот не запущен: {e}")
    
    # Первичный парсинг при запуске, если БД пустая
    try:
        items = list_versions(GROUP_CODE, 1)
        if not items:
            print("🔄 База данных пустая, запускаем первичный парсинг...")
            await run_job()
        else:
            print(f"✅ В базе данных уже есть {len(items)} версий расписания")
    except Exception as e:
        print(f"⚠️ Ошибка при проверке БД: {e}")
        print("🔄 Запускаем первичный парсинг...")
        await run_job()
    
    # Запускаем планировщик
    sched = AsyncIOScheduler(timezone=os.getenv("TZ","Asia/Irkutsk"))
    
    # Парсинг каждые 20 минут
    sched.add_job(run_job, 'interval', minutes=20, id='schedule_check')
    
    # Дополнительно два раза в день: 06:30 и 18:30
    for h in (6, 18):
        sched.add_job(run_job, CronTrigger(hour=h, minute=30), id=f'schedule_daily_{h}')
    
    sched.start()
    print("✅ Планировщик запущен: каждые 20 минут + 06:30 и 18:30")

async def run_job():
    try:
        print(f"🔄 Запуск проверки расписания {GROUP_CODE}...")
        diff = check_and_store(GROUP_CODE, GROUP_URL)
        
        if diff:
            print(f"✅ Обнаружены изменения: неделя {diff.get('week', 'N/A')}, записей: {diff.get('count', 0)}")
            await notify_admin(f"🗓 Обновилось расписание {GROUP_CODE} (неделя {diff.get('week', 'N/A')}), записей: {diff.get('count', 0)}\n{GROUP_URL}")
        else:
            print("ℹ️ Изменений в расписании не обнаружено")
            
    except Exception as e:
        error_msg = f"❌ Ошибка при проверке расписания: {e}"
        print(error_msg)
        try:
            await notify_admin(error_msg)
        except Exception as notify_error:
            print(f"⚠️ Не удалось отправить уведомление: {notify_error}")

@app.get("/api/versions")
def api_versions():
    return JSONResponse([{
        "id": v.id, "week": v.week_start, "created_at": v.created_at.isoformat()
    } for v in list_versions(GROUP_CODE, 20)])

@app.get("/api/schedule/{version_id}")
def api_schedule(version_id: int):
    try:
        from db import list_versions
        items = list_versions(GROUP_CODE, 1)
        if items and items[0].id == version_id:
            from json import loads
            schedule_data = loads(items[0].payload)
            return JSONResponse(schedule_data)
        else:
            return JSONResponse({"error": "Версия не найдена"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/force-update")
async def force_update():
    """Принудительный запуск обновления расписания"""
    try:
        print("🔄 Принудительный запуск обновления расписания...")
        await run_job()
        return JSONResponse({"status": "success", "message": "Обновление запущено"})
    except Exception as e:
        error_msg = f"Ошибка при принудительном обновлении: {e}"
        print(f"❌ {error_msg}")
        return JSONResponse({"status": "error", "message": error_msg}, status_code=500)

@app.get("/api/status")
def api_status():
    """Статус системы"""
    try:
        from db import list_versions
        items = list_versions(GROUP_CODE, 1)
        
        if items:
            latest = items[0]
            from json import loads
            schedule_data = loads(latest.payload)
            return JSONResponse({
                "status": "running",
                "last_update": latest.created_at.isoformat(),
                "week": latest.week_start,
                "records_count": len(schedule_data),
                "group": GROUP_CODE
            })
        else:
            return JSONResponse({
                "status": "no_data",
                "message": "База данных пустая",
                "group": GROUP_CODE
            })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "group": GROUP_CODE
        }, status_code=500)

@app.get("/")
def web_home():
    html = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Расписание BIiK - CG389</title>
        <link rel="stylesheet" href="/static/style.css">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <meta name="format-detection" content="telephone=no">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="default">
        <meta name="apple-mobile-web-app-title" content="Расписание BIiK">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="msapplication-TileColor" content="#2481cc">
        <meta name="theme-color" content="#2481cc">
    </head>
    <body>
        <div class="header">
            <h1>📅 Расписание BIiK</h1>
            <div class="subtitle">Группа CG389</div>
        </div>
        
        <div class="schedule-container">
            <div class="loading">
                <div class="spinner"></div>
                <div>Загружаем расписание...</div>
            </div>
        </div>
        
        <button class="fab-button" title="Обновить">🔄</button>
        
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <script src="/static/app.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.on_event("shutdown")
async def on_shutdown():
    await bot_close()
