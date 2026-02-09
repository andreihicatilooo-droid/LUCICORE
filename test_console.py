#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           LUCICORE API — Консольное меню тестирования           ║
╚══════════════════════════════════════════════════════════════════╝

Интерактивная консоль для тестирования всех эндпоинтов LUCICORE API
через LucicoreClient.

Запуск:
    python test_console.py                          # настройки по умолчанию
    python test_console.py --url http://host:8000   # свой URL
    python test_console.py --token my-secret-token  # свой Bearer-токен

Требования:
    • Запущенный LUCICORE API сервер
    • pip install httpx python-dotenv
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Optional

# Добавляем корень проекта в PATH, чтобы импорт shared работал
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from shared.lucicore_client import LucicoreClient, LucicoreAPIError

load_dotenv()

# ─────────────────────────────────────────────────────────────────
# Цвета терминала (ANSI)
# ─────────────────────────────────────────────────────────────────
class C:
    """ANSI-коды цветов для красивого вывода в терминале."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    BG_BLUE = "\033[44m"
    BG_RED  = "\033[41m"
    BG_GREEN = "\033[42m"


# ─────────────────────────────────────────────────────────────────
# Утилиты вывода
# ─────────────────────────────────────────────────────────────────
def clear_screen():
    """Очистить терминал."""
    os.system("clear" if os.name != "nt" else "cls")


def print_header(title: str):
    """Напечатать заголовок секции."""
    width = 62
    print()
    print(f"{C.CYAN}{'─' * width}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
    print(f"{C.CYAN}{'─' * width}{C.RESET}")


def print_success(msg: str):
    print(f"  {C.GREEN}✔ {msg}{C.RESET}")


def print_error(msg: str):
    print(f"  {C.RED}✘ {msg}{C.RESET}")


def print_info(msg: str):
    print(f"  {C.BLUE}ℹ {msg}{C.RESET}")


def print_warn(msg: str):
    print(f"  {C.YELLOW}⚠ {msg}{C.RESET}")


def print_json(data: Any, indent: int = 2):
    """Красиво напечатать JSON с подсветкой."""
    if data is None:
        print(f"  {C.DIM}(пустой ответ){C.RESET}")
        return
    raw = json.dumps(data, ensure_ascii=False, indent=indent, default=str)
    for line in raw.split("\n"):
        # Подсветка ключей
        colored = line
        if '":' in line:
            key_end = line.index('":')
            key_start = line.index('"')
            colored = (
                line[:key_start]
                + C.MAGENTA
                + line[key_start : key_end + 1]
                + C.RESET
                + line[key_end + 1 :]
            )
        print(f"  {colored}")


def print_user_table(users: list[dict]):
    """Напечатать пользователей в табличном формате."""
    if not users:
        print_warn("Список пуст")
        return

    # Определяем ширину колонок
    h_w = max(len(u.get("hash_id", "")[:12]) for u in users)
    h_w = max(h_w, 7)  # минимум "hash_id"
    n_w = max(len(u.get("username", "")) for u in users)
    n_w = max(n_w, 8)

    hdr = (
        f"  {C.BOLD}{C.WHITE}"
        f"{'#':<4} "
        f"{'hash_id':<{h_w + 2}} "
        f"{'username':<{n_w + 2}} "
        f"{'email':<22} "
        f"{'active':>7} "
        f"{'balance':>9}"
        f"{C.RESET}"
    )
    sep = f"  {C.DIM}{'─' * (4 + h_w + n_w + 22 + 7 + 9 + 12)}{C.RESET}"

    print(hdr)
    print(sep)
    for i, u in enumerate(users, 1):
        hid = u.get("hash_id", "???")[:12] + "…"
        name = u.get("username", "—")
        email = u.get("email") or "—"
        if len(email) > 20:
            email = email[:18] + "…"
        active = f"{C.GREEN}да{C.RESET}" if u.get("is_active") else f"{C.RED}нет{C.RESET}"
        balance = u.get("balance", 0.0)
        print(
            f"  {C.DIM}{i:<4}{C.RESET} "
            f"{C.CYAN}{hid:<{h_w + 2}}{C.RESET} "
            f"{C.WHITE}{name:<{n_w + 2}}{C.RESET} "
            f"{email:<22} "
            f"{active:>16} "
            f"{C.YELLOW}{balance:>9.2f}{C.RESET}"
        )


def prompt(text: str, default: str = "") -> str:
    """Запросить ввод с необязательным значением по умолчанию."""
    suffix = f" [{C.DIM}{default}{C.RESET}]" if default else ""
    try:
        val = input(f"  {C.YELLOW}▸{C.RESET} {text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return val or default


def prompt_int(text: str, default: int | None = None) -> int | None:
    """Запросить целое число."""
    d = str(default) if default is not None else ""
    raw = prompt(text, d)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print_error("Нужно целое число")
        return None


def pause():
    """Пауза до нажатия Enter."""
    try:
        input(f"\n  {C.DIM}Нажмите Enter для продолжения...{C.RESET}")
    except (EOFError, KeyboardInterrupt):
        pass


# ─────────────────────────────────────────────────────────────────
# Главное меню
# ─────────────────────────────────────────────────────────────────
MAIN_MENU = f"""
{C.BOLD}{C.BG_BLUE}{C.WHITE} LUCICORE API  —  Консоль тестирования {C.RESET}

  {C.BOLD}{C.CYAN}[ Общее ]{C.RESET}
    {C.WHITE}1{C.RESET}  — Проверка здоровья          {C.DIM}GET  /health{C.RESET}
    {C.WHITE}2{C.RESET}  — Корневой эндпоинт          {C.DIM}GET  /{C.RESET}

  {C.BOLD}{C.CYAN}[ Пользователи ]{C.RESET}
    {C.WHITE}3{C.RESET}  — Список пользователей       {C.DIM}GET  /users/{C.RESET}
    {C.WHITE}4{C.RESET}  — Найти по ID (числовой)     {C.DIM}GET  /users/{{id}}{C.RESET}
    {C.WHITE}5{C.RESET}  — Найти по HASH              {C.DIM}GET  /users/hash/{{hash_id}}{C.RESET}
    {C.WHITE}6{C.RESET}  — Создать пользователя       {C.DIM}POST /users/{C.RESET}
    {C.WHITE}7{C.RESET}  — Обновить по ID             {C.DIM}PUT  /users/{{id}}{C.RESET}
    {C.WHITE}8{C.RESET}  — Обновить по HASH           {C.DIM}PUT  /users/hash/{{hash_id}}{C.RESET}
    {C.WHITE}9{C.RESET}  — Удалить по ID              {C.DIM}DEL  /users/{{id}}{C.RESET}
    {C.WHITE}10{C.RESET} — Удалить по HASH            {C.DIM}DEL  /users/hash/{{hash_id}}{C.RESET}

  {C.BOLD}{C.CYAN}[ Merchant / Web Client API ]{C.RESET}
    {C.WHITE}11{C.RESET} — Получить капчу             {C.DIM}GET  /merchant/captcha{C.RESET}
    {C.WHITE}12{C.RESET} — Регистрация в Merchant     {C.DIM}POST /users/{{id}}/merchant/register{C.RESET}
    {C.WHITE}13{C.RESET} — Синхронизация профиля      {C.DIM}POST /users/{{id}}/merchant/sync{C.RESET}

  {C.BOLD}{C.CYAN}[ Массовые операции ]{C.RESET}
    {C.WHITE}14{C.RESET} — Создать N тестовых юзеров
    {C.WHITE}15{C.RESET} — Удалить ВСЕХ пользователей

  {C.BOLD}{C.RED}  0{C.RESET}  — Выход
