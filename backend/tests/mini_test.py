import os, asyncio, re, json, shutil
from types import SimpleNamespace


def setup_test_db():
    # Используем отдельный файл БД для тестов
    os.makedirs('./data', exist_ok=True)
    os.environ['DATABASE_URL'] = 'sqlite:///./data/test_schedule.db'
    # Чистим предыдущий файл БД, если был
    try:
        if os.path.exists('./data/test_schedule.db'):
            os.remove('./data/test_schedule.db')
    except Exception:
        pass


def test_scraper_no_duplicates():
    # Минимальный HTML, имитирующий структуру страницы
    html = '''
    <table>
      <tr><th>29.09.2025 Пн-1</th><th>1</th><th>ОС (Лек) 301 Белоусова М.В.</th></tr>
      <tr><td> </td><td>2</td><td>ФЛП (Практич.) 319 Елтунова И.Б.</td></tr>
      <tr><td> </td><td>5</td><td>ТСВПС (Практич.) 308 Извеков Я.О.</td></tr>
      <!-- мусорная строка как в логах: ["8",""] -->
      <tr><td> </td><td>8</td><td></td></tr>
      <!-- дубликат последней пары (не должен остаться после нормализации+дедупа) -->
      <tr><td> </td><td>5</td><td>ТСВПС (Практич.) 308 Извеков Я.О.</td></tr>
    </table>
    '''
    from scraper import normalize_schedule
    items = normalize_schedule(html)
    # Проверяем, что нет дубликатов по ключу
    seen = set(); dups = 0
    for i in items:
        key = (i.get('pair'), i.get('time'), i.get('subject'), i.get('room'), i.get('kind'), i.get('teacher'))
        if key in seen:
            dups += 1
        seen.add(key)
    assert dups == 0, f"Найдены дубликаты: {dups}"
    # Проверяем, что мусорной строки нет
    for i in items:
        raw = i.get('raw')
        assert not (isinstance(raw, list) and len(raw) == 2 and str(raw[0]).isdigit() and (raw[1] or '') == ''), 'Обнаружена мусорная строка'


async def test_group_rate_limit():
    # Настраиваем тестовую БД
    setup_test_db()
    from db import init_db, get_user_daily_count
    init_db()

    # Импортируем проверку лимита
    from notifier import _check_and_increment_limit
    from datetime import datetime

    def make_message(chat_id: int, user_id: int, chat_type: str):
        chat = SimpleNamespace(id=chat_id, type=chat_type)
        from_user = SimpleNamespace(id=user_id)
        return SimpleNamespace(chat=chat, from_user=from_user, text='')

    chat_id = -100123
    user_id = 555
    today = datetime.utcnow().strftime('%Y-%m-%d')

    # 3 разрешённых вызова
    for n in range(3):
        allowed = await _check_and_increment_limit(make_message(chat_id, user_id, 'group'), limit=3)
        assert allowed, f"Запрос #{n+1} должен быть разрешён"

    # 4-й должен быть запрещён
    allowed4 = await _check_and_increment_limit(make_message(chat_id, user_id, 'group'), limit=3)
    assert not allowed4, '4-й запрос в группе должен быть отклонён'

    # В личке ограничения нет
    dm_allowed = await _check_and_increment_limit(make_message(777, user_id, 'private'), limit=3)
    assert dm_allowed, 'В личке запросы не должны ограничиваться'


def main():
    print('== Тест парсера: дубликаты и мусорные строки ==')
    test_scraper_no_duplicates()
    print('OK')
    print('== Тест лимита запросов в группе ==')
    asyncio.run(test_group_rate_limit())
    print('OK')
    print('Все мини-тесты прошли успешно')


if __name__ == '__main__':
    main()


