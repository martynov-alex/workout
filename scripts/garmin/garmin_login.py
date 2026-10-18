#!/usr/bin/env python3
"""Первый вход в Garmin Connect: email, пароль и MFA вводятся в терминале, токены сохраняются локально."""

from __future__ import annotations

from getpass import getpass

from common import TOKENSTORE
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)


def main() -> None:
    email = input("Email Garmin Connect: ").strip()
    password = getpass("Пароль: ")
    client = Garmin(email, password, prompt_mfa=lambda: input("MFA-код: ").strip())
    try:
        client.login(str(TOKENSTORE))
    except GarminConnectAuthenticationError as exc:
        raise SystemExit(f"Вход не удался: {exc}") from exc
    except GarminConnectTooManyRequestsError as exc:
        raise SystemExit(f"Garmin ограничил частоту входов: {exc}. Повтори позже.") from exc
    except GarminConnectConnectionError as exc:
        raise SystemExit(f"Не удалось связаться с Garmin Connect: {exc}") from exc
    print(f"Вход выполнен ({client.get_full_name()}). Токены сохранены в {TOKENSTORE}.")


if __name__ == "__main__":
    main()
