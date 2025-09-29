# backend/scraper.py
import os, re, hashlib
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta

GROUP_PAGE_URL = os.getenv("GROUP_PAGE_URL", "https://biik.ru/rasp/cg389.htm")

def get_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())

def fetch_html(url: str) -> str:
    # Иногда сайт отдаёт cp1251 — requests сам определит, но подстрахуемся
    r = requests.get(url, timeout=20, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "windows-1251"
    return r.text

def normalize_schedule(html: str) -> list[dict]:
    """
    Возвращаем структурированное расписание:
    [{day: 'Пн', pair: 1, time: '08:30-10:00', subject: '...', kind: 'Лек', room:'122', teacher:'...'}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")

    # Шаблон страниц «Экспресс-расписание» обычно таблицы/списки по дням.
    # Берём все строки, где есть номер пары/время, предмет, аудитория и препод.
    # Ниже — эвристичный парсер, который хорошо работает с табличной вёрсткой.
    data = []
    current_date = None
    current_weekday = None
    current_week = None
    
    # Ищем все таблицы
    tables = soup.find_all("table")
    
    for tbl in tables:
        # Ищем все строки в таблице
        rows = tbl.find_all("tr")
        
        for tr in rows:
            tds = [td.get_text(" ", strip=True) for td in tr.find_all(["td","th"])]
            
            # Проверяем первую ячейку на наличие даты
            if tds and len(tds) > 0:
                first_cell = tds[0].strip()
                date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})\s*([А-Яа-я]+)-(\d+)', first_cell)
                if date_match:
                    current_date = date_match.group(1)
                    current_weekday = date_match.group(2)
                    current_week = date_match.group(3)
                    
                                        # Проверяем, есть ли в этой же строке первая пара
                    # Если в строке 3 ячейки: дата, номер пары, предмет
                    if len(tds) == 3:
                        pair_cell = tds[1]  # Номер пары
                        subject_cell = tds[2]  # Предмет
                        
                        # Ищем номер пары
                        m_pair = re.search(r'\b([1-7])\b', pair_cell)
                        if m_pair and m_pair.group(1) == "1":
                            # Это первая пара! Проверяем, что предмет не пустой
                            if not subject_cell.strip() or subject_cell.strip() == '\xa0' or len(subject_cell.strip()) < 3:
                                continue  # Пропускаем пустые пары
                            
                            # Это первая пара! Обрабатываем её
                            pair_num = 1
                            time_start, time_end = "08:30", "10:00"
                            
                            # Ищем предмет, аудиторию и тип
                            m_kind = re.search(r'\((Лек|Пр|Лаб|Сем|Зач|Практич\.?)\)', subject_cell, re.I)
                            m_room = re.search(r'\b([А-ЯA-Z]?-?\d{2,4}[A-Za-zА-Я]?)\b', subject_cell)
                            m_teacher = re.search(r'([А-Я][а-я]+ [А-Я]\.[А-Я]\.)', subject_cell)
                            if not m_teacher:
                                # Альтернативный поиск преподавателя - более гибкий
                                m_teacher = re.search(r'([А-Я][а-я]+ [А-Я]\.[А-Я]\.)', subject_cell)
                            if not m_teacher:
                                # Еще более гибкий поиск - ищем любые инициалы
                                m_teacher = re.search(r'([А-Я][а-я]+ [А-Я]\.[А-Я]\.)', subject_cell)
                            
                            # Очищаем название предмета
                            clean_subject = subject_cell
                            if m_room:
                                clean_subject = clean_subject.replace(m_room.group(1), '').strip()
                            if m_teacher:
                                clean_subject = clean_subject.replace(m_teacher.group(1), '').strip()
                            clean_subject = re.sub(r'\s+', ' ', clean_subject).strip()
                            
                            # Извлекаем тип занятия
                            kind_val = "Практика"  # По умолчанию
                            if m_kind:
                                kind_raw = m_kind.group(1)
                                if kind_raw == "Лек":
                                    kind_val = "Лекция"
                                elif kind_raw == "Лаб":
                                    kind_val = "Лабораторная"
                                elif kind_raw == "Практич" or kind_raw == "Пр":
                                    kind_val = "Практика"
                                elif kind_raw == "Сем":
                                    kind_val = "Семинар"
                                elif kind_raw == "Зач":
                                    kind_val = "Зачет"
                                else:
                                    kind_val = kind_raw
                            
                            # Извлекаем аудиторию
                            room_val = ""
                            if m_room:
                                room_raw = m_room.group(1)
                                if room_raw.isdigit() and int(room_raw) in [4, 10, 12]:
                                    room_val = ""
                                else:
                                    room_val = room_raw
                            
                            # Извлекаем преподавателя
                            teacher_val = ""
                            if m_teacher:
                                teacher_val = m_teacher.group(1)
                            
                            # Добавляем первую пару
                            subject_with_date = f"{current_date} {current_weekday}-{current_week} | {clean_subject}"
                            data.append({
                                "pair": pair_num,
                                "time": f"{time_start}-{time_end}",
                                "subject": subject_with_date,
                                "room": room_val,
                                "kind": kind_val,
                                "teacher": teacher_val,
                                "raw": tds
                            })
                    
                    continue  # Пропускаем строку с датой
            
            # Ищем строки с парами
            if len(tds) >= 2:  # Может быть 2 ячейки из-за rowspan в первой ячейке
                # Если 2 ячейки: первая - номер пары, вторая - предмет
                # Если 3 ячейки: первая - дата (rowspan), вторая - номер пары, третья - предмет
                if len(tds) == 2:
                    pair_cell = tds[0]  # Номер пары
                    subject_cell = tds[1]  # Предмет
                elif len(tds) == 3:
                    pair_cell = tds[1]  # Номер пары (пропускаем дату)
                    subject_cell = tds[2]  # Предмет
                else:
                    continue  # Пропускаем неподходящие строки
                
                # Проверяем, есть ли дата
                if not current_date:
                    continue  # Пропускаем, если нет даты
                
                # Явно фильтруем мусорные строки, которые содержат лишь одиночные цифры (напр. ['8',''])
                if subject_cell.strip() == '' and re.fullmatch(r'\d+', pair_cell.strip() or ''):
                    continue

                # Время не указано в HTML, будем определять по номеру пары
                # Ищем номер пары в ячейке (просто цифра 1, 2, 3, 4, 5, 6, 7)
                m_pair = re.search(r'\b([1-7])\b', pair_cell)
                
                # Ищем предмет, аудиторию и тип в ячейке предмета
                # Формат: "ТСВПС (Практич.) 314 Извеков Я.О."
                m_kind = re.search(r'\((Лек|Пр|Лаб|Сем|Зач|Практич\.?)\)', subject_cell, re.I)
                
                # Ищем аудиторию (число или текст типа "ЦМИТ", "сз2")
                m_room = re.search(r'\b([А-ЯA-Z]?-?\d{2,4}[A-Za-zА-Я]?)\b', subject_cell)
                
                # Ищем преподавателя (после аудитории) - учитываем HTML-ссылки
                m_teacher = re.search(r'([А-Я][а-я]+ [А-Я]\.[А-Я]\.)', subject_cell)
                if not m_teacher:
                    # Альтернативный поиск преподавателя - более гибкий
                    m_teacher = re.search(r'([А-Я][а-я]+ [А-Я]\.[А-Я]\.)', subject_cell)
                if not m_teacher:
                    # Еще более гибкий поиск - ищем любые инициалы
                    m_teacher = re.search(r'([А-Я][а-я]+ [А-Я]\.[А-Я]\.)', subject_cell)
                
                # Если есть номер пары и дата - это строка с парой
                if not (m_pair and current_date):
                    continue

                # Проверяем, что предмет не пустой (не только пробелы и не &nbsp;)
                if not subject_cell.strip() or subject_cell.strip() == '\xa0' or len(subject_cell.strip()) < 3:
                    continue  # Пропускаем пустые пары

                # Определяем номер пары
                pair_num = int(m_pair.group(1))
                
                # Определяем время по номеру пары
                time_start = ""
                time_end = ""
                if pair_num == 1:
                    time_start, time_end = "08:30", "10:00"
                elif pair_num == 2:
                    time_start, time_end = "10:10", "11:40"
                elif pair_num == 3:
                    time_start, time_end = "12:20", "13:50"
                elif pair_num == 4:
                    time_start, time_end = "14:10", "15:40"
                elif pair_num == 5:
                    time_start, time_end = "15:50", "17:20"
                elif pair_num == 6:
                    time_start, time_end = "17:30", "19:00"
                elif pair_num == 7:
                    time_start, time_end = "19:10", "20:40"
                
                # Очищаем название предмета от лишнего
                clean_subject = subject_cell
                
                # Убираем аудиторию и преподавателя, оставляем только название предмета и тип
                if m_room:
                    clean_subject = clean_subject.replace(m_room.group(1), '').strip()
                if m_teacher:
                    clean_subject = clean_subject.replace(m_teacher.group(1), '').strip()
                
                # Убираем лишние пробелы
                clean_subject = re.sub(r'\s+', ' ', clean_subject).strip()
                
                # Извлекаем тип занятия
                kind_val = ""
                if m_kind:
                    kind_raw = m_kind.group(1)
                    if kind_raw == "Лек":
                        kind_val = "Лекция"
                    elif kind_raw == "Лаб":
                        kind_val = "Лабораторная"
                    elif kind_raw == "Практич" or kind_raw == "Пр":
                        kind_val = "Практика"
                    elif kind_raw == "Сем":
                        kind_val = "Семинар"
                    elif kind_raw == "Зач":
                        kind_val = "Зачет"
                    else:
                        kind_val = kind_raw
                else:
                    kind_val = "Практика"  # По умолчанию
                
                # Извлекаем аудиторию
                room_val = ""
                if m_room:
                    room_raw = m_room.group(1)
                    # Фильтруем проблемные номера аудиторий
                    if room_raw.isdigit() and int(room_raw) in [4, 10, 12]:
                        room_val = ""
                    else:
                        room_val = room_raw
                
                # Извлекаем преподавателя
                teacher_val = ""
                if m_teacher:
                    teacher_val = m_teacher.group(1)
                
                # Добавляем дату в начало названия предмета для группировки по дням
                subject_with_date = f"{current_date} {current_weekday}-{current_week} | {clean_subject}"
                
                data.append({
                    "pair": pair_num,
                    "time": f"{time_start}-{time_end}",
                    "subject": subject_with_date,
                    "room": room_val,
                    "kind": kind_val,
                    "teacher": teacher_val,
                    "raw": tds
                })

    # если таблицы не нашли, пробуем списки:
    if not data:
        for li in soup.find_all("li"):
            txt = li.get_text(" ", strip=True)
            m_time = re.search(r'\b(\d{1,2}[:.]\d{2})\s*[-–]\s*(\d{1,2}[:.]\d{2})\b', txt)
            if m_time:
                data.append({
                    "pair": None,
                    "time": f"{m_time.group(1)}-{m_time.group(2)}".replace('.',':'),
                    "subject": txt,
                    "room": "",
                    "kind": "",
                    "raw": [txt]
                })
    
    # Финальная очистка и дедупликация
    cleaned = []
    seen = set()
    for item in data:
        # Пропускаем мусорные элементы без предмета/времени или с подозрительным raw
        if not item.get("subject") or not item.get("time"):
            continue
        raw_val = item.get("raw")
        if isinstance(raw_val, list) and len(raw_val) == 2 and raw_val[0].isdigit() and raw_val[1] == "":
            # Это как раз случай ["8", ""] из логов
            continue
        key = (
            item.get("subject"),
            item.get("pair"),
            item.get("time"),
            item.get("room"),
            item.get("kind"),
            item.get("teacher"),
        )
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)

    return cleaned

def schedule_hash(items: list[dict]) -> str:
    # Хэшируем только существенные поля
    # Важно хэшировать уже очищенный и дедуплицированный список
    norm = [(i.get("pair"), i.get("time"), i.get("subject"), i.get("room"), i.get("kind")) for i in items]
    blob = repr(norm).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()

def scrape_group(url: str = GROUP_PAGE_URL) -> tuple[list[dict], str]:
    html = fetch_html(url)
    items = normalize_schedule(html)
    return items, schedule_hash(items)
