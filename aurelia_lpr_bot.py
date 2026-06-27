"""
Aurelia Alert Bot — "Турбанский ЛПР1"
=======================================

Автоматический бот для Telegram-канала, имитирующий формат боевых сводок
(в духе "ЛПР1") для войны Турбания/КАР vs Курбания во вселенной Aurelia.

КАНОН, КОТОРЫЙ УЧТЁН:
У Курбании НЕТ БПЛА ("БПЛА: ОТСУТСТВУЮТ" — Курбания считает дроны
"непригодными в условиях турбанской РЭБ"). Поэтому все угрозы в этой
версии — артиллерия, РСЗО, тяжёлые миномёты, тактические ракеты "Гром"
и диверсионно-разведывательные группы. Цели — Турбания и Курбанская АР
(зона Козлова), направления огня — типичные "вылетные" районы Курбании.

НАСТРОЙКА
---------
1. Получить токен бота у @BotFather в Telegram.
2. Добавить бота администратором в канал (право публикации сообщений).
3. Узнать chat_id канала: "@your_channel" или числовой ID.
4. Указать токен и chat_id через переменные окружения:
       export AURELIA_BOT_TOKEN="ваш_токен"
       export AURELIA_CHANNEL_ID="@your_channel"
   (либо впишите их прямо в константы ниже)
5. pip install requests
6. python3 aurelia_lpr_bot.py

ПРАКТИЧЕСКИЙ СОВЕТ:
Формат сознательно копирует структуру реальных сводок об обстрелах/БПЛА.
Стоит явно указать в описании канала, что это часть фикшен-проекта
Aurelia (альтернативная история) — это снимает риск путаницы с реальными
сводками для случайных читателей канала.
"""

import os
import random
import time
from datetime import datetime

import requests

# ====================== НАСТРОЙКИ ======================

BOT_TOKEN = os.getenv("AURELIA_BOT_TOKEN", "PASTE_TOKEN_HERE")
CHANNEL_ID = os.getenv("AURELIA_CHANNEL_ID", "@your_channel")

MIN_INTERVAL_SEC = 90        # минимальный интервал между сообщениями
MAX_INTERVAL_SEC = 1200      # максимальный интервал между сообщениями

WAVE_CHANCE = 0.20           # шанс "волны" из нескольких связанных сводок
SITREP_CHANCE = 0.05         # шанс общей сводки по обстановке

# ====================== ГЕОГРАФИЯ: ЦЕЛИ ======================
# Турбания и Курбанская АР (зона Козлова) — обе стороны под угрозой огня.

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

# ====================== ГЕОГРАФИЯ: НАПРАВЛЕНИЯ ОГНЯ ======================
# "Обычно летит (с Курбании)" — типичные районы, откуда идёт огонь.

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
    """Форматирует число в стиле RU: пробел - разделитель тысяч, запятая - дробная часть."""
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
    """
    Серия связанных сообщений об одном направлении - как в реальной ленте,
    где одно событие развивается через несколько сводок подряд.
    """
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

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": CHANNEL_ID, "text": text}, timeout=10)
        if not resp.ok:
            print(f"[{datetime.now():%H:%M:%S}] Ошибка отправки: {resp.text}")
        return resp.ok
    except requests.RequestException as exc:
        print(f"[{datetime.now():%H:%M:%S}] Сбой соединения: {exc}")
        return False


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
                time.sleep(random.randint(15, 60))

        else:
            msg = generate_alert()
            send_message(msg)
            print(f"[{datetime.now():%H:%M:%S}]\n{msg}\n")

        time.sleep(random.randint(MIN_INTERVAL_SEC, MAX_INTERVAL_SEC))


if __name__ == "__main__":
    run()
