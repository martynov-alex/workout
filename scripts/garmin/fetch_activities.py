#!/usr/bin/env python3
"""Выгрузка тренировок Garmin Connect за неделю (пн–вс): активности, круги, силовые подходы."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from common import (
    REPO_ROOT,
    as_dict,
    as_list,
    call,
    connect,
    fmt_hms,
    fmt_num,
    fmt_pace,
    humanize_key,
    kmh,
    merge_week,
    monday_sunday,
    number,
    parse_local,
    pick,
    save_raw,
    target_dir,
    translate,
    week_args,
    week_label,
)

ACTIVITIES_FILE = "activities.csv"
LAPS_FILE = "laps.csv"
SETS_FILE = "strength sets.csv"

ACTIVITY_HEADER = [
    "Id",
    "Название",
    "Тип",
    "Тип события",
    "Дата",
    "Время старта",
    "Время финиша",
    "Длительность",
    "Время в движении",
    "Общее время",
    "Дистанция (км)",
    "Набор (м)",
    "Сброс (м)",
    "Мин. высота (м)",
    "Макс. высота (м)",
    "Средняя скорость (км/ч)",
    "Макс. скорость (км/ч)",
    "Средний темп (мин/км)",
    "Темп с поправкой на уклон (мин/км)",
    "Макс. вертикальная скорость (м/мин)",
    "Средний пульс (уд/мин)",
    "Макс. пульс (уд/мин)",
    "Мин. пульс (уд/мин)",
    "Зона 1",
    "Зона 2",
    "Зона 3",
    "Зона 4",
    "Зона 5",
    "Калории",
    "Аэробный эффект",
    "Анаэробный эффект",
    "Основная польза",
    "Нагрузка (Training Load)",
    "Ударная нагрузка (Impact Load)",
    "Каденс средний (шаг/мин)",
    "Каденс макс (шаг/мин)",
    "Длина шага (см)",
    "Время контакта с землёй (мс)",
    "Вертикальное колебание (см)",
    "Вертикальное соотношение (%)",
    "Мощность средняя (Вт)",
    "Мощность макс (Вт)",
    "Мощность нормализованная (Вт)",
    "Шаги",
    "Body Battery (изменение)",
    "Stamina в начале (%)",
    "Stamina в конце (%)",
    "Stamina мин. (%)",
    "Потеря жидкости (мл)",
    "Выпито (мл)",
    "Температура средняя (°C)",
    "Температура мин. (°C)",
    "Температура макс. (°C)",
    "Дыхание среднее (вдох/мин)",
    "Дыхание макс. (вдох/мин)",
    "Минуты интенсивности умеренные",
    "Минуты интенсивности высокие",
    "RPE (1-10)",
    "Ощущение",
    "VO2max",
    "Подходов",
    "Повторов",
    "Тоннаж (кг)",
    "Кругов",
    "Устройство",
    "Место",
    "Заметки",
]

LAP_HEADER = [
    "Id активности",
    "Дата",
    "Тип активности",
    "Круг",
    "Тип интенсивности",
    "Время старта",
    "Длительность",
    "Время в движении",
    "Дистанция (км)",
    "Набор (м)",
    "Сброс (м)",
    "Средняя скорость (км/ч)",
    "Средний темп (мин/км)",
    "Темп с поправкой на уклон (мин/км)",
    "Средний пульс (уд/мин)",
    "Макс. пульс (уд/мин)",
    "Каденс средний (шаг/мин)",
    "Мощность средняя (Вт)",
    "Калории",
]

SET_HEADER = [
    "Id активности",
    "Дата",
    "Подход",
    "Тип",
    "Время старта",
    "Категория",
    "Упражнение",
    "Повторы",
    "Вес (кг)",
    "Длительность",
]

ACTIVITY_TYPES = {
    "running": "Бег",
    "trail_running": "Трейлраннинг",
    "treadmill_running": "Бег на дорожке",
    "indoor_running": "Бег в помещении",
    "track_running": "Бег на стадионе",
    "street_running": "Бег по городу",
    "ultra_run": "Ультрабег",
    "virtual_run": "Виртуальный бег",
    "obstacle_run": "Бег с препятствиями",
    "walking": "Ходьба",
    "casual_walking": "Прогулка",
    "speed_walking": "Спортивная ходьба",
    "indoor_walking": "Ходьба в помещении",
    "hiking": "Хайкинг",
    "rucking": "Ходьба с рюкзаком",
    "mountaineering": "Альпинизм",
    "cycling": "Велосипед",
    "road_biking": "Шоссейный велосипед",
    "mountain_biking": "Горный велосипед",
    "gravel_cycling": "Гравийный велосипед",
    "indoor_cycling": "Велотренажёр",
    "virtual_ride": "Виртуальный велозаезд",
    "strength_training": "Силовая",
    "hiit": "HIIT",
    "indoor_cardio": "Кардио в зале",
    "cardio_training": "Кардио",
    "fitness_equipment": "Тренажёры",
    "indoor_rowing": "Гребной тренажёр",
    "rowing": "Гребля",
    "elliptical": "Эллипс",
    "stair_climbing": "Степпер / лестница",
    "floor_climbing": "Подъём по этажам",
    "indoor_climbing": "Скалолазание в зале",
    "bouldering": "Боулдеринг",
    "jump_rope": "Скакалка",
    "yoga": "Йога",
    "pilates": "Пилатес",
    "mobility": "Мобилити",
    "breathwork": "Дыхательная практика",
    "stop_watch": "Секундомер",
    "meditation": "Медитация",
    "multi_sport": "Мультиспорт",
    "transition": "Транзит",
    "lap_swimming": "Плавание в бассейне",
    "open_water_swimming": "Плавание на открытой воде",
    "backcountry_skiing": "Ски-тур",
    "resort_skiing": "Горные лыжи",
    "resort_skiing_snowboarding_ws": "Горные лыжи / сноуборд",
    "cross_country_skiing_ws": "Беговые лыжи",
    "skate_skiing_ws": "Лыжи коньком",
    "snow_shoe_ws": "Снегоступы",
    "other": "Другое",
}

EVENT_TYPES = {
    "race": "Соревнование",
    "training": "Тренировка",
    "recreation": "Отдых",
    "fitness": "Фитнес",
    "specialEvent": "Особое событие",
    "touring": "Тур",
    "transportation": "Перемещение",
    "geocaching": "Геокешинг",
    "uncategorized": "",
}

TE_LABELS = {
    "RECOVERY": "Восстановление",
    "AEROBIC_BASE": "Аэробная база",
    "TEMPO": "Темповая",
    "LACTATE_THRESHOLD": "Лактатный порог",
    "THRESHOLD": "Порог",
    "VO2MAX": "МПК (VO2max)",
    "ANAEROBIC_CAPACITY": "Анаэробная ёмкость",
    "SPEED": "Скорость",
    "NO_BENEFIT": "Нет пользы",
    "UNKNOWN": "",
}

INTENSITY_TYPES = {
    "ACTIVE": "Работа",
    "INTERVAL": "Интервал",
    "REST": "Отдых",
    "RECOVERY": "Восстановление",
    "WARMUP": "Разминка",
    "COOLDOWN": "Заминка",
    "OTHER": "Другое",
}

SET_TYPES = {"ACTIVE": "Работа", "REST": "Отдых"}

FEEL = {0: "Очень слабо", 25: "Слабо", 50: "Нормально", 75: "Сильно", 100: "Очень сильно"}

STRENGTH_TYPES = {"strength_training", "hiit", "indoor_cardio", "cardio_training", "fitness_equipment"}


def type_key(item: dict) -> str:
    return str(pick([as_dict(item.get("activityType")), as_dict(item.get("activityTypeDTO"))], "typeKey") or "")


def event_key(item: dict) -> str:
    return str(pick([as_dict(item.get("eventType")), as_dict(item.get("eventTypeDTO"))], "typeKey") or "")


def kg(value: Any) -> float | None:
    """Вес в подходах Garmin хранит в граммах."""
    num = number(value)
    if num is None:
        return None
    return num / 1000 if num > 500 else num


def zone_times(sources: list[dict], zones: Any) -> list[str]:
    times = [fmt_hms(pick(sources, f"hrTimeInZone_{index}")) for index in range(1, 6)]
    if any(times):
        return times
    for zone in as_list(zones):
        index = int(number(as_dict(zone).get("zoneNumber")) or 0)
        if 1 <= index <= 5:
            times[index - 1] = fmt_hms(zone.get("secsInZone"))
    return times


def feel_label(value: Any) -> str:
    num = number(value)
    if num is None:
        return ""
    nearest = min(FEEL, key=lambda mark: abs(mark - num))
    return FEEL[nearest]


def set_totals(sets: list[dict]) -> tuple[int, int, float]:
    active = [item for item in sets if item.get("setType") == "ACTIVE"]
    reps = sum(int(number(item.get("repetitionCount")) or 0) for item in active)
    volume = sum((kg(item.get("weight")) or 0) * (number(item.get("repetitionCount")) or 0) for item in active)
    return len(active), reps, volume


def activity_row(item: dict, summary: dict, zones: Any, sets: list[dict], devices: dict[str, str]) -> dict[str, str]:
    src = [item, summary]
    started = parse_local(pick(src, "startTimeLocal"))
    duration = number(pick(src, "duration"))
    elapsed = number(pick(src, "elapsedDuration"))
    finished = started + timedelta(seconds=elapsed or duration or 0) if started else None
    distance = number(pick(src, "distance"))
    speed = pick(src, "averageSpeed")
    rpe = number(pick(src, "directWorkoutRpe"))
    vertical = number(pick(src, "maxVerticalSpeed"))
    temperature = pick(src, "averageTemperature", "avgTemperature")
    set_count, rep_count, volume = set_totals(sets)
    zones_hms = zone_times(src, zones)
    device_id = str(pick(src, "deviceId") or pick(as_dict(summary.get("metadataDTO")), "deviceId") or "")

    return {
        "Id": str(pick(src, "activityId") or ""),
        "Название": str(pick(src, "activityName") or ""),
        "Тип": translate(type_key(item) or type_key(summary), ACTIVITY_TYPES),
        "Тип события": translate(event_key(item) or event_key(summary), EVENT_TYPES),
        "Дата": started.strftime("%d.%m.%Y") if started else "",
        "Время старта": started.strftime("%H:%M:%S") if started else "",
        "Время финиша": finished.strftime("%H:%M:%S") if finished else "",
        "Длительность": fmt_hms(duration),
        "Время в движении": fmt_hms(pick(src, "movingDuration")),
        "Общее время": fmt_hms(elapsed),
        "Дистанция (км)": fmt_num(distance / 1000, 2) if distance else "",
        "Набор (м)": fmt_num(pick(src, "elevationGain")),
        "Сброс (м)": fmt_num(pick(src, "elevationLoss")),
        "Мин. высота (м)": fmt_num(pick(src, "minElevation")),
        "Макс. высота (м)": fmt_num(pick(src, "maxElevation")),
        "Средняя скорость (км/ч)": fmt_num(kmh(speed), 1) if distance else "",
        "Макс. скорость (км/ч)": fmt_num(kmh(pick(src, "maxSpeed")), 1) if distance else "",
        "Средний темп (мин/км)": fmt_pace(speed) if distance else "",
        "Темп с поправкой на уклон (мин/км)": fmt_pace(pick(src, "avgGradeAdjustedSpeed")),
        "Макс. вертикальная скорость (м/мин)": fmt_num(vertical * 60, 1) if vertical else "",
        "Средний пульс (уд/мин)": fmt_num(pick(src, "averageHR")),
        "Макс. пульс (уд/мин)": fmt_num(pick(src, "maxHR")),
        "Мин. пульс (уд/мин)": fmt_num(pick(src, "minHR")),
        "Зона 1": zones_hms[0],
        "Зона 2": zones_hms[1],
        "Зона 3": zones_hms[2],
        "Зона 4": zones_hms[3],
        "Зона 5": zones_hms[4],
        "Калории": fmt_num(pick(src, "calories")),
        "Аэробный эффект": fmt_num(pick(src, "aerobicTrainingEffect", "trainingEffect"), 1),
        "Анаэробный эффект": fmt_num(pick(src, "anaerobicTrainingEffect"), 1),
        "Основная польза": translate(pick(src, "trainingEffectLabel"), TE_LABELS),
        "Нагрузка (Training Load)": fmt_num(pick(src, "activityTrainingLoad"), 1),
        "Ударная нагрузка (Impact Load)": fmt_num(pick(src, "impactLoad"), 1),
        "Каденс средний (шаг/мин)": fmt_num(
            pick(src, "averageRunningCadenceInStepsPerMinute", "averageRunCadence")
        ),
        "Каденс макс (шаг/мин)": fmt_num(pick(src, "maxRunningCadenceInStepsPerMinute", "maxRunCadence")),
        "Длина шага (см)": fmt_num(pick(src, "avgStrideLength", "strideLength"), 1),
        "Время контакта с землёй (мс)": fmt_num(pick(src, "avgGroundContactTime", "groundContactTime")),
        "Вертикальное колебание (см)": fmt_num(pick(src, "avgVerticalOscillation", "verticalOscillation"), 1),
        "Вертикальное соотношение (%)": fmt_num(pick(src, "avgVerticalRatio", "verticalRatio"), 1),
        "Мощность средняя (Вт)": fmt_num(pick(src, "avgPower", "averagePower")),
        "Мощность макс (Вт)": fmt_num(pick(src, "maxPower")),
        "Мощность нормализованная (Вт)": fmt_num(pick(src, "normPower", "normalizedPower")),
        "Шаги": fmt_num(pick(src, "steps")),
        "Body Battery (изменение)": fmt_num(pick(src, "differenceBodyBattery")),
        "Stamina в начале (%)": fmt_num(pick(src, "beginPotentialStamina")),
        "Stamina в конце (%)": fmt_num(pick(src, "endPotentialStamina")),
        "Stamina мин. (%)": fmt_num(pick(src, "minAvailableStamina")),
        "Потеря жидкости (мл)": fmt_num(pick(src, "waterEstimated")),
        "Выпито (мл)": fmt_num(pick(src, "waterConsumed")),
        "Температура средняя (°C)": fmt_num(temperature, 1),
        "Температура мин. (°C)": fmt_num(pick(src, "minTemperature"), 1),
        "Температура макс. (°C)": fmt_num(pick(src, "maxTemperature"), 1),
        "Дыхание среднее (вдох/мин)": fmt_num(pick(src, "avgRespirationRate"), 1),
        "Дыхание макс. (вдох/мин)": fmt_num(pick(src, "maxRespirationRate"), 1),
        "Минуты интенсивности умеренные": fmt_num(pick(src, "moderateIntensityMinutes")),
        "Минуты интенсивности высокие": fmt_num(pick(src, "vigorousIntensityMinutes")),
        "RPE (1-10)": fmt_num(rpe / 10 if rpe and rpe > 10 else rpe, 1),
        "Ощущение": feel_label(pick(src, "directWorkoutFeel")),
        "VO2max": fmt_num(pick(src, "vO2MaxValue"), 1),
        "Подходов": str(set_count) if set_count else fmt_num(pick(src, "activeSets")),
        "Повторов": str(rep_count) if rep_count else fmt_num(pick(src, "totalReps")),
        "Тоннаж (кг)": fmt_num(volume, 1) if volume else "",
        "Кругов": fmt_num(pick(src, "lapCount")),
        "Устройство": devices.get(device_id, ""),
        "Место": str(pick(src, "locationName") or ""),
        "Заметки": str(pick(src, "description") or "").replace("\r", " ").replace("\n", " "),
    }


def utc_offset(sources: list[dict]) -> timedelta:
    local = parse_local(pick(sources, "startTimeLocal"))
    gmt = parse_local(pick(sources, "startTimeGMT"))
    return local - gmt if local and gmt else timedelta(0)


def lap_rows(activity: dict[str, str], splits: Any, offset: timedelta) -> list[dict[str, str]]:
    rows = []
    for index, lap in enumerate(as_list(as_dict(splits).get("lapDTOs")), start=1):
        lap = as_dict(lap)
        distance = number(lap.get("distance"))
        gmt = parse_local(lap.get("startTimeGMT"))
        started = parse_local(lap.get("startTimeLocal")) or (gmt + offset if gmt else None)
        rows.append(
            {
                "Id активности": activity["Id"],
                "Дата": activity["Дата"],
                "Тип активности": activity["Тип"],
                "Круг": str(int(number(lap.get("lapIndex")) or index)),
                "Тип интенсивности": translate(lap.get("intensityType"), INTENSITY_TYPES),
                "Время старта": started.strftime("%H:%M:%S") if started else "",
                "Длительность": fmt_hms(lap.get("duration")),
                "Время в движении": fmt_hms(lap.get("movingDuration")),
                "Дистанция (км)": fmt_num(distance / 1000, 2) if distance else "",
                "Набор (м)": fmt_num(lap.get("elevationGain")),
                "Сброс (м)": fmt_num(lap.get("elevationLoss")),
                "Средняя скорость (км/ч)": fmt_num(kmh(lap.get("averageSpeed")), 1) if distance else "",
                "Средний темп (мин/км)": fmt_pace(lap.get("averageSpeed")) if distance else "",
                "Темп с поправкой на уклон (мин/км)": fmt_pace(lap.get("avgGradeAdjustedSpeed")),
                "Средний пульс (уд/мин)": fmt_num(lap.get("averageHR")),
                "Макс. пульс (уд/мин)": fmt_num(lap.get("maxHR")),
                "Каденс средний (шаг/мин)": fmt_num(lap.get("averageRunCadence")),
                "Мощность средняя (Вт)": fmt_num(lap.get("averagePower")),
                "Калории": fmt_num(lap.get("calories")),
            }
        )
    return rows


def set_rows(activity: dict[str, str], sets: list[dict]) -> list[dict[str, str]]:
    rows = []
    for index, item in enumerate(sets, start=1):
        exercise = as_dict((as_list(item.get("exercises")) or [{}])[0])
        started = parse_local(item.get("startTime"))
        weight = kg(item.get("weight"))
        rows.append(
            {
                "Id активности": activity["Id"],
                "Дата": activity["Дата"],
                "Подход": str(index),
                "Тип": translate(item.get("setType"), SET_TYPES),
                "Время старта": started.strftime("%H:%M:%S") if started else "",
                "Категория": humanize_key(exercise.get("category")),
                "Упражнение": humanize_key(exercise.get("name")),
                "Повторы": fmt_num(item.get("repetitionCount")),
                "Вес (кг)": fmt_num(weight, 1) if weight else "",
                "Длительность": fmt_hms(item.get("duration")),
            }
        )
    return rows


def device_names(client: Any) -> dict[str, str]:
    names: dict[str, str] = {}
    for device in as_list(call("devices", client.get_devices)):
        device = as_dict(device)
        name = pick(device, "productDisplayName", "displayName", "deviceTypeName")
        if device.get("deviceId") is not None and name:
            names[str(device["deviceId"])] = str(name)
    return names


def expand_multisport(client: Any, item: dict) -> list[tuple[dict, dict]]:
    """Возвращает пары (элемент списка, summaryDTO); мультиспорт раскладывается по дочерним."""
    activity_id = item.get("activityId")
    details = as_dict(call(f"activity {activity_id}", client.get_activity, activity_id))
    save_raw(["activities", str(activity_id), "activity"], details)
    child_ids = as_list(item.get("childIds")) or as_list(as_dict(details.get("metadataDTO")).get("childIds"))
    if not child_ids:
        return [(item, {**as_dict(details.get("summaryDTO")), **_meta(details)})]
    pairs = []
    for child_id in child_ids:
        child = as_dict(call(f"activity {child_id}", client.get_activity, child_id))
        save_raw(["activities", str(child_id), "activity"], child)
        base = {
            "activityId": child.get("activityId", child_id),
            "activityName": child.get("activityName") or item.get("activityName"),
            "activityTypeDTO": child.get("activityTypeDTO"),
            "eventTypeDTO": child.get("eventTypeDTO") or item.get("eventType"),
            "description": child.get("description") or item.get("description"),
            "locationName": child.get("locationName") or item.get("locationName"),
        }
        pairs.append((base, {**as_dict(child.get("summaryDTO")), **_meta(child)}))
    return pairs


def _meta(details: dict) -> dict:
    meta = as_dict(details.get("metadataDTO"))
    device = as_dict(meta.get("deviceMetaDataDTO"))
    return {
        "activityId": details.get("activityId"),
        "activityName": details.get("activityName"),
        "activityTypeDTO": details.get("activityTypeDTO"),
        "eventTypeDTO": details.get("eventTypeDTO"),
        "description": details.get("description"),
        "locationName": details.get("locationName"),
        "lapCount": meta.get("lapCount"),
        "deviceId": device.get("deviceId"),
    }


def main() -> None:
    args = week_args("Выгрузить тренировки Garmin за неделю (понедельник–воскресенье).").parse_args()
    monday, sunday = monday_sunday(args.week, args.date)
    folder = target_dir(args.dir)
    client = connect()
    devices = device_names(client)

    listed = as_list(
        call("activities", client.get_activities_by_date, monday.isoformat(), sunday.isoformat(), None, "asc")
    )
    save_raw(["weeks", f"{monday.isoformat()}_activities"], listed)

    activities: list[dict[str, str]] = []
    laps: list[dict[str, str]] = []
    sets_out: list[dict[str, str]] = []
    for item in listed:
        for base, summary in expand_multisport(client, as_dict(item)):
            activity_id = base.get("activityId") or summary.get("activityId")
            key = type_key(base) or type_key(summary)
            zones = None
            if not pick([base, summary], "hrTimeInZone_1"):
                zones = call(f"hr zones {activity_id}", client.get_activity_hr_in_timezones, activity_id)
                save_raw(["activities", str(activity_id), "hr_zones"], zones)
            sets: list[dict] = []
            if key in STRENGTH_TYPES or pick([base, summary], "totalSets", "activeSets"):
                payload = call(f"exercise sets {activity_id}", client.get_activity_exercise_sets, activity_id)
                save_raw(["activities", str(activity_id), "exercise_sets"], payload)
                sets = [as_dict(entry) for entry in as_list(as_dict(payload).get("exerciseSets"))]
            splits = call(f"splits {activity_id}", client.get_activity_splits, activity_id)
            save_raw(["activities", str(activity_id), "splits"], splits)

            row = activity_row(base, summary, zones, sets, devices)
            if not row["Дата"]:
                continue
            activities.append(row)
            laps.extend(lap_rows(row, splits, utc_offset([base, summary])))
            sets_out.extend(set_rows(row, sets))

    merge_week(folder / ACTIVITIES_FILE, ACTIVITY_HEADER, activities, monday, sunday, ("Время старта",))
    merge_week(folder / LAPS_FILE, LAP_HEADER, laps, monday, sunday, ("Id активности",))
    merge_week(folder / SETS_FILE, SET_HEADER, sets_out, monday, sunday, ("Id активности",))

    print(week_label(monday, sunday))
    print(f"Тренировок: {len(activities)}, кругов: {len(laps)}, подходов: {len(sets_out)}")
    print(f"Записано в {folder.relative_to(REPO_ROOT) if folder.is_relative_to(REPO_ROOT) else folder}/")
    if not activities:
        print("Пусто. Проверь, что часы синхронизированы с Garmin Connect за эту неделю.")
        return
    for row in sorted(activities, key=lambda r: (r["Дата"][6:] + r["Дата"][3:5] + r["Дата"][:2], r["Время старта"])):
        print(
            f"{row['Дата']} {row['Время старта']}  {row['Тип']}  {row['Длительность']}  "
            f"{row['Дистанция (км)'] + ' км' if row['Дистанция (км)'] else '—'}  "
            f"D+ {row['Набор (м)'] or '—'}  ЧСС {row['Средний пульс (уд/мин)'] or '—'}  "
            f"TE {row['Аэробный эффект'] or '—'}/{row['Анаэробный эффект'] or '—'}  "
            f"нагрузка {row['Нагрузка (Training Load)'] or '—'}"
        )


if __name__ == "__main__":
    main()
