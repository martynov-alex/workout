---
name: polar-cardio-load
description: >-
  Downloads Polar AccessLink Cardio Load for a Monday–Sunday week and merges it
  into 2026-2027/cardio load/cardio load.csv. Use when the user asks to update
  cardio load, выгрузить кардионагрузку, синхронизировать Polar Flow, обновить
  журнал Cardio Load, или заполнить таблицу cardio load.
---

# Polar Cardio Load

Выгрузка Cardio Load из Polar AccessLink в сезонный CSV. Для этого запроса сеть разрешена. Не переписывать HTTP руками — запускать готовый скрипт.

## Workflow

1. Определи неделю: `ГГГГ-НН` (как папки планов) или любая дата `ДД.ММ.ГГГГ`. Иначе текущая неделя пн–вс.
2. Определи файл:
   - текущий сезон → `2026-2027/cardio load/cardio load.csv`
   - прошлый сезон → `2025-2026/cardio load/cardio load.csv`
   - иначе `--file`
3. Запусти из корня репозитория:

```bash
python3 scripts/fetch_cardio_load.py --week 2026-37
python3 scripts/fetch_cardio_load.py --date 13.09.2026
python3 scripts/fetch_cardio_load.py --file "2025-2026/cardio load/cardio load.csv" --week 2026-20
```

4. Если ответ `403` — один раз `python3 scripts/fetch_cardio_load.py --register`, затем повтори выгрузку.
5. Если `401` / нет токена — попроси обновить `.polar_token` через Bruno `bruno/get polar token.bru`. Не печатай токен и не коммить `.polar_token`.
6. После успеха кратко: неделя, файл, таблица 7 дней (дата, статус, показатель, TRIMP, напряжение, выносливость).

## Правила записи

- Скрипт сам мержит: дни выбранной недели обновляет, остальные строки не трогает.
- Не переписывать `training log` и чужие сезоны без явной просьбы.
- Статусы не сжимать до пяти. Писать полный перевод Polar:

| Polar | CSV |
|---|---|
| `DETRAINING` | Детренированность |
| `MAINTAINING` | Поддержание |
| `PRODUCTIVE` | Эффективность |
| `OVERREACHING` | Перетренированность |
| `RECOVERY_AFTER_OVERREACHING` | Восстановление после перетренированности |
| `PRODUCTIVE_DROPPED_FROM_OVERREACHING` | Эффективность после перетренированности |
| `PRODUCTIVE_ALMOST_OVERREACHING` | Эффективность, почти перетренированность |
| `LOAD_STATUS_NOT_AVAILABLE` | Недоступно |
| `UNRECOGNIZED` | Не распознан |

- CSV: UTF-8, `\n`, запятая, даты `ДД.ММ.ГГГГ`, показатель с одной десятой (`1.0`).
- Токен: `.polar_token`, строка `POLAR_ACCESS_TOKEN=...`.
- Колонки: День, Статус кардионагрузки, Показатель кардионагрузки, Кардионагрузка (TRIMP — Training Impulse), Напряжение, Выносливость.

## Не делать

- Не парсить flow.polar.com.
- Не ставить pip-зависимости.
- Не выдумывать строки, если API не ответил.
