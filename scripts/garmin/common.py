"""Общие функции выгрузки Garmin Connect: вход, неделя, форматирование, CSV, кэш."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = REPO_ROOT / "2026-2027" / "garmin"
CACHE_DIR = REPO_ROOT / ".garmin_cache"
TOKENSTORE = Path(os.getenv("GARMINTOKENS", "~/.garminconnect")).expanduser()
LOGIN_HINT = "Запусти в терминале: .venv/bin/python scripts/garmin/garmin_login.py"
DATE_IN = "%d.%m.%Y"
DATE_COLUMN = "Дата"


def week_args(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--week", help="ISO-неделя ГГГГ-НН, например 2026-42. По умолчанию текущая.")
    parser.add_argument("--date", help="Любая дата недели в формате ДД.ММ.ГГГГ.")
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_DIR,
        help="Папка с CSV. По умолчанию 2026-2027/garmin",
    )
    return parser


def monday_sunday(week: str | None, day_text: str | None) -> tuple[date, date]:
    if week:
        try:
            year_s, week_s = week.split("-", 1)
            monday = date.fromisocalendar(int(year_s), int(week_s), 1)
        except ValueError as exc:
            raise SystemExit(f"Некорректная неделя {week!r}, нужен формат ГГГГ-НН") from exc
        return monday, monday + timedelta(days=6)
    if day_text:
        try:
            chosen = datetime.strptime(day_text, DATE_IN).date()
        except ValueError as exc:
            raise SystemExit(f"Некорректная дата {day_text!r}, нужен формат ДД.ММ.ГГГГ") from exc
    else:
        chosen = date.today()
    monday = chosen - timedelta(days=chosen.weekday())
    return monday, monday + timedelta(days=6)


def week_days(monday: date, sunday: date) -> list[date]:
    return [monday + timedelta(days=offset) for offset in range((sunday - monday).days + 1)]


def week_label(monday: date, sunday: date) -> str:
    iso = monday.isocalendar()
    return f"Неделя {iso.year}-{iso.week:02d}: {monday.strftime(DATE_IN)}–{sunday.strftime(DATE_IN)}"


def target_dir(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def connect() -> Garmin:
    if not TOKENSTORE.exists():
        raise SystemExit(f"Нет сохранённых токенов Garmin в {TOKENSTORE}. {LOGIN_HINT}")
    client = Garmin()
    try:
        client.login(str(TOKENSTORE))
    except GarminConnectAuthenticationError as exc:
        raise SystemExit(f"Garmin не принял токены ({exc}). {LOGIN_HINT}") from exc
    except GarminConnectTooManyRequestsError as exc:
        raise SystemExit(f"Garmin ограничил частоту запросов: {exc}. Повтори позже.") from exc
    except GarminConnectConnectionError as exc:
        raise SystemExit(f"Не удалось связаться с Garmin Connect: {exc}") from exc
    return client


def call(name: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Вызов эндпоинта: пустой результат вместо падения, если данных нет."""
    try:
        return func(*args, **kwargs)
    except GarminConnectAuthenticationError as exc:
        raise SystemExit(f"Garmin: ошибка авторизации ({exc}). {LOGIN_HINT}") from exc
    except GarminConnectTooManyRequestsError as exc:
        raise SystemExit(f"Garmin ограничил частоту запросов: {exc}. Повтори позже.") from exc
    except (GarminConnectConnectionError, ValueError, KeyError, TypeError) as exc:
        print(f"{name}: нет данных ({exc})", file=sys.stderr)
        return None


def save_raw(parts: list[str], payload: Any) -> None:
    path = CACHE_DIR.joinpath(*parts[:-1], f"{parts[-1]}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def pick(sources: dict | list[dict], *names: str) -> Any:
    for source in sources if isinstance(sources, list) else [sources]:
        for name in names:
            value = as_dict(source).get(name)
            if value is not None and value != "":
                return value
    return None


def dig(value: Any, *path: str) -> Any:
    for key in path:
        value = as_dict(value).get(key)
    return value


def number(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_num(value: Any, digits: int = 0) -> str:
    num = number(value)
    if num is None:
        return ""
    if digits == 0:
        return str(int(round(num)))
    return f"{num:.{digits}f}".rstrip("0").rstrip(".")


def fmt_hms(seconds: Any) -> str:
    num = number(seconds)
    if num is None:
        return ""
    total = max(0, int(round(num)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def fmt_minutes(seconds: Any) -> str:
    num = number(seconds)
    return "" if num is None else str(int(round(num / 60)))


def kmh(speed_ms: Any) -> float | None:
    num = number(speed_ms)
    return None if num is None or num <= 0 else num * 3.6


def fmt_pace(speed_ms: Any) -> str:
    num = number(speed_ms)
    if num is None or num <= 0:
        return ""
    total = int(round(1000 / num))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def parse_local(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("T", " ")
    for fmt, length in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16)):
        try:
            return datetime.strptime(text[:length], fmt)
        except ValueError:
            continue
    return None


def local_from_millis(value: Any) -> datetime | None:
    """Garmin отдаёт «локальные» метки как миллисекунды эпохи в UTC-представлении."""
    num = number(value)
    if num is None:
        return None
    return datetime.fromtimestamp(num / 1000, tz=UTC).replace(tzinfo=None)


def translate(value: Any, table: dict[str, str], warn: bool = True) -> str:
    if value is None or value == "":
        return ""
    key = str(value)
    if key in table:
        return table[key]
    if warn:
        print(f"Неизвестное значение Garmin: {key}", file=sys.stderr)
    return key


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def row_day(row: dict[str, str]) -> date | None:
    try:
        return datetime.strptime(row.get(DATE_COLUMN, ""), DATE_IN).date()
    except ValueError:
        return None


def merge_week(
    path: Path,
    header: list[str],
    week_rows: list[dict[str, str]],
    monday: date,
    sunday: date,
    order: tuple[str, ...] = (),
) -> None:
    """Заменяет строки выбранной недели, остальные оставляет как есть."""
    kept = [row for row in read_csv(path) if not (row_day(row) and monday <= row_day(row) <= sunday)]
    merged = kept + week_rows
    merged.sort(key=lambda row: (row_day(row) or date.max, *[row.get(name, "") for name in order]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in merged:
            writer.writerow({name: row.get(name, "") for name in header})


def humanize_key(value: Any) -> str:
    return "" if not value else str(value).replace("_", " ").lower()
