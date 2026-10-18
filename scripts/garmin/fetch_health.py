#!/usr/bin/env python3
"""Выгрузка здоровья, восстановления и статуса тренированности Garmin Connect за неделю (пн–вс)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from common import (
    REPO_ROOT,
    as_dict,
    as_list,
    call,
    connect,
    dig,
    fmt_hms,
    fmt_minutes,
    fmt_num,
    fmt_pace,
    humanize_key,
    local_from_millis,
    merge_week,
    monday_sunday,
    number,
    pick,
    save_raw,
    target_dir,
    translate,
    week_args,
    week_days,
    week_label,
)

HEALTH_FILE = "daily health.csv"
STATUS_FILE = "training status.csv"

HEALTH_HEADER = [
    "Дата",
    "Отбой",
    "Подъём",
    "Сон всего",
    "Глубокий сон",
    "Лёгкий сон",
    "REM-сон",
    "Бодрствование",
    "Оценка сна",
    "Качество сна",
    "Потребность во сне",
    "Пульс во сне (уд/мин)",
    "Дыхание во сне (вдох/мин)",
    "SpO2 во сне средний (%)",
    "SpO2 во сне мин. (%)",
    "Стресс во сне",
    "Пробуждений",
    "Беспокойные моменты",
    "Body Battery за ночь",
    "Дневной сон",
    "HRV ночь (мс)",
    "HRV макс. 5 мин (мс)",
    "HRV 7 дней (мс)",
    "HRV база низ (мс)",
    "HRV база верх (мс)",
    "Статус HRV",
    "Пульс покоя (уд/мин)",
    "Пульс мин. (уд/мин)",
    "Пульс макс. (уд/мин)",
    "Пульс покоя 7 дней (уд/мин)",
    "Body Battery при пробуждении",
    "Body Battery макс.",
    "Body Battery мин.",
    "Body Battery заряд",
    "Body Battery расход",
    "Стресс средний",
    "Стресс макс.",
    "Стресс: отдых (мин)",
    "Стресс: низкий (мин)",
    "Стресс: средний (мин)",
    "Стресс: высокий (мин)",
    "Шаги",
    "Дистанция за день (км)",
    "Этажи вверх",
    "Этажи вниз",
    "Калории активные",
    "Калории всего",
    "Калории BMR",
    "Минуты интенсивности умеренные",
    "Минуты интенсивности высокие",
    "Дыхание днём среднее (вдох/мин)",
    "Дыхание мин. (вдох/мин)",
    "Дыхание макс. (вдох/мин)",
    "SpO2 средний (%)",
    "SpO2 мин. (%)",
    "Выпито (мл)",
    "Потеря с потом (мл)",
    "Вес (кг)",
    "Жир (%)",
    "Мышечная масса (кг)",
]

STATUS_HEADER = [
    "Дата",
    "Готовность (0-100)",
    "Уровень готовности",
    "Отзыв готовности",
    "Фактор: сон (%)",
    "Фактор: восстановление (%)",
    "Фактор: острая нагрузка (%)",
    "Фактор: HRV (%)",
    "Фактор: история стресса (%)",
    "Фактор: история сна (%)",
    "Время восстановления утром (ч)",
    "Время восстановления на конец дня (ч)",
    "Статус тренированности",
    "Отзыв статуса",
    "Острая нагрузка (7 дней)",
    "Хроническая нагрузка (28 дней)",
    "Оптимум хронической мин.",
    "Оптимум хронической макс.",
    "Соотношение острой/хронической (ACWR)",
    "Статус ACWR",
    "Фокус: анаэробная",
    "Фокус: анаэробная цель мин.",
    "Фокус: анаэробная цель макс.",
    "Фокус: высокая аэробная",
    "Фокус: высокая аэробная цель мин.",
    "Фокус: высокая аэробная цель макс.",
    "Фокус: низкая аэробная",
    "Фокус: низкая аэробная цель мин.",
    "Фокус: низкая аэробная цель макс.",
    "Отзыв по фокусу нагрузки",
    "VO2max бег",
    "VO2max вело",
    "Фитнес-возраст",
    "Акклиматизация к жаре (%)",
    "Акклиматизация к высоте (м)",
    "Endurance Score",
    "Endurance Score класс",
    "Hill Score",
    "Hill Score сила",
    "Hill Score выносливость",
    "Прогноз 5 км",
    "Прогноз 10 км",
    "Прогноз 21,1 км",
    "Прогноз 42,2 км",
    "Лактатный порог пульс (уд/мин)",
    "Лактатный порог темп (мин/км)",
]

HRV_STATUS = {
    "BALANCED": "Сбалансирован",
    "UNBALANCED": "Несбалансирован",
    "LOW": "Низкий",
    "POOR": "Плохой",
    "NONE": "Нет статуса",
    "NO_STATUS": "Нет статуса",
}

SLEEP_QUALITY = {
    "EXCELLENT": "Отлично",
    "GOOD": "Хорошо",
    "FAIR": "Удовлетворительно",
    "POOR": "Плохо",
}

READINESS_LEVEL = {
    "PRIME": "Отличная",
    "HIGH": "Высокая",
    "MODERATE": "Средняя",
    "LOW": "Низкая",
    "POOR": "Плохая",
    "NONE": "",
}

TRAINING_STATUS = {
    "PEAKING": "Пик формы",
    "PRODUCTIVE": "Эффективность",
    "MAINTAINING": "Поддержание",
    "RECOVERY": "Восстановление",
    "UNPRODUCTIVE": "Непродуктивность",
    "DETRAINING": "Детренированность",
    "OVERREACHING": "Перетренированность",
    "STRAINED": "Перенапряжение",
    "PAUSED": "Пауза",
    "NO_STATUS": "Нет статуса",
}

ACWR_STATUS = {
    "LOW": "Низкое",
    "OPTIMAL": "Оптимальное",
    "HIGH": "Высокое",
    "VERY_HIGH": "Очень высокое",
    "NONE": "",
}


def primary_entry(mapping: Any) -> dict:
    """Garmin группирует статус по устройствам; берём основное устройство."""
    entries = [as_dict(value) for value in as_dict(mapping).values() if isinstance(value, dict)]
    for entry in entries:
        if entry.get("primaryTrainingDevice"):
            return entry
    return entries[0] if entries else {}


def readiness_snapshots(snapshots: Any) -> list[dict]:
    items = [as_dict(item) for item in as_list(snapshots)] or ([as_dict(snapshots)] if snapshots else [])
    return sorted(items, key=lambda item: str(item.get("timestamp") or ""))


def morning_readiness(snapshots: list[dict]) -> dict:
    for item in snapshots:
        if item.get("inputContext") == "AFTER_WAKEUP_RESET":
            return item
    return snapshots[0] if snapshots else {}


def status_key(phrase: Any) -> str:
    return re.sub(r"_\d+$", "", str(phrase or ""))


def time_of(value: Any) -> str:
    moment = local_from_millis(value)
    return moment.strftime("%H:%M") if moment else ""


def kg(grams: Any) -> str:
    num = number(grams)
    if num is None:
        return ""
    return fmt_num(num / 1000 if num > 500 else num, 1)


def weights_by_day(payload: Any) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in as_list(as_dict(payload).get("dateWeightList")):
        item = as_dict(item)
        day = str(item.get("calendarDate") or "")
        if day:
            result[day] = item
    return result


def predictions_by_day(payload: Any) -> dict[str, dict]:
    items = as_list(payload) or as_list(as_dict(payload).get("racePredictions"))
    return {str(item.get("calendarDate")): item for item in map(as_dict, items) if item.get("calendarDate")}


def series_points(payload: Any) -> list[tuple[str, float]]:
    """Точки ряда биометрии: (дата, значение) из любых вложенных списков."""
    points: list[tuple[str, float]] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            day = node.get("calendarDate") or node.get("from") or node.get("date")
            value = number(node.get("value"))
            if day and value is not None:
                points.append((str(day)[:10], value))
            for child in node.values():
                if isinstance(child, (list, dict)):
                    walk(child)

    walk(payload)
    return sorted(points)


def latest_on(points: list[tuple[str, float]], day: date) -> float | None:
    found = None
    for point_day, value in points:
        if point_day <= day.isoformat():
            found = value
    return found


def lt_pace(speed: float | None) -> str:
    if speed is None:
        return ""
    return fmt_pace(speed * 10 if speed < 1 else speed)


def health_row(day: date, stats: dict, sleep: dict, hrv: dict, hydration: dict, weight: dict) -> dict[str, str]:
    dto = as_dict(sleep.get("dailySleepDTO"))
    summary = as_dict(hrv.get("hrvSummary"))
    baseline = as_dict(summary.get("baseline"))
    need = number(dig(dto, "sleepNeed", "actual"))
    return {
        "Дата": day.strftime("%d.%m.%Y"),
        "Отбой": time_of(dto.get("sleepStartTimestampLocal")),
        "Подъём": time_of(dto.get("sleepEndTimestampLocal")),
        "Сон всего": fmt_hms(dto.get("sleepTimeSeconds")),
        "Глубокий сон": fmt_hms(dto.get("deepSleepSeconds")),
        "Лёгкий сон": fmt_hms(dto.get("lightSleepSeconds")),
        "REM-сон": fmt_hms(dto.get("remSleepSeconds")),
        "Бодрствование": fmt_hms(dto.get("awakeSleepSeconds")),
        "Оценка сна": fmt_num(dig(dto, "sleepScores", "overall", "value")),
        "Качество сна": translate(dig(dto, "sleepScores", "overall", "qualifierKey"), SLEEP_QUALITY),
        "Потребность во сне": fmt_hms(need * 60) if need else "",
        "Пульс во сне (уд/мин)": fmt_num(pick(dto, "avgHeartRate")),
        "Дыхание во сне (вдох/мин)": fmt_num(pick(dto, "averageRespirationValue"), 1),
        "SpO2 во сне средний (%)": fmt_num(pick(dto, "averageSpO2Value", "avgSpO2"), 1),
        "SpO2 во сне мин. (%)": fmt_num(pick(dto, "lowestSpO2Value")),
        "Стресс во сне": fmt_num(pick(dto, "avgSleepStress"), 1),
        "Пробуждений": fmt_num(pick(dto, "awakeCount")),
        "Беспокойные моменты": fmt_num(sleep.get("restlessMomentsCount")),
        "Body Battery за ночь": fmt_num(pick([sleep, stats], "bodyBatteryChange", "bodyBatteryDuringSleep")),
        "Дневной сон": fmt_hms(dto.get("napTimeSeconds")) if number(dto.get("napTimeSeconds")) else "",
        "HRV ночь (мс)": fmt_num(pick([summary, sleep], "lastNightAvg", "avgOvernightHrv")),
        "HRV макс. 5 мин (мс)": fmt_num(summary.get("lastNight5MinHigh")),
        "HRV 7 дней (мс)": fmt_num(summary.get("weeklyAvg")),
        "HRV база низ (мс)": fmt_num(baseline.get("balancedLow")),
        "HRV база верх (мс)": fmt_num(baseline.get("balancedUpper")),
        "Статус HRV": translate(pick([summary, sleep], "status", "hrvStatus"), HRV_STATUS),
        "Пульс покоя (уд/мин)": fmt_num(pick(stats, "restingHeartRate")),
        "Пульс мин. (уд/мин)": fmt_num(pick(stats, "minHeartRate")),
        "Пульс макс. (уд/мин)": fmt_num(pick(stats, "maxHeartRate")),
        "Пульс покоя 7 дней (уд/мин)": fmt_num(pick(stats, "lastSevenDaysAvgRestingHeartRate")),
        "Body Battery при пробуждении": fmt_num(pick(stats, "bodyBatteryAtWakeTime")),
        "Body Battery макс.": fmt_num(pick(stats, "bodyBatteryHighestValue")),
        "Body Battery мин.": fmt_num(pick(stats, "bodyBatteryLowestValue")),
        "Body Battery заряд": fmt_num(pick(stats, "bodyBatteryChargedValue")),
        "Body Battery расход": fmt_num(pick(stats, "bodyBatteryDrainedValue")),
        "Стресс средний": fmt_num(pick(stats, "averageStressLevel")),
        "Стресс макс.": fmt_num(pick(stats, "maxStressLevel")),
        "Стресс: отдых (мин)": fmt_minutes(pick(stats, "restStressDuration")),
        "Стресс: низкий (мин)": fmt_minutes(pick(stats, "lowStressDuration")),
        "Стресс: средний (мин)": fmt_minutes(pick(stats, "mediumStressDuration")),
        "Стресс: высокий (мин)": fmt_minutes(pick(stats, "highStressDuration")),
        "Шаги": fmt_num(pick(stats, "totalSteps")),
        "Дистанция за день (км)": fmt_num((number(pick(stats, "totalDistanceMeters")) or 0) / 1000, 2)
        if pick(stats, "totalDistanceMeters")
        else "",
        "Этажи вверх": fmt_num(pick(stats, "floorsAscended")),
        "Этажи вниз": fmt_num(pick(stats, "floorsDescended")),
        "Калории активные": fmt_num(pick(stats, "activeKilocalories")),
        "Калории всего": fmt_num(pick(stats, "totalKilocalories")),
        "Калории BMR": fmt_num(pick(stats, "bmrKilocalories")),
        "Минуты интенсивности умеренные": fmt_num(pick(stats, "moderateIntensityMinutes")),
        "Минуты интенсивности высокие": fmt_num(pick(stats, "vigorousIntensityMinutes")),
        "Дыхание днём среднее (вдох/мин)": fmt_num(pick(stats, "avgWakingRespirationValue"), 1),
        "Дыхание мин. (вдох/мин)": fmt_num(pick(stats, "lowestRespirationValue"), 1),
        "Дыхание макс. (вдох/мин)": fmt_num(pick(stats, "highestRespirationValue"), 1),
        "SpO2 средний (%)": fmt_num(pick(stats, "averageSpo2"), 1),
        "SpO2 мин. (%)": fmt_num(pick(stats, "lowestSpo2")),
        "Выпито (мл)": fmt_num(pick(hydration, "valueInML")),
        "Потеря с потом (мл)": fmt_num(pick(hydration, "sweatLossInML")),
        "Вес (кг)": kg(weight.get("weight")),
        "Жир (%)": fmt_num(weight.get("bodyFat"), 1),
        "Мышечная масса (кг)": kg(weight.get("muscleMass")),
    }


def hours(minutes: Any) -> str:
    num = number(minutes)
    return fmt_num(num / 60, 1) if num is not None else ""


def factor(readiness: dict, name: str) -> str:
    """Пока Garmin калибрует готовность (score = null), факторы приходят нулями — не пишем их."""
    return fmt_num(readiness.get(name)) if readiness.get("score") is not None else ""


def status_row(
    day: date,
    readiness: dict,
    evening: dict,
    status: dict,
    fitness_age: dict,
    endurance: dict,
    hill: dict,
    prediction: dict,
    lt_hr: float | None,
    lt_speed: float | None,
    acclimation: dict,
) -> dict[str, str]:
    training = primary_entry(dig(status, "mostRecentTrainingStatus", "latestTrainingStatusData"))
    acute = as_dict(training.get("acuteTrainingLoadDTO"))
    balance = primary_entry(dig(status, "mostRecentTrainingLoadBalance", "metricsTrainingLoadBalanceDTOMap"))
    vo2 = as_dict(status.get("mostRecentVO2Max"))
    heat = as_dict(vo2.get("heatAltitudeAcclimation")) or acclimation
    phrase = training.get("trainingStatusFeedbackPhrase")
    feedback = readiness.get("feedbackShort")
    return {
        "Дата": day.strftime("%d.%m.%Y"),
        "Готовность (0-100)": fmt_num(readiness.get("score")),
        "Уровень готовности": translate(readiness.get("level"), READINESS_LEVEL),
        "Отзыв готовности": "" if feedback in (None, "UNKNOWN", "NONE") else humanize_key(feedback),
        "Фактор: сон (%)": factor(readiness, "sleepScoreFactorPercent"),
        "Фактор: восстановление (%)": factor(readiness, "recoveryTimeFactorPercent"),
        "Фактор: острая нагрузка (%)": factor(readiness, "acwrFactorPercent"),
        "Фактор: HRV (%)": factor(readiness, "hrvFactorPercent"),
        "Фактор: история стресса (%)": factor(readiness, "stressHistoryFactorPercent"),
        "Фактор: история сна (%)": factor(readiness, "sleepHistoryFactorPercent"),
        "Время восстановления утром (ч)": hours(readiness.get("recoveryTime")),
        "Время восстановления на конец дня (ч)": hours(evening.get("recoveryTime")),
        "Статус тренированности": translate(status_key(phrase), TRAINING_STATUS) if phrase else "",
        "Отзыв статуса": humanize_key(phrase),
        "Острая нагрузка (7 дней)": fmt_num(acute.get("dailyTrainingLoadAcute")),
        "Хроническая нагрузка (28 дней)": fmt_num(acute.get("dailyTrainingLoadChronic")),
        "Оптимум хронической мин.": fmt_num(acute.get("minTrainingLoadChronic")),
        "Оптимум хронической макс.": fmt_num(acute.get("maxTrainingLoadChronic")),
        "Соотношение острой/хронической (ACWR)": fmt_num(acute.get("dailyAcuteChronicWorkloadRatio"), 2),
        "Статус ACWR": translate(acute.get("acwrStatus"), ACWR_STATUS),
        "Фокус: анаэробная": fmt_num(balance.get("monthlyLoadAnaerobic")),
        "Фокус: анаэробная цель мин.": fmt_num(balance.get("monthlyLoadAnaerobicTargetMin")),
        "Фокус: анаэробная цель макс.": fmt_num(balance.get("monthlyLoadAnaerobicTargetMax")),
        "Фокус: высокая аэробная": fmt_num(balance.get("monthlyLoadAerobicHigh")),
        "Фокус: высокая аэробная цель мин.": fmt_num(balance.get("monthlyLoadAerobicHighTargetMin")),
        "Фокус: высокая аэробная цель макс.": fmt_num(balance.get("monthlyLoadAerobicHighTargetMax")),
        "Фокус: низкая аэробная": fmt_num(balance.get("monthlyLoadAerobicLow")),
        "Фокус: низкая аэробная цель мин.": fmt_num(balance.get("monthlyLoadAerobicLowTargetMin")),
        "Фокус: низкая аэробная цель макс.": fmt_num(balance.get("monthlyLoadAerobicLowTargetMax")),
        "Отзыв по фокусу нагрузки": humanize_key(balance.get("trainingBalanceFeedbackPhrase")),
        "VO2max бег": fmt_num(pick(as_dict(vo2.get("generic")), "vo2MaxPreciseValue", "vo2MaxValue"), 1),
        "VO2max вело": fmt_num(pick(as_dict(vo2.get("cycling")), "vo2MaxPreciseValue", "vo2MaxValue"), 1),
        "Фитнес-возраст": fmt_num(pick([fitness_age, as_dict(vo2.get("generic"))], "fitnessAge"), 1),
        "Акклиматизация к жаре (%)": fmt_num(pick(heat, "heatAcclimationPercentage")),
        "Акклиматизация к высоте (м)": fmt_num(pick(heat, "altitudeAcclimation")),
        "Endurance Score": fmt_num(endurance.get("overallScore")),
        "Endurance Score класс": fmt_num(endurance.get("classification")),
        "Hill Score": fmt_num(hill.get("overallScore")),
        "Hill Score сила": fmt_num(hill.get("strengthScore")),
        "Hill Score выносливость": fmt_num(hill.get("enduranceScore")),
        "Прогноз 5 км": fmt_hms(prediction.get("time5K")),
        "Прогноз 10 км": fmt_hms(prediction.get("time10K")),
        "Прогноз 21,1 км": fmt_hms(prediction.get("timeHalfMarathon")),
        "Прогноз 42,2 км": fmt_hms(prediction.get("timeMarathon")),
        "Лактатный порог пульс (уд/мин)": fmt_num(lt_hr),
        "Лактатный порог темп (мин/км)": lt_pace(lt_speed),
    }


def main() -> None:
    args = week_args("Выгрузить здоровье, восстановление и статус Garmin за неделю (понедельник–воскресенье).")
    parsed = args.parse_args()
    monday, sunday = monday_sunday(parsed.week, parsed.date)
    folder = target_dir(parsed.dir)
    days = [day for day in week_days(monday, sunday) if day <= date.today()]
    client = connect()

    start, end = monday.isoformat(), min(sunday, date.today()).isoformat()
    weights = call("body composition", client.get_body_composition, start, end)
    predictions = call("race predictions", client.get_race_predictions, start, end, "daily")
    lactate = call("lactate threshold", client.get_lactate_threshold, latest=False, start_date=start, end_date=end)
    save_raw(["weeks", f"{start}_body_composition"], weights)
    save_raw(["weeks", f"{start}_race_predictions"], predictions)
    save_raw(["weeks", f"{start}_lactate_threshold"], lactate)
    weight_map = weights_by_day(weights)
    prediction_map = predictions_by_day(predictions)
    lt_hr_points = series_points(as_dict(lactate).get("heart_rate"))
    lt_speed_points = series_points(as_dict(lactate).get("speed"))

    health_rows: list[dict[str, str]] = []
    status_rows: list[dict[str, str]] = []
    for day in days:
        iso = day.isoformat()
        raw = {
            "stats": call(f"stats {iso}", client.get_stats, iso),
            "sleep": call(f"sleep {iso}", client.get_sleep_data, iso),
            "hrv": call(f"hrv {iso}", client.get_hrv_data, iso),
            "hydration": call(f"hydration {iso}", client.get_hydration_data, iso),
            "readiness": call(f"training readiness {iso}", client.get_training_readiness, iso),
            "training_status": call(f"training status {iso}", client.get_training_status, iso),
            "fitness_age": call(f"fitness age {iso}", client.get_fitnessage_data, iso),
            "endurance": call(f"endurance score {iso}", client.get_endurance_score, iso),
            "hill": call(f"hill score {iso}", client.get_hill_score, iso),
        }
        if not dig(raw["training_status"], "mostRecentVO2Max", "heatAltitudeAcclimation"):
            raw["acclimation"] = call(f"acclimation {iso}", client.get_heat_altitude_acclimation, iso)
        for name, payload in raw.items():
            save_raw(["days", iso, name], payload)

        health_rows.append(
            health_row(
                day,
                as_dict(raw["stats"]),
                as_dict(raw["sleep"]),
                as_dict(raw["hrv"]),
                as_dict(raw["hydration"]),
                weight_map.get(iso, {}),
            )
        )
        snapshots = readiness_snapshots(raw["readiness"])
        status_rows.append(
            status_row(
                day,
                morning_readiness(snapshots),
                snapshots[-1] if snapshots else {},
                as_dict(raw["training_status"]),
                as_dict(raw["fitness_age"]),
                as_dict(raw["endurance"]),
                as_dict(raw["hill"]),
                prediction_map.get(iso, {}),
                latest_on(lt_hr_points, day),
                latest_on(lt_speed_points, day),
                as_dict(raw.get("acclimation")),
            )
        )

    merge_week(folder / HEALTH_FILE, HEALTH_HEADER, health_rows, monday, sunday)
    merge_week(folder / STATUS_FILE, STATUS_HEADER, status_rows, monday, sunday)

    print(week_label(monday, sunday))
    print(f"Дней: {len(health_rows)}")
    print(f"Записано в {folder.relative_to(REPO_ROOT) if folder.is_relative_to(REPO_ROOT) else folder}/")
    for health, status in zip(health_rows, status_rows):
        print(
            f"{health['Дата']}  сон {health['Сон всего'] or '—'} ({health['Оценка сна'] or '—'})  "
            f"HRV {health['HRV ночь (мс)'] or '—'} {health['Статус HRV']}  "
            f"ЧССпокоя {health['Пульс покоя (уд/мин)'] or '—'}  "
            f"BB {health['Body Battery при пробуждении'] or '—'}  "
            f"готовность {status['Готовность (0-100)'] or '—'}  "
            f"нагрузка {status['Острая нагрузка (7 дней)'] or '—'}/{status['Хроническая нагрузка (28 дней)'] or '—'}  "
            f"{status['Статус тренированности']}"
        )


if __name__ == "__main__":
    main()
