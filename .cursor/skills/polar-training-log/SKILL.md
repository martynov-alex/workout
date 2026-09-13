---
name: polar-training-log
description: >-
  Downloads Polar AccessLink v4 training session summaries for a Monday–Sunday
  week and merges them into 2026-2027/training log/training log.csv. Use when
  the user asks to update the training log, выгрузить тренировки, синхронизировать
  тренировки Polar, загрузить журнал тренировок, или заполнить training log.
---

# Polar Training Log

Выгрузка сводок тренировок из Polar AccessLink **v4**. Сеть разрешена. Не переписывать HTTP руками — запускать скрипт. Не запрашивать samples, routes, laps, GPX.

## Токен v4

Отдельный OAuth, не тот же, что для cardio load.

1. Браузер: `https://auth.polar.com/oauth/authorize?client_id=...&response_type=code&scope=training_sessions:read sports:read&redirect_uri=http://localhost:8765/callback`
2. Bruno `bruno/get polar v4 token.bru` → в `.polar_token`:

```
POLAR_V4_ACCESS_TOKEN=...
POLAR_V4_REFRESH_TOKEN=...
```

3. Для автообновления скриптом добавь ещё `POLAR_CLIENT_ID` и `POLAR_CLIENT_SECRET`. Иначе при 401 — `bruno/refresh polar v4 token.bru`.
4. `POLAR_ACCESS_TOKEN` (v3) не трогать — он для кардионагрузки.
5. Токены не печатать и не коммитить. Access v4 живёт 12 часов.

## Workflow

1. Неделя `ГГГГ-НН` или дата `ДД.ММ.ГГГГ`. Иначе текущая пн–вс.
2. Файл: `2026-2027/training log/training log.csv`.
3. Из корня:

```bash
python3 scripts/fetch_training_log.py --week 2026-37
python3 scripts/fetch_training_log.py --date 13.09.2026
```

4. После успеха: неделя, число тренировок, кратко дата / спорт / длительность / км / набор / ЧСС.

## Форма CSV

`GET /v4/data/training-sessions/list` по дням с `features=statistics,zones,training-load-report`.

Есть набор/сброс, скорость, темп, каденс, мощность, зоны, Training Load Pro. Посекундные ряды и трек не писать.

## Правила

- Скрипт заменяет строки выбранной недели, остальные не трогает.
- Не переписывать `cardio load` и чужие сезоны без просьбы.
- Не выдумывать тренировки, если API пустой.
- Не ставить pip-зависимости.
