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

В `.polar_token` должны быть `POLAR_CLIENT_ID`, `POLAR_CLIENT_SECRET`, `POLAR_V4_ACCESS_TOKEN`, `POLAR_V4_REFRESH_TOKEN`.

1. Access v4 живёт 12 часов — при 401 скрипт сам обновляет его по refresh token и сохраняет в `.polar_token`.
2. Если refresh token протух (ошибка `Polar OAuth 4xx`) или v4-токенов нет — запустить в фоне с полным доступом `python3 scripts/fetch_training_log.py --login`: откроется браузер, пользователь входит в Polar, локальный callback на `localhost:8765` ловит код, скрипт пишет новую пару токенов. Дождаться строки «Новая пара Polar v4 токенов записана», затем повторить выгрузку.
3. `POLAR_ACCESS_TOKEN` (v3) не трогать — он для кардионагрузки.
4. Токены не печатать и не коммитить; при выводе URL авторизации маскировать `client_id`.

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