"""


# ─────────────────────────────────────────────────────────────────
# Обработчики пунктов меню
# ─────────────────────────────────────────────────────────────────

async def cmd_health(client: LucicoreClient):
    """1 — Проверка здоровья."""
    print_header("Проверка здоровья API")
    t0 = time.monotonic()
    result = await client.health()
    ms = (time.monotonic() - t0) * 1000
    print_json(result)
    status = result.get("status", "unknown")
    if status == "healthy":
        print_success(f"Сервер доступен  ({ms:.0f} мс)")
    else:
        print_warn(f"Статус: {status}  ({ms:.0f} мс)")


async def cmd_root(client: LucicoreClient):
    """2 — Корневой эндпоинт."""
    print_header("Корневой эндпоинт  GET /")
    result = await client._get("/")
    print_json(result)


async def cmd_get_users(client: LucicoreClient):
    """3 — Список пользователей."""
    print_header("Список пользователей  GET /users/")
    skip = prompt_int("skip (смещение)", 0) or 0
    limit = prompt_int("limit (лимит)", 100) or 100
    users = await client.get_users(skip=skip, limit=limit)
    print()
    print_user_table(users)
    print_info(f"Получено: {len(users)} записей")


async def cmd_get_user_by_id(client: LucicoreClient):
    """4 — Найти по ID."""
    print_header("Найти по числовому ID  GET /users/{id}")
    uid = prompt_int("user_id")
    if uid is None:
        return
    result = await client.get_user(uid)
    print_json(result)
    print_success(f"Пользователь найден: {result.get('username')}")


async def cmd_get_user_by_hash(client: LucicoreClient):
    """5 — Найти по HASH."""
    print_header("Найти по HASH  GET /users/hash/{hash_id}")
    hash_id = prompt("hash_id")
    if not hash_id:
        print_error("hash_id не может быть пустым")
        return
    result = await client.get_user_by_hash(hash_id)
    print_json(result)
    print_success(f"Пользователь найден: {result.get('username')}")


async def cmd_create_user(client: LucicoreClient):
    """6 — Создать пользователя."""
    print_header("Создать пользователя  POST /users/")
    username = prompt("username (обязательно)")
    if not username:
        print_error("username не может быть пустым")
        return
    password = prompt("password (обязательно)")
    if not password:
        print_error("password не может быть пустым")
        return
    email = prompt("email (необязательно)")
    first_name = prompt("first_name (необязательно)")
    last_name = prompt("last_name (необязательно)")
    avatar = prompt("avatar URL (необязательно)")

    kwargs: dict[str, Any] = {}
    if email:
        kwargs["email"] = email
    if first_name:
        kwargs["first_name"] = first_name
    if last_name:
        kwargs["last_name"] = last_name
    if avatar:
        kwargs["avatar"] = avatar

    result = await client.create_user(username=username, password=password, **kwargs)
    print()
    print_json(result)
    print_success(f"Создан пользователь: {result.get('username')}  hash_id={result.get('hash_id')}")


async def cmd_update_user_by_id(client: LucicoreClient):
    """7 — Обновить по ID."""
    print_header("Обновить по ID  PUT /users/{id}")
    uid = prompt_int("user_id")
    if uid is None:
        return

    print_info("Оставьте поле пустым, чтобы не изменять его")
    fields = _collect_update_fields()
    if not fields:
        print_warn("Нечего обновлять")
        return

    result = await client.update_user(uid, **fields)
    print()
    print_json(result)
    print_success("Пользователь обновлён")


async def cmd_update_user_by_hash(client: LucicoreClient):
    """8 — Обновить по HASH."""
    print_header("Обновить по HASH  PUT /users/hash/{hash_id}")
    hash_id = prompt("hash_id")
    if not hash_id:
        print_error("hash_id не может быть пустым")
        return

    print_info("Оставьте поле пустым, чтобы не изменять его")
    fields = _collect_update_fields()
    if not fields:
        print_warn("Нечего обновлять")
        return

    result = await client.update_user_by_hash(hash_id, **fields)
    print()
    print_json(result)
    print_success("Пользователь обновлён")


def _collect_update_fields() -> dict[str, Any]:
    """Собрать поля для обновления через ввод."""
    fields: dict[str, Any] = {}
    username = prompt("username")
    if username:
        fields["username"] = username
    email = prompt("email")
    if email:
        fields["email"] = email
    first_name = prompt("first_name")
    if first_name:
        fields["first_name"] = first_name
    last_name = prompt("last_name")
    if last_name:
        fields["last_name"] = last_name
    avatar = prompt("avatar")
    if avatar:
        fields["avatar"] = avatar
    is_active = prompt("is_active (true/false)")
    if is_active:
        fields["is_active"] = is_active.lower() in ("true", "1", "да", "yes")
    is_verified = prompt("is_verified (true/false)")
    if is_verified:
        fields["is_verified"] = is_verified.lower() in ("true", "1", "да", "yes")
    return fields


async def cmd_delete_user_by_id(client: LucicoreClient):
    """9 — Удалить по ID."""
    print_header("Удалить по ID  DELETE /users/{id}")
    uid = prompt_int("user_id")
    if uid is None:
        return
    confirm = prompt(f"Удалить пользователя #{uid}? (да/нет)", "нет")
    if confirm.lower() not in ("да", "yes", "y", "1"):
        print_warn("Отменено")
        return
    result = await client.delete_user(uid)
    print_json(result)
    print_success("Пользователь удалён")


async def cmd_delete_user_by_hash(client: LucicoreClient):
    """10 — Удалить по HASH."""
    print_header("Удалить по HASH  DELETE /users/hash/{hash_id}")
    hash_id = prompt("hash_id")
    if not hash_id:
        print_error("hash_id не может быть пустым")
        return
    confirm = prompt(f"Удалить пользователя {hash_id[:12]}…? (да/нет)", "нет")
    if confirm.lower() not in ("да", "yes", "y", "1"):
        print_warn("Отменено")
        return
    result = await client.delete_user_by_hash(hash_id)
    print_json(result)
    print_success("Пользователь удалён")


async def cmd_get_captcha(client: LucicoreClient):
    """11 — Получить капчу."""
    print_header("Получить капчу  GET /merchant/captcha")
    result = await client.get_captcha()

    # Обрезаем base64-строку для вывода
    display = dict(result)
    img = display.get("image", "")
    if len(img) > 80:
        display["image"] = img[:60] + f"…[{len(img)} символов]"
    print_json(display)

    captcha_id = result.get("captcha_id", "???")
    image_url = result.get("image_url", "")
    print_success(f"captcha_id = {captcha_id}")
    if image_url:
        print_success(f"Файл капчи: {C.CYAN}{image_url}{C.RESET}")


async def cmd_register_merchant(client: LucicoreClient):
    """12 — Регистрация в Merchant."""
    print_header("Регистрация в Merchant  POST /users/{id}/merchant/register")
    uid = prompt_int("user_id")
    if uid is None:
        return
    captcha_id = prompt("captcha_id")
    if not captcha_id:
        print_error("captcha_id обязателен")
        return
    captcha_answer = prompt("captcha_answer")
    if not captcha_answer:
        print_error("captcha_answer обязателен")
        return
    result = await client.register_merchant(uid, captcha_id=captcha_id, captcha_answer=captcha_answer)
    print_json(result)
    print_success(f"Привязан: hash_id={result.get('hash_id')}, merchant_id={result.get('merchant_client_id')}")


async def cmd_sync_merchant(client: LucicoreClient):
    """13 — Синхронизация профиля."""
    print_header("Синхронизация профиля  POST /users/{id}/merchant/sync")
    uid = prompt_int("user_id")
    if uid is None:
        return
    result = await client.sync_merchant(uid)
    print_json(result)
    print_success("Профиль синхронизирован")


async def cmd_bulk_create(client: LucicoreClient):
    """14 — Создать N тестовых юзеров."""
    print_header("Массовое создание тестовых пользователей")
    n = prompt_int("Количество пользователей", 5) or 5
    prefix = prompt("Префикс username", "testuser")
    password = prompt("Пароль для всех", "pass123")
    print()

    created = 0
    errors = 0
    for i in range(1, n + 1):
        ts = int(time.time() * 1000) % 100000
        username = f"{prefix}_{ts}_{i}"
        try:
            result = await client.create_user(
                username=username,
                password=password,
                email=f"{username}@test.local",
                first_name=f"Тест-{i}",
            )
            hid = result.get("hash_id", "???")
            print(f"  {C.GREEN}✔{C.RESET} [{i}/{n}] {C.CYAN}{username}{C.RESET}  →  hash_id={C.MAGENTA}{hid}{C.RESET}")
            created += 1
        except LucicoreAPIError as e:
            print(f"  {C.RED}✘{C.RESET} [{i}/{n}] {username}: {e.detail}")
            errors += 1

    print()
    print_success(f"Создано: {created}")
    if errors:
        print_error(f"Ошибок: {errors}")


async def cmd_bulk_delete(client: LucicoreClient):
    """15 — Удалить ВСЕХ пользователей."""
    print_header("Удаление ВСЕХ пользователей")
    users = await client.get_users(limit=10000)
    total = len(users)
    if total == 0:
        print_warn("Пользователей нет")
        return

    print_warn(f"Будет удалено: {total} пользователей!")
    confirm = prompt("Введите 'УДАЛИТЬ' для подтверждения")
    if confirm != "УДАЛИТЬ":
        print_warn("Отменено")
        return

    deleted = 0
    for u in users:
        hid = u.get("hash_id")
        try:
            await client.delete_user_by_hash(hid)
            deleted += 1
            print(f"  {C.RED}✘{C.RESET} {u.get('username')}  ({hid[:12]}…)")
        except LucicoreAPIError as e:
            print_error(f"{u.get('username')}: {e.detail}")

    print()
    print_success(f"Удалено: {deleted}/{total}")


# ─────────────────────────────────────────────────────────────────
# Маршрутизация команд
# ─────────────────────────────────────────────────────────────────
COMMANDS = {
    "1":  cmd_health,
    "2":  cmd_root,
    "3":  cmd_get_users,
    "4":  cmd_get_user_by_id,
    "5":  cmd_get_user_by_hash,
    "6":  cmd_create_user,
    "7":  cmd_update_user_by_id,
    "8":  cmd_update_user_by_hash,
    "9":  cmd_delete_user_by_id,
    "10": cmd_delete_user_by_hash,
    "11": cmd_get_captcha,
    "12": cmd_register_merchant,
    "13": cmd_sync_merchant,
    "14": cmd_bulk_create,
    "15": cmd_bulk_delete,
}


# ─────────────────────────────────────────────────────────────────
# Главный цикл
# ─────────────────────────────────────────────────────────────────

async def main_loop(base_url: str, api_token: str | None):
    """Основной цикл интерактивного меню."""
    async with LucicoreClient(base_url=base_url, api_token=api_token) as client:
        # Проверяем связь при старте
        clear_screen()
        print(f"\n  {C.DIM}Подключение к {C.CYAN}{base_url}{C.RESET}{C.DIM}...{C.RESET}")
        try:
            await client.health()
            print_success(f"Сервер доступен: {base_url}")
        except Exception as e:
            print_error(f"Не удалось подключиться: {e}")
            print_info("Убедитесь, что сервер запущен (python -m uvicorn app.main:app)")
            return

        if api_token:
            print_info(f"Bearer-токен: {api_token[:8]}…{'*' * 8}")
        else:
            print_warn("Bearer-токен не задан — мутирующие операции могут быть недоступны")

        while True:
            print(MAIN_MENU)
            choice = prompt("Выберите пункт меню").strip()

            if choice == "0":
                print(f"\n  {C.DIM}До свидания!{C.RESET}\n")
                break

            handler = COMMANDS.get(choice)
            if handler is None:
                print_error(f"Неизвестный пункт: {choice}")
                continue

            try:
                await handler(client)
            except LucicoreAPIError as e:
                print()
                print_error(f"API ошибка [{e.status_code}]: {e.detail}")
            except Exception as e:
                print()
                print_error(f"Ошибка: {type(e).__name__}: {e}")

            pause()


def parse_args():
    """Разобрать аргументы командной строки."""
    import argparse

    parser = argparse.ArgumentParser(
        description="LUCICORE API — Консольное меню тестирования",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Примеры:\n"
            "  python test_console.py\n"
            "  python test_console.py --url http://192.168.1.10:8000\n"
            "  python test_console.py --token change-me-sales-token\n"
        ),
    )
    parser.add_argument(
        "--url",
        default=os.getenv("LUCICORE_API_URL", "http://127.0.0.1:8000"),
        help="Базовый URL сервера (по умолчанию: $LUCICORE_API_URL или http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("BOT_SALES_API_TOKEN"),
        help="Bearer API-токен (по умолчанию: $BOT_SALES_API_TOKEN)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(main_loop(args.url, args.token))
    except KeyboardInterrupt:
        print(f"\n  {C.DIM}Прервано (Ctrl+C){C.RESET}\n")
