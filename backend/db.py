# backend/db.py
from sqlmodel import SQLModel, Field, create_engine, Session, select
from datetime import datetime
from typing import Optional, List
import json, os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/schedule.db")
engine = create_engine(DATABASE_URL, echo=False)

class ScheduleVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    group_code: str
    week_start: str                   # ISO monday (yyyy-mm-dd)
    hash: str                         # хэш нормализованных пар
    payload: str                      # JSON нормализованных данных
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserDailyUsage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int
    user_id: int
    date_ymd: str  # YYYY-MM-DD
    count: int = Field(default=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

def init_db():
    SQLModel.metadata.create_all(engine)

def save_version(group_code: str, week_start: str, hash_: str, data: List[dict]):
    with Session(engine) as s:
        ver = ScheduleVersion(group_code=group_code, week_start=week_start,
                              hash=hash_, payload=json.dumps(data, ensure_ascii=False))
        s.add(ver); s.commit(); s.refresh(ver)
        return ver

def last_version(group_code: str, week_start: str) -> Optional[ScheduleVersion]:
    with Session(engine) as s:
        stmt = select(ScheduleVersion).where(
            (ScheduleVersion.group_code == group_code) &
            (ScheduleVersion.week_start == week_start)
        ).order_by(ScheduleVersion.created_at.desc())
        return s.exec(stmt).first()

def list_versions(group_code: str, limit:int=10):
    with Session(engine) as s:
        stmt = select(ScheduleVersion).where(ScheduleVersion.group_code==group_code)\
            .order_by(ScheduleVersion.created_at.desc()).limit(limit)
        return list(s.exec(stmt))

# ===== Rate Limit helpers =====
def get_user_daily_count(chat_id: int, user_id: int, date_ymd: str) -> int:
    with Session(engine) as s:
        stmt = select(UserDailyUsage).where(
            (UserDailyUsage.chat_id == chat_id) &
            (UserDailyUsage.user_id == user_id) &
            (UserDailyUsage.date_ymd == date_ymd)
        )
        rec = s.exec(stmt).first()
        return rec.count if rec else 0

def increment_user_daily_count(chat_id: int, user_id: int, date_ymd: str) -> int:
    with Session(engine) as s:
        stmt = select(UserDailyUsage).where(
            (UserDailyUsage.chat_id == chat_id) &
            (UserDailyUsage.user_id == user_id) &
            (UserDailyUsage.date_ymd == date_ymd)
        )
        rec = s.exec(stmt).first()
        if rec:
            rec.count += 1
            rec.updated_at = datetime.utcnow()
        else:
            rec = UserDailyUsage(chat_id=chat_id, user_id=user_id, date_ymd=date_ymd, count=1)
            s.add(rec)
        s.commit(); s.refresh(rec)
        return rec.count
