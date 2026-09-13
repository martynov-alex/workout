#!/usr/bin/env python3
"""Выгрузка сводок тренировок Polar AccessLink v4 за календарную неделю (пн–вс)."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = REPO_ROOT / "2026-2027" / "training log" / "training log.csv"
TOKEN_FILE = REPO_ROOT / ".polar_token"
API_SESSIONS = "https://www.polaraccesslink.com/v4/data/training-sessions/list"
API_SPORTS = "https://www.polaraccesslink.com/v4/data/sports/list"
API_TOKEN = "https://auth.polar.com/oauth/token"
FEATURES = ("statistics", "zones", "training-load-report")
DATE_IN = "%d.%m.%Y"

HEADER = [
    "Id",
    "Название",
    "Вид спорта",
    "Дата",
    "Время старта",
    "Время финиша",
    "Длительность",
    "Дистанция (км)",
    "Набор (м)",
    "Сброс (м)",
    "Средняя скорость (км/ч)",
    "Макс. скорость (км/ч)",
    "Средний темп (мин/км)",
    "Макс. темп (мин/км)",
    "Средний пульс (уд/мин)",
    "Макс. пульс (уд/мин)",
    "Калории",
    "Жиры (%)",
    "Углеводы (%)",
    "Белки (%)",
    "Каденс средний",
    "Каденс макс",
    "Длина шага (см)",
    "Мощность средняя (Вт)",
    "Мощность макс (Вт)",
    "Running index",
    "Training load",
    "Training benefit",
    "Cardio load",
    "Muscle load",
    "Perceived load",
    "Интерпретация cardio load",
    "Интерпретация muscle load",
    "Интерпретация perceived load",
    "RPE",
    "Восстановление",
    "Зона 1",
    "Зона 2",
    "Зона 3",
    "Зона 4",
    "Зона 5",
    "Устройство",
    "Заметки",
    "Самочувствие",
    "Рост (см)",
    "Вес (кг)",
    "ЧССmax",
    "ЧССпокоя",
    "VO2max",
]

DATE_INDEX = HEADER.index("Дата")
START_INDEX = HEADER.index("Время старта")

LOAD_RU = {
    "LOAD_INTERPRETATION_VERY_LOW": "Очень низкая",
    "LOAD_INTERPRETATION_LOW": "Низкая",
    "LOAD_INTERPRETATION_MEDIUM": "Средняя",
    "LOAD_INTERPRETATION_HIGH": "Высокая",
    "LOAD_INTERPRETATION_VERY_HIGH": "Очень высокая",
    "VERY_LOW": "Очень низкая",
    "LOW": "Низкая",
    "MEDIUM": "Средняя",
    "HIGH": "Высокая",
    "VERY_HIGH": "Очень высокая",
    "NOT_AVAILABLE": "Недоступно",
    "LOAD_INTERPRETATION_NOT_AVAILABLE": "Недоступно",
    "UNKNOWN": "",
}

RPE_RU = {
    "RPE_NONE": "Нет",
    "RPE_EASY": "Легко",
    "RPE_LIGHT": "Слабая",
    "RPE_FAIRLY_BRISK": "Довольно бодрая",
    "RPE_BRISK": "Бодрая",
    "RPE_MODERATE": "Умеренная",
    "RPE_FAIRLY_HARD": "Довольно тяжёлая",
    "RPE_HARD": "Тяжёлая",
    "RPE_EXHAUSTING": "Изнуряющая",
    "RPE_EXTREME": "Экстремальная",
    "UNKNOWN": "",
}

BENEFIT_RU = {
    "TRAINING_BENEFIT_UNSPECIFIED": "",
    "TRAINING_BENEFIT_NONE": "",
    "TRAINING_BENEFIT_RECOVERY_TRAINING": "Восстановительная",
    "TRAINING_BENEFIT_BASIC_TRAINING": "Базовая",
    "TRAINING_BENEFIT_BASIC_TRAINING_LONG": "Базовая длительная",
    "TRAINING_BENEFIT_BASIC_AND_STEADY_STATE_TRAINING": "Базовая и равномерная",
    "TRAINING_BENEFIT_BASIC_AND_STEADY_STATE_TRAINING_LONG": "Базовая и равномерная длительная",
    "TRAINING_BENEFIT_STEADY_STATE_TRAINING": "Равномерная",
    "TRAINING_BENEFIT_STEADY_STATE_AND_BASIC_TRAINING": "Равномерная и базовая",
    "TRAINING_BENEFIT_STEADY_STATE_AND_BASIC_TRAINING_LONG": "Равномерная и базовая длительная",
    "TRAINING_BENEFIT_STEADY_STATE_TRAINING_PLUS": "Равномерная+",
    "TRAINING_BENEFIT_STEADY_STATE_AND_TEMPO_TRAINING": "Равномерная и темповая",
    "TRAINING_BENEFIT_TEMPO_AND_STEADY_STATE_TRAINING": "Темповая и равномерная",
    "TRAINING_BENEFIT_TEMPO_TRAINING": "Темповая",
    "TRAINING_BENEFIT_TEMPO_TRAINING_PLUS": "Темповая+",
    "TRAINING_BENEFIT_TEMPO_AND_MAXIMUM_TRAINING": "Темповая и максимальная",
    "TRAINING_BENEFIT_MAXIMUM_TRAINING": "Максимальная",
    "TRAINING_BENEFIT_MAXIMUM_AND_TEMPO_TRAINING": "Максимальная и темповая",
    "TRAINING_BENEFIT_MAXIMUM_TRAINING_PLUS": "Максимальная+",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Выгрузить сводки тренировок Polar v4 за неделю (понедельник–воскресенье)."
    )
    parser.add_argument("--week", help="ISO-неделя ГГГГ-НН, например 2026-37. По умолчанию текущая.")
    parser.add_argument("--date", help="Любая дата недели в формате ДД.ММ.ГГГГ.")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_CSV,
        help="CSV для записи. По умолчанию 2026-2027/training log/training log.csv",
    )
    return parser.parse_args()


def load_secrets() -> dict[str, str]:
    values: dict[str, str] = {}
    if TOKEN_FILE.exists():
        for raw in TOKEN_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def save_secrets(values: dict[str, str]) -> None:
    lines = [f"{key}={values[key]}" for key in values if values[key]]
    TOKEN_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


class PolarV4:
    def __init__(self, secrets: dict[str, str]) -> None:
        self.secrets = secrets
        self.token = secrets.get("POLAR_V4_ACCESS_TOKEN") or ""
        if not self.token:
            raise SystemExit(
                "Нет POLAR_V4_ACCESS_TOKEN в .polar_token. "
                "Получи токен через Bruno: bruno/get polar v4 token.bru"
            )

    def refresh(self) -> None:
        refresh = self.secrets.get("POLAR_V4_REFRESH_TOKEN")
        client_id = self.secrets.get("POLAR_CLIENT_ID")
        client_secret = self.secrets.get("POLAR_CLIENT_SECRET")
        if not (refresh and client_id and client_secret):
            raise SystemExit(
                "Access token v4 истёк. Обнови через Bruno refresh polar v4 token.bru "
                "или добавь в .polar_token POLAR_V4_REFRESH_TOKEN, POLAR_CLIENT_ID, POLAR_CLIENT_SECRET."
            )
        body = urllib.parse.urlencode(
            {"grant_type": "refresh_token", "refresh_token": refresh}
        ).encode()
        request = urllib.request.Request(
            API_TOKEN,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        credentials = f"{client_id}:{client_secret}".encode()
        request.add_header("Authorization", "Basic " + base64.b64encode(credentials).decode())
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.token = payload["access_token"]
        self.secrets["POLAR_V4_ACCESS_TOKEN"] = self.token
        if payload.get("refresh_token"):
            self.secrets["POLAR_V4_REFRESH_TOKEN"] = payload["refresh_token"]
        save_secrets(self.secrets)
        print("Обновлён Polar v4 access token.", file=sys.stderr)

    def get(self, url: str, retry: bool = True) -> object:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "Authorization": f"Bearer {self.token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status == 204:
                    return {}
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 401 and retry:
                self.refresh()
                return self.get(url, retry=False)
            raise SystemExit(f"Polar v4 API {exc.code} {exc.reason}. {detail}".strip()) from exc
        except urllib.error.URLError as exc:
            raise SystemExit(f"Не удалось связаться с Polar API: {exc.reason}") from exc


def pick(item: dict, *names: str) -> object:
    for name in names:
        if name in item and item[name] is not None:
            return item[name]
    return None


def as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def object_id(value: object) -> str:
    if isinstance(value, dict):
        found = pick(value, "id")
        return str(found) if found is not None else ""
    return str(value) if value is not None else ""


def parse_dt(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "")
    for fmt, length in (
        ("%Y-%m-%dT%H:%M:%S.%f", 26),
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S", 19),
    ):
        try:
            return datetime.strptime(text[:length], fmt)
        except ValueError:
            continue
    return None


def format_hms(seconds: float | None) -> str:
    if seconds is None:
        return ""
    total = max(0, int(round(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_pace(kmh: float | None) -> str:
    if kmh is None or kmh <= 0:
        return ""
    total = int(round(3600 / kmh))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def format_number(value: object, digits: int | None = None) -> str:
    if value is None or value == "":
        return ""
    number = float(value)
    if digits is None:
        return str(int(round(number))) if abs(number - round(number)) < 1e-9 else str(number)
    formatted = f"{number:.{digits}f}"
    return formatted.rstrip("0").rstrip(".") if digits > 0 else formatted


def translate(value: object, table: dict[str, str]) -> str:
    if value is None or value == "":
        return ""
    key = str(value)
    if key in table:
        return table[key]
    print(f"Неизвестное значение Polar: {key}", file=sys.stderr)
    return key


def millis_to_hms(value: object) -> str:
    if value is None or value == "":
        return ""
    return format_hms(float(value) / 1000)


def stats_map(exercise: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in as_list(as_dict(exercise.get("statistics")).get("statistics")):
        if isinstance(item, dict) and item.get("type"):
            result[str(item["type"])] = item
    return result


def stat_value(stats: dict[str, dict], key: str, field: str) -> float | None:
    item = stats.get(key)
    if not item:
        return None
    value = item.get(field)
    return float(value) if value is not None else None


def speed_kmh(raw: float | None, distance_km: float | None, duration_s: float | None) -> float | None:
    computed = None
    if distance_km and duration_s and duration_s > 0:
        computed = distance_km / (duration_s / 3600)
    if raw is None:
        return computed
    if computed is not None and raw < 8 and abs(raw * 3.6 - computed) < abs(raw - computed):
        return raw * 3.6
    return raw


def stride_cm(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 10 if value > 250 else value


def hr_zones(exercise: dict) -> list[str]:
    times = [""] * 5
    for group in as_list(exercise.get("zones")):
        if not isinstance(group, dict) or group.get("type") != "ZONE_TYPE_HEART_RATE":
            continue
        for index, zone in enumerate(as_list(group.get("zones"))[:5]):
            if isinstance(zone, dict):
                times[index] = millis_to_hms(zone.get("inZone"))
    return times


def sport_names(client: PolarV4) -> dict[str, str]:
    names: dict[str, str] = {}
    try:
        payload = client.get(API_SPORTS)
    except SystemExit as exc:
        print(f"Каталог спорта недоступен: {exc}", file=sys.stderr)
        return names
    sports = payload if isinstance(payload, list) else as_list(as_dict(payload).get("sports"))
    for sport in sports:
        if not isinstance(sport, dict):
            continue
        sid = object_id(sport.get("id"))
        localized = as_dict(sport.get("localizedNames"))
        ru = as_dict(localized.get("ru")).get("longName")
        en = as_dict(localized.get("en")).get("longName")
        names[sid] = str(ru or en or sport.get("name") or sid)
    return names


def fetch_day(client: PolarV4, day: date) -> list[dict]:
    start = datetime.combine(day, datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%S")
    end = datetime.combine(day + timedelta(days=1), datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%S")
    query = urllib.parse.urlencode(
        [
            ("from", start),
            ("to", end),
            *[("features", feature) for feature in FEATURES],
        ]
    )
    payload = client.get(f"{API_SESSIONS}?{query}")
    sessions = as_list(as_dict(payload).get("trainingSessions"))
    return [item for item in sessions if isinstance(item, dict)]


def row_from_exercise(session: dict, exercise: dict, sports: dict[str, str]) -> list[str] | None:
    started = parse_dt(pick(exercise, "startTime") or pick(session, "startTime"))
    stopped = parse_dt(pick(exercise, "stopTime") or pick(session, "stopTime"))
    if started is None:
        return None

    duration_ms = pick(exercise, "durationMillis") or pick(session, "durationMillis")
    duration_s = float(duration_ms) / 1000 if duration_ms not in (None, "") else None
    distance_m = pick(exercise, "distanceMeters") or pick(session, "distanceMeters")
    distance_km = float(distance_m) / 1000 if distance_m not in (None, "") else None

    stats = stats_map(exercise)
    avg_speed = speed_kmh(stat_value(stats, "STATISTICS_TYPE_SPEED", "avg"), distance_km, duration_s)
    max_speed = speed_kmh(stat_value(stats, "STATISTICS_TYPE_SPEED", "max"), distance_km, duration_s)
    avg_hr = pick(session, "hrAvg") or stat_value(stats, "STATISTICS_TYPE_HEART_RATE", "avg")
    max_hr = pick(session, "hrMax") or stat_value(stats, "STATISTICS_TYPE_HEART_RATE", "max")
    report = as_dict(exercise.get("trainingLoadReport"))
    physical = as_dict(session.get("physicalInformation"))
    product = as_dict(session.get("product"))
    sport_id = object_id(as_dict(exercise.get("sport")).get("id") or as_dict(session.get("sport")).get("id"))
    zones = hr_zones(exercise)
    exercise_id = object_id(exercise.get("identifier")) or object_id(session.get("identifier"))

    return [
        exercise_id,
        str(pick(session, "name") or ""),
        sports.get(sport_id, sport_id),
        started.strftime(DATE_IN),
        started.strftime("%H:%M:%S"),
        stopped.strftime("%H:%M:%S") if stopped else "",
        format_hms(duration_s),
        format_number(distance_km, 2),
        format_number(pick(exercise, "ascentMeters"), 0),
        format_number(pick(exercise, "descentMeters"), 0),
        format_number(avg_speed, 1),
        format_number(max_speed, 1),
        format_pace(avg_speed),
        format_pace(max_speed),
        format_number(avg_hr),
        format_number(max_hr),
        format_number(pick(exercise, "calories") or pick(session, "calories")),
        format_number(pick(exercise, "fatPercentage") or pick(session, "fatPercentage")),
        format_number(pick(exercise, "carboPercentage") or pick(session, "carboPercentage")),
        format_number(pick(exercise, "proteinPercentage") or pick(session, "proteinPercentage")),
        format_number(stat_value(stats, "STATISTICS_TYPE_CADENCE", "avg")),
        format_number(stat_value(stats, "STATISTICS_TYPE_CADENCE", "max")),
        format_number(stride_cm(stat_value(stats, "STATISTICS_TYPE_STRIDE_LENGTH", "avg"))),
        format_number(stat_value(stats, "STATISTICS_TYPE_POWER", "avg")),
        format_number(stat_value(stats, "STATISTICS_TYPE_POWER", "max")),
        format_number(pick(exercise, "runningIndex")),
        format_number(pick(exercise, "trainingLoad") or pick(session, "trainingLoad")),
        translate(pick(session, "trainingBenefit"), BENEFIT_RU),
        format_number(pick(report, "cardioLoad"), 1),
        format_number(pick(report, "muscleLoad"), 1),
        format_number(pick(report, "perceivedLoad"), 1),
        translate(pick(report, "cardioLoadInterpretation"), LOAD_RU),
        translate(pick(report, "muscleLoadInterpretation"), LOAD_RU),
        translate(pick(report, "perceivedLoadInterpretation"), LOAD_RU),
        translate(pick(report, "sessionRpe"), RPE_RU),
        millis_to_hms(pick(exercise, "recoveryTimeMillis") or pick(session, "recoveryTimeMillis")),
        zones[0],
        zones[1],
        zones[2],
        zones[3],
        zones[4],
        str(pick(product, "modelName") or ""),
        str(pick(session, "note") or ""),
        format_number(pick(session, "feeling"), 2),
        format_number(pick(physical, "heightCm"), 1),
        format_number(pick(physical, "weightKg"), 1),
        format_number(pick(physical, "maximumHeartRate")),
        format_number(pick(physical, "restingHeartRate")),
        format_number(pick(physical, "vo2Max")),
    ]


def rows_from_session(session: dict, sports: dict[str, str]) -> list[list[str]]:
    exercises = [item for item in as_list(session.get("exercises")) if isinstance(item, dict)]
    if not exercises:
        row = row_from_exercise(session, session, sports)
        return [row] if row else []
    rows = []
    for exercise in exercises:
        row = row_from_exercise(session, exercise, sports)
        if row:
            rows.append(row)
    return rows


def in_week(row: list[str], monday: date, sunday: date) -> bool:
    try:
        day = datetime.strptime(row[DATE_INDEX], DATE_IN).date()
    except (IndexError, ValueError):
        return False
    return monday <= day <= sunday


def read_csv(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if rows and rows[0] and rows[0][0] in {"Id", "Name"}:
        return rows[1:]
    return rows


def merge_week(existing: list[list[str]], week_rows: list[list[str]], monday: date, sunday: date) -> list[list[str]]:
    kept = [row for row in existing if row and not in_week(row, monday, sunday)]
    merged = kept + week_rows
    merged.sort(
        key=lambda row: (
            datetime.strptime(row[DATE_INDEX], DATE_IN).date()
            if len(row) > DATE_INDEX and row[DATE_INDEX]
            else date.max,
            row[START_INDEX] if len(row) > START_INDEX else "",
        )
    )
    return merged


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)


def print_week(rows: list[list[str]]) -> None:
    for row in rows:
        print(
            f"{row[3]} {row[4]}  {row[2]}  {row[6]}  "
            f"{row[7] + ' км' if row[7] else '—'}  "
            f"D+ {row[8] or '—'}  ЧСС {row[14] or '—'}"
        )


def main() -> None:
    args = parse_args()
    monday, sunday = monday_sunday(args.week, args.date)
    client = PolarV4(load_secrets())
    sports = sport_names(client)

    week_rows: list[list[str]] = []
    day = monday
    while day <= sunday:
        for session in fetch_day(client, day):
            week_rows.extend(rows_from_session(session, sports))
        day += timedelta(days=1)
    week_rows.sort(key=lambda row: (row[DATE_INDEX], row[START_INDEX]))

    target = args.file if args.file.is_absolute() else REPO_ROOT / args.file
    write_csv(target, merge_week(read_csv(target), week_rows, monday, sunday))

    iso = monday.isocalendar()
    print(f"Неделя {iso.year}-{iso.week:02d}: {monday.strftime(DATE_IN)}–{sunday.strftime(DATE_IN)}")
    print(f"Тренировок: {len(week_rows)}")
    print(f"Записано в {target.relative_to(REPO_ROOT)}")
    if not week_rows:
        print("Пусто. Проверь POLAR_V4_ACCESS_TOKEN и что в Flow есть тренировки за эту неделю.")
        return
    print_week(week_rows)


if __name__ == "__main__":
    main()
