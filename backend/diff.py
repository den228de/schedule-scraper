# backend/diff.py
from datetime import date
from db import last_version, save_version
from scraper import scrape_group, get_monday
from typing import Optional

def check_and_store(group_code: str, url: str) -> Optional[dict]:
    items, h = scrape_group(url)
    week = get_monday(date.today()).isoformat()
    prev = last_version(group_code, week)
    if not prev or prev.hash != h:
        ver = save_version(group_code, week, h, items)
        diff = {"changed": True, "count": len(items), "week": week}
        return diff
    return None
