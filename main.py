"""
Aurelia Alert Bot — "Турбанский ЛПР1"
=======================================

Автоматический бот для Telegram-канала, имитирующий формат боевых сводок
(в духе "ЛПР1") для войны Турбания/КАР vs Курбания во вселенной Aurelia.

КАНОН, КОТОРЫЙ УЧТЁН:
У Курбании НЕТ БПЛА. Угрозы - артиллерия, РСЗО, тяжёлые миномёты,
тактические ракеты "Гром" и диверсионно-разведывательные группы.

НАСТРОЙКА
---------
1. Токен бота - у @BotFather.
2. Бот - админ канала (право публикации сообщений).
3. chat_id канала: "@your_channel" или числовой ID.
4. Переменные окружения:
       export AURELIA_BOT_TOKEN="8990241307:AAGsWRxCQul8WqGnETqC6ZYjGb0llvkEbWU"
       export AURELIA_CHANNEL_ID="-1004360097165"
       export AURELIA_ADMIN_IDS="7787565361"   # необязательно
       export AURELIA_MIN_INTERVAL="90"                 # необязательно
       export AURELIA_MAX_INTERVAL="1200"               # необязательно
5. pip install requests
6. python3 aurelia_lpr_bot.py

КОМАНДЫ (для админа):
   /stat - написать боту В ЛИЧНОЕ СООБЩЕНИЕ (не в канал!).
           Бот ответит, через сколько будет следующая сводка.
           Если AURELIA_ADMIN_IDS не задан - отвечает всем, кто спросит.

ПРАКТИЧЕСКИЙ СОВЕТ:
Стоит явно указать в описании канала, что это часть фикшен-проекта
Aurelia (альтернативная история) - снимает риск путаницы с реальностью.
"""

import os
import random
import threading
import time
from datetime import datetime

import requests

# ====================== НАСТРОЙКИ ======================

BOT_TOKEN = os.getenv("AURELIA_BOT_TOKEN")
CHANNEL_ID = os.getenv("AURELIA_CHANNEL_ID")


def _safe_int(env_name, default):
    """Безопасно читает целое число из переменной окружения. Не падает на None/мусоре."""
    raw = os.getenv(env_name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"Предупреждение: {env_name}='{raw}' не похоже на число, использую {default}")
        return default


MIN_INTERVAL_SEC = _safe_int("AURELIA_MIN_INTERVAL", 90)
MAX_INTERVAL_SEC = _safe_int("AURELIA_MAX_INTERVAL", 1200)

WAVE_CHANCE = 0.20
SITREP_CHANCE = 0.05

