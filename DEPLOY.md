# 🚀 Инструкция по деплою VPN Sales System

## Быстрый старт (5 минут)

### 1. Клонировать и настроить

```bash
git clone <репозиторий>
cd vpn-sales-system

# Скопировать конфиг
cp .env.example .env
```

### 2. Заполнить `.env`

Обязательно заполнить:

| Переменная | Где получить | Пример |
|---|---|---|
| `BOT_TOKEN` | @BotFather в Telegram | `1234567890:AAH...` |
| `ADMIN_IDS` | @userinfobot → Your ID | `123456789` |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` | `a1b2c3...` |
| `ADMIN_USERNAME` | Придумать | `admin` |
| `ADMIN_PASSWORD` | Придумать | `MySecurePass123` |
| `POSTGRES_PASSWORD` | Придумать | `DbPassword456` |

Опционально:
- `YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY` — для приёма платежей картой
- `TELEGRAM_CHANNEL_URL` — ссылка на канал в боте
- `TELEGRAM_SUPPORT_URL` — ссылка на поддержку

> `VPN_MOCK_MODE=true` — бот работает без реальных VPN серверов (заглушка)

### 3. Pre-deploy проверка

```bash
python scripts/pre_deploy_check.py
```

Должно показать: `✅ 82 проверок пройдено`

### 4. Запуск

```bash
# Сборка и запуск всех сервисов
docker-compose up -d --build

# Проверка статуса
docker-compose ps

# Логи backend
docker-compose logs -f backend

# Логи бота
docker-compose logs -f bot
```

### 5. Доступ

| Сервис | URL | Описание |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger документация |
| Admin панель | http://localhost:3000 | React веб-панель |
| Health check | http://localhost:8000/health | Статус системы |

**Логин в веб-панель:** используйте `ADMIN_USERNAME` и `ADMIN_PASSWORD` из `.env`

---

## Структура сервисов

```
postgres    — База данных PostgreSQL 16
redis       — Кеш и очереди задач
backend     — FastAPI API (порт 8000)
bot         — Telegram бот (polling)
worker      — Celery воркер (уведомления, задачи)
beat        — Celery планировщик
admin-panel — React веб-панель (порт 3000)
nginx       — Reverse proxy (порт 80)
```

---

## Управление ботом

### Команды в боте

| Команда | Кто видит | Описание |
|---|---|---|
| `/start` | Все | Главное меню |
| `/admin` | Только ADMIN_IDS | Панель администратора |
| `/help` | Все | Помощь |

> ⚠️ Кнопка «Админ» **не показывается** в главном меню.  
> Доступ только через команду `/admin` для указанных `ADMIN_IDS`.

### Через веб-панель (http://localhost:3000)

- **Дашборд** — статистика: пользователи, подписки, выручка
- **Пользователи** — список, поиск, детали, бан/разбан
- **Рассылка** — отправить сообщение всем / активным / с истёкшей подпиской
- **Тексты бота** — изменить любой текст без перезагрузки бота
- **Кнопки меню** — добавить/убрать/переименовать кнопки
- **Настройки бота** — медиа, тарифы, реферальная программа, уведомления
- **Начислить баланс** — добавить ₽ или дни подписки пользователю
- **Цены тарифов** — Solo и Family, периоды и цены
- **VPN Серверы** — добавить позже (сейчас mock режим)

---

## Добавление VPN серверов (позже)

Когда купите VPN сервер с панелью 3x-ui:

1. В `.env` измените: `VPN_MOCK_MODE=false`
2. Откройте веб-панель → **VPN Серверы** → **Добавить сервер**
3. Заполните: название, страна, IP, порт, URL панели, логин, пароль

---

## Полезные команды

```bash
# Перезапуск одного сервиса
docker-compose restart backend

# Остановить всё
docker-compose down

# Остановить и удалить данные (осторожно!)
docker-compose down -v

# Войти в контейнер backend
docker-compose exec backend bash

# Просмотр всех логов
docker-compose logs -f

# Только логи бота
docker-compose logs -f bot

# Статус здоровья
curl http://localhost:8000/health
```

---

## Обновление

```bash
git pull
docker-compose up -d --build
docker-compose logs -f backend
```

---

## Решение проблем

### Бот не отвечает
```bash
docker-compose logs bot | tail -50
```
Проверь `BOT_TOKEN` в `.env`

### Backend не запускается
```bash
docker-compose logs backend | tail -50
```
Проверь `DATABASE_URL` (PostgreSQL должен быть запущен)

### Веб-панель не открывается
```bash
docker-compose logs admin-panel | tail -20
```
Убедись что порт 3000 не занят

### Pre-deploy проверка падает
```bash
python scripts/pre_deploy_check.py
```
Исправь все ❌ ошибки перед деплоем
