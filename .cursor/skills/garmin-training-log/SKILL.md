---
name: garmin-training-log
description: >-
  Downloads Garmin Connect activities for a Monday–Sunday week and merges them
  into 2026-2027/garmin/activities.csv, laps.csv and strength sets.csv. Use when
  the user asks to update the training log, выгрузить тренировки, синхронизировать
  Garmin, загрузить журнал тренировок, заполнить training log или activities.
---

# Garmin Training Log

Выгрузка тренировок из Garmin Connect через неофициальную библиотеку `garminconnect` (в `.venv`). Сеть разрешена. Не писать HTTP руками — запускать готовый скрипт. Посекундные ряды и GPS-треки не запрашивать.

## Workflow

1. Неделя `ГГГГ-НН` (как папки планов) или любая дата `ДД.ММ.ГГГГ`. Иначе текущая пн–вс.
2. Запустить из корня репозитория **с полным доступом к сети** (`required_permissions: ["all"]` — домены Garmin не в allowlist песочницы):

```bash
.venv/bin/python scripts/garmin/fetch_activities.py --week 2026-42
.venv/bin/python scripts/garmin/fetch_activities.py --date 15.10.2026
```

3. После успеха кратко: неделя, число тренировок, таблица дата / тип / длительность / км / набор / ЧСС / аэробный и анаэробный эффект / нагрузка. Для силовых — подходы, повторы, тоннаж.

## Авторизация

- Токены: `~/.garminconnect/garmin_tokens.json` (вне репозитория), обновляются автоматически.
- Если скрипт пишет «Нет сохранённых токенов» или «ошибка авторизации» — попросить пользователя самого выполнить в терминале `.venv/bin/python scripts/garmin/garmin_login.py` (email, пароль, MFA вводятся интерактивно). Пароль в чате не спрашивать, токены не печатать.
- `429` / «ограничил частоту» — подождать и повторить позже, не долбить.

## Если `.venv` нет

```bash
curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
~/.local/bin/uv venv .venv --python 3.12
~/.local/bin/uv pip install --python .venv/bin/python -r scripts/garmin/requirements.txt
```

## Таблицы (`2026-2027/garmin/`)

- `activities.csv` — строка на активность (мультиспорт — по дочерним): время, дистанция, набор/сброс, высоты, скорость, темп и GAP, вертикальная скорость, пульс и зоны 1–5, калории, аэробный/анаэробный эффект, основная польза, Training Load, беговая динамика, мощность, Body Battery, Stamina, потеря жидкости, температура, дыхание, RPE и ощущение, сводка подходов, устройство, заметки.
- `laps.csv` — круги/сплиты: тип интенсивности, дистанция, набор/сброс, темп и GAP, пульс, каденс, мощность.
- `strength sets.csv` — подходы силовых/HIIT: категория и упражнение (как распознали часы), повторы, вес, длительность.

## Правила

- Скрипт заменяет строки выбранной недели во всех трёх файлах, остальные не трогает. Руками эти CSV не переписывать.
- Сырые ответы — в `.garmin_cache/activities/<id>/` (gitignored); если колонка пустая, сначала посмотреть туда, затем при необходимости поправить маппинг в скрипте.
- Предупреждение «Неизвестное значение Garmin: …» — добавить перевод в словарь `ACTIVITY_TYPES` / `TE_LABELS` и т.п. в `fetch_activities.py`.
- Не трогать архив Polar (`training log/`, `cardio load/`) и чужие сезоны без просьбы.
- Не выдумывать тренировки, если API вернул пусто.
- Не ставить новые pip-зависимости сверх `scripts/garmin/requirements.txt`.