# ID администраторов, которым разрешена команда /stat (через запятую).
# Если не задано - команда отвечает любому, кто её напишет боту в личку.
ADMIN_IDS = {
    int(x) for x in os.getenv("AURELIA_ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

# ====================== ГЕОГРАФИЯ: ЦЕЛИ ======================

TURBANIA_REGIONS = {
    "Турбанов-ярская область": [
        "Дияма-Великая", "Дамирск", "Зорьемаровград", "Саржа", "Чернов",
        "Деши-Зелем", "Вовск", "Рашабад", "Иваненковск", "Сильрыш", "Турбанов Яр",
    ],
    "Север Турбанов-ярской области": [
        "Дашрабат", "Новотурбановка", "Индано", "Ираша",
    ],
    "Тихоборская республика": [
        "Гумыслов", "Дрость", "Турбреколь", "Суэжа", "Алэ-Деша", "Тихоборск",
    ],
    "Лесопольский АО": [
        "Йогурт", "Кудро", "Вальда", "Валь", "Еверен", "Залара", "Чаплар",
        "Камен", "Лахты", "Лесовск", "Азвон", "Высший", "Хуммел", "Рекославск",
        "Ервемовка", "Гугда", "Магнорь", "Славка", "Лесополье", "Рекопль", "Лен",
    ],
    "Новотурбанская область": [
        "Наворой", "Озурт", "Ферам", "Озерок", "Лок", "Кевир", "Азнов",
        "Умурт", "Новотурбанск",
    ],
}

KAR_REGIONS = {
    "Югозапад КАР": ["Умуртов", "Аллара", "Аз", "Алдеруга", "Антонов", "Шарда"],
    "Запад КАР": ["Щемель", "Чернозем", "Зелем", "Гуга", "Рой", "Монорой", "Реренан"],
    "Северозапад КАР": ["Трамапор", "Цетро", "Алугда", "Зелень", "Фаран"],
    "Почти север КАР": ["Сокол"],
    "Север КАР": ["Алер", "Свет", "Чаплонь", "Шельмен", "Сугда"],
}

TARGET_REGIONS = {**TURBANIA_REGIONS, **KAR_REGIONS}

KURBANIA_ORIGIN = {
    "Югозапад/запад Курбании": ["Евгено-Форов", "Горный Ал", "Фор"],
    "Запад/северо-запад Курбании": ["Курбск", "Хуре", "Озерославск"],
    "Север Курбании": ["Ангерас", "Доброгород", "Верходияма"],
}

# ====================== УГРОЗЫ (БЕЗ БПЛА) ======================

THREATS = [
    {"threat": "Тревога по артиллерийскому обстрелу",
     "detail": "артиллерийский обстрел из САУ \"Орудие-152\""},
    {"threat": "Тревога по артиллерийскому обстрелу",
     "detail": "артиллерийский обстрел из САУ \"Орудие-122\""},
    {"threat": "Тревога по артиллерийскому обстрелу",
     "detail": "артиллерийский обстрел из буксируемых гаубиц \"Стена-152\""},
    {"threat": "Тревога по РСЗО",
     "detail": "обстрел РСЗО \"Град-К\""},
    {"threat": "Тревога по РСЗО крупного калибра",
     "detail": "обстрел РСЗО \"Ураган-К\""},
    {"threat": "Тревога по миномётному обстрелу",
     "detail": "обстрел из тяжёлого миномёта \"Молот-240\""},
    {"threat": "Ракетная опасность",
     "detail": "пуск тактического ракетного комплекса \"Гром\""},
    {"threat": "Опасность ДРГ",
     "detail": "выход диверсионно-разведывательной группы"},
    {"threat": "Опасность минирования",
     "detail": "засада и минирование на маршруте снабжения"},
]

TAGS = [
    "Меры безопасности.",
    "Повторно.",
    "Опасность сохраняется.",
    "Ещё фиксации.",
    "Принять меры безопасности.",
    "Покинуть улицы! Срочно!",
    "",
]

TEMPLATES = [
    "{target_city} и близлежащие\n{threat}\n{target_region}",
    "{target_region}\n{threat}\n{tag}",
    "От {origin_city} в направлении {target_city} - {detail}\n{target_region}",
    "{target_city}, {target_region}\n{threat}. {tag}",
    "{target_region}\n{detail} в направлении {target_city}\n{tag}",
    "{origin_region}\nАктивность: {detail}\nНаправление - {target_city}, {target_region}",
    "{target_city}\n{tag}\n{threat}",
]

# ====================== СВОДКА ПО ОБСТАНОВКЕ ======================

SITREP_FACTS = {
    "area_kurbania_km2": 1616390.2,
    "area_kar_km2_pre_kto": 286137.4,
    "border_length_km": 3828.78,
}


def _ru_number(value, decimals=1):
    s = f"{value:,.{decimals}f}"
    integer_part, _, frac_part = s.partition(".")
    integer_part = integer_part.replace(",", " ")
    return f"{integer_part},{frac_part}" if frac_part else integer_part


def generate_sitrep():
    return (
        "Сводка обстановки\n"
        f"Площадь Курбании: {_ru_number(SITREP_FACTS['area_kurbania_km2'])} км²\n"
        f"Площадь Курбанской АР (до КТО): {_ru_number(SITREP_FACTS['area_kar_km2_pre_kto'])} км²\n"
        f"Протяжённость границы Турбания-Курбания: "
        f"{_ru_number(SITREP_FACTS['border_length_km'], 2)} км\n"
        "Линия фронта сохраняется."
    )


# ====================== ОТСЛЕЖИВАНИЕ "СЛЕДУЮЩЕГО ПОСТА" (для /stat) ======================

_next_post_at = time.time()
_next_post_lock = threading.Lock()


def _mark_next_post(seconds_from_now):
    global _next_post_at
    with _next_post_lock:
        _next_post_at = time.time() + seconds_from_now


def _seconds_until_next_post():
    with _next_post_lock:
        return max(0, int(_next_post_at - time.time()))


def _sleep_and_track(seconds):
    _mark_next_post(seconds)
    time.sleep(seconds)


def _format_eta(seconds):
    minutes, sec = divmod(seconds, 60)
    if minutes:
        return f"{minutes} мин {sec} сек"
    return f"{sec} сек"


# ====================== ГЕНЕРАЦИЯ СВОДОК ======================

def _pick_target():
    region = random.choice(list(TARGET_REGIONS.keys()))
    city = random.choice(TARGET_REGIONS[region])
    return region, city


def _pick_origin():
    region = random.choice(list(KURBANIA_ORIGIN.keys()))
    city = random.choice(KURBANIA_ORIGIN[region])
    return region, city


def _compose(target_region, target_city, origin_region, origin_city, threat, tag, template):
    text = template.format(
        target_city=target_city,
        target_region=target_region,
        origin_city=origin_city,
        origin_region=origin_region,
        threat=threat["threat"],
        detail=threat["detail"],
        tag=tag,
    )
    return "\n".join(line for line in text.split("\n") if line.strip())


def generate_alert():
    target_region, target_city = _pick_target()
    origin_region, origin_city = _pick_origin()
    threat = random.choice(THREATS)
    tag = random.choice(TAGS)
    template = random.choice(TEMPLATES)
    return _compose(target_region, target_city, origin_region, origin_city, threat, tag, template)


def generate_wave(count=4):
    origin_region, origin_city = _pick_origin()
    region = random.choice(list(TARGET_REGIONS.keys()))
    cities = random.sample(
        TARGET_REGIONS[region], k=min(count, len(TARGET_REGIONS[region]))
    )
    wave = []
    for city in cities:
        threat = random.choice(THREATS)
        tag = random.choice(TAGS)
        template = random.choice(TEMPLATES)
        wave.append(_compose(region, city, origin_region, origin_city, threat, tag, template))
    return wave


# ====================== ОТПРАВКА В TELEGRAM ======================

def send_message(text, chat_id=None):
    target = chat_id or CHANNEL_ID
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": target, "text": text}, timeout=10)
        if not resp.ok:
            print(f"[{datetime.now():%H:%M:%S}] Ошибка отправки: {resp.text}")
        return resp.ok
    except requests.RequestException as exc:
        print(f"[{datetime.now():%H:%M:%S}] Сбой соединения: {exc}")
        return False


# ====================== АДМИН-КОМАНДЫ ======================

def _is_admin(user_id):
    return not ADMIN_IDS or user_id in ADMIN_IDS


def _handle_command(text, chat_id, user_id):
    command = text.split()[0].split("@")[0]

    if command == "/stat":
        if not _is_admin(user_id):
            send_message("Команда доступна только администратору.", chat_id)
            return
        eta = _seconds_until_next_post()
        send_message(f"Следующая сводка ориентировочно через {_format_eta(eta)}.", chat_id)


def poll_commands():
    """Слушает личные сообщения боту (long polling) и обрабатывает команды."""
    offset = None
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(url, params=params, timeout=35)
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"[{datetime.now():%H:%M:%S}] Сбой опроса команд: {exc}")
            time.sleep(5)
            continue

        if not data.get("ok"):
            print(f"[{datetime.now():%H:%M:%S}] getUpdates вернул ошибку: {data}")
            time.sleep(5)
            continue

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            text = (message.get("text") or "").strip()
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            if text.startswith("/"):
                _handle_command(text, chat_id, user_id)


# ====================== ОСНОВНОЙ ЦИКЛ ======================

def run():
    print("Aurelia Alert Bot запущен. Ctrl+C для остановки.")
    while True:
        roll = random.random()

        if roll < SITREP_CHANCE:
            msg = generate_sitrep()
            send_message(msg)
            print(f"[{datetime.now():%H:%M:%S}]\n{msg}\n")

        elif roll < SITREP_CHANCE + WAVE_CHANCE:
            for msg in generate_wave(count=random.randint(3, 5)):
                send_message(msg)
                print(f"[{datetime.now():%H:%M:%S}]\n{msg}\n")
                _sleep_and_track(random.randint(15, 60))

        else:
            msg = generate_alert()
            send_message(msg)
            print(f"[{datetime.now():%H:%M:%S}]\n{msg}\n")

        _sleep_and_track(random.randint(MIN_INTERVAL_SEC, MAX_INTERVAL_SEC))


if __name__ == "__main__":
    threading.Thread(target=poll_commands, daemon=True).start()
    run()
