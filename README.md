# workout

Разработка тренировочных планов с использованием AI.

Загрузка артефактов тренировок -> генерация новых тренировок с использованием Claude Opus в Cursor на базе предыдущих и планового макроцикла.

## Данные Garmin

С 12.10.2026 тренировки, сон, HRV, готовность и нагрузка выгружаются из Garmin Connect в `2026-2027/garmin/` скиллами `garmin-training-log` и `garmin-health`. Данные Polar до 11.10.2026 лежат в `training log/` и `cardio load/` как архив.

Настройка (один раз):

```bash
curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
~/.local/bin/uv venv .venv --python 3.12
~/.local/bin/uv pip install --python .venv/bin/python -r scripts/garmin/requirements.txt
.venv/bin/python scripts/garmin/garmin_login.py
```

Вход спрашивает email, пароль и MFA-код; токены сохраняются в `~/.garminconnect/` и обновляются автоматически.

Выгрузка недели:

```bash
.venv/bin/python scripts/garmin/fetch_activities.py --week 2026-42
.venv/bin/python scripts/garmin/fetch_health.py --week 2026-42
```
