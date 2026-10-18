#!/usr/bin/env python3
"""Выгрузка Cardio Load из Polar AccessLink за календарную неделю (пн–вс)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = REPO_ROOT / "2026-2027" / "cardio load" / "cardio load.csv"
TOKEN_FILE = REPO_ROOT / ".polar_token"
API_RANGE = "https://www.polaraccesslink.com/v3/users/cardio-load/date"
API_REGISTER = "https://www.polaraccesslink.com/v3/users"

HEADER = [
    "День",
    "Статус кардионагрузки",
    "Показатель кардионагрузки",
    "Кардионагрузка (TRIMP — Training Impulse)",
    "Напряжение",
    "Выносливость",
]

STATUS_RU = {
    "LOAD_STATUS_NOT_AVAILABLE": "Недоступно",
    "DETRAINING": "Детренированность",
    "MAINTAINING": "Поддержание",
    "PRODUCTIVE": "Эффективность",
    "OVERREACHING": "Перетренированность",
    "RECOVERY_AFTER_OVERREACHING": "Восстановление после перетренированности",
    "PRODUCTIVE_DROPPED_FROM_OVERREACHING": "Эффективность после перетренированности",
    "PRODUCTIVE_ALMOST_OVERREACHING": "Эффективность, почти перетренированность",
    "UNRECOGNIZED": "Не распознан",
}

DATE_IN = "%d.%m.%Y"
DATE_API = "%Y-%m-%d"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Выгрузить Cardio Load Polar за неделю (понедельник–воскресенье)."
    )
    parser.add_argument(
        "--week",
        help="ISO-неделя ГГГГ-НН, например 2026-37. По умолчанию текущая.",
    )
    parser.add_argument(
        "--date",
        help="Любая дата недели в формате ДД.ММ.ГГГГ. Игнорируется, если задан --week.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_CSV,
        help="CSV для записи. По умолчанию 2026-2027/cardio load/cardio load.csv",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Один раз зарегистрировать пользователя в AccessLink и выйти.",
    )
    return parser.parse_args()


def load_token() -> str:
    token = ""
    if TOKEN_FILE.exists():
        for raw in TOKEN_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("POLAR_ACCESS_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not token:
        raise SystemExit(
            f"Нет POLAR_ACCESS_TOKEN в {TOKEN_FILE}. "
            "Положи туда строку POLAR_ACCESS_TOKEN=..."
        )
    return token


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


def api_request(token: str, url: str, data: bytes | None = None, method: str | None = None) -> object:
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            if not body:
                return {}
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        hint = ""
        if exc.code == 403:
            hint = " Нужна регистрация: python3 scripts/fetch_cardio_load.py --register"
        raise SystemExit(f"Polar API {exc.code} {exc.reason}.{hint} {detail}".strip()) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Не удалось связаться с Polar API: {exc.reason}") from exc


def register_user(token: str) -> None:
    payload = json.dumps({"member-id": "workout-local"}).encode("utf-8")
    try:
        api_request(token, API_REGISTER, data=payload, method="POST")
    except SystemExit as exc:
        if "409" in str(exc):
            print("Пользователь уже зарегистрирован в AccessLink.")
            return
        raise
    print("Пользователь зарегистрирован в AccessLink.")


def fetch_week(token: str, monday: date, sunday: date) -> list[dict]:
    query = urllib.parse.urlencode(
        {"from": monday.strftime(DATE_API), "to": sunday.strftime(DATE_API)}
    )
    payload = api_request(token, f"{API_RANGE}?{query}")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "cardio_loads", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise SystemExit(f"Неожиданный ответ Polar API: {type(payload).__name__}")


def format_ratio(value: object) -> str:
    if value is None or value == "":
        return ""
    return f"{float(value):.1f}"


def format_int(value: object) -> str:
    if value is None or value == "":
        return ""
    return str(int(round(float(value))))


def translate_status(value: object) -> str:
    if value is None or value == "":
        return ""
    key = str(value)
    if key in STATUS_RU:
        return STATUS_RU[key]
    print(f"Неизвестный статус Polar: {key}", file=sys.stderr)
    return key


def parse_api_date(value: object) -> date:
    text = str(value)
    try:
        return datetime.strptime(text[:10], DATE_API).date()
    except ValueError as exc:
        raise SystemExit(f"Polar вернул странную дату: {value!r}") from exc


def row_from_item(item: dict) -> list[str]:
    day = parse_api_date(item.get("date"))
    return [
        day.strftime(DATE_IN),
        translate_status(item.get("cardio_load_status")),
        format_ratio(item.get("cardio_load_ratio")),
        format_int(item.get("cardio_load")),
        format_int(item.get("strain")),
        format_int(item.get("tolerance")),
    ]


def read_csv(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if rows and rows[0] == HEADER:
        return rows[1:]
    if rows and rows[0] and rows[0][0] == HEADER[0]:
        return rows[1:]
    return rows


def parse_row_date(row: list[str]) -> date | None:
    if not row or not row[0].strip():
        return None
    try:
        return datetime.strptime(row[0].strip(), DATE_IN).date()
    except ValueError:
        return None


def merge_week(existing: list[list[str]], week_rows: list[list[str]]) -> list[list[str]]:
    by_date: dict[date, list[str]] = {}
    leftovers: list[list[str]] = []
    for row in existing:
        day = parse_row_date(row)
        if day is None:
            if any(cell.strip() for cell in row):
                leftovers.append(row)
            continue
        by_date[day] = row
    for row in week_rows:
        day = parse_row_date(row)
        if day is not None:
            by_date[day] = row
    merged = [by_date[day] for day in sorted(by_date)]
    return leftovers + merged


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)


def print_week(rows: list[list[str]]) -> None:
    for row in rows:
        print(",".join(row))


def main() -> None:
    args = parse_args()
    token = load_token()
    if args.register:
        register_user(token)
        return

    monday, sunday = monday_sunday(args.week, args.date)
    items = fetch_week(token, monday, sunday)
    week_rows = [row_from_item(item) for item in items]
    week_rows.sort(key=lambda row: parse_row_date(row) or date.max)

    target = args.file if args.file.is_absolute() else REPO_ROOT / args.file
    existing = read_csv(target)
    write_csv(target, merge_week(existing, week_rows))

    iso = monday.isocalendar()
    print(f"Неделя {iso.year}-{iso.week:02d}: {monday.strftime(DATE_IN)}–{sunday.strftime(DATE_IN)}")
    print(f"Записано в {target.relative_to(REPO_ROOT)}")
    print_week(week_rows)


if __name__ == "__main__":
    main()
