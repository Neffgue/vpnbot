#!/usr/bin/env python3
"""
Pre-deploy проверка VPN Sales System.
Запуск: python scripts/pre_deploy_check.py

Проверяет:
 1. Наличие всех обязательных переменных окружения
 2. Синтаксис всех Python-файлов
 3. Импорты backend (config, database, models, services)
 4. Security (JWT)
 5. Mock VPN сервис
 6. Конфигурацию admin-panel (package.json)
 7. Наличие всех Docker файлов
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import timedelta

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

passed = 0
failed = 0
warnings = []


def ok(msg):
    global passed
    passed += 1
    print(f"  ✅ {msg}")


def fail(msg, detail=""):
    global failed
    failed += 1
    print(f"  ❌ {msg}")
    if detail:
        print(f"     → {detail}")


def warn(msg):
    warnings.append(msg)
    print(f"  ⚠️  {msg}")


def section(title):
    print(f"\n{'─' * 55}\n  {title}\n{'─' * 55}")


# ── 1. Переменные окружения ───────────────────────────────────
section("1. Переменные окружения (.env)")

env_file = ROOT / ".env"
env_vars = {}
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env_vars[k.strip()] = v.strip()
    ok(f".env файл найден ({len(env_vars)} переменных)")
else:
    fail(".env файл не найден")

REQUIRED = [
    ("BOT_TOKEN", "Telegram Bot Token от @BotFather"),
    ("ADMIN_IDS", "Telegram ID администраторов"),
    ("JWT_SECRET_KEY", "Секретный ключ для JWT"),
    ("ADMIN_USERNAME", "Логин для веб-панели"),
    ("ADMIN_PASSWORD", "Пароль для веб-панели"),
]

for key, desc in REQUIRED:
    val = env_vars.get(key) or os.environ.get(key, "")
    if val and val not in ("", "your_value_here", "change_me"):
        ok(f"{key} установлен")
    else:
        fail(f"{key} не установлен или не изменён", desc)

OPTIONAL = [
    ("YOOKASSA_SHOP_ID", "YooKassa (опционально)"),
    ("WEBHOOK_URL", "Webhook URL (опционально, для production)"),
    ("TELEGRAM_CHANNEL_URL", "URL канала"),
    ("TELEGRAM_SUPPORT_URL", "URL поддержки"),
]
for key, desc in OPTIONAL:
    val = env_vars.get(key) or os.environ.get(key, "")
    if not val:
        warn(f"{key} не установлен — {desc}")

mock_mode = env_vars.get("VPN_MOCK_MODE", "true").lower() in ("true", "1", "yes")
if mock_mode:
    ok("VPN_MOCK_MODE=true (работает без реальных VPN серверов)")
else:
    warn("VPN_MOCK_MODE=false — убедитесь что VPN серверы настроены")


# ── 2. Синтаксис Python файлов ────────────────────────────────
section("2. Синтаксис Python файлов")

python_files = [
    "backend/main.py",
    "backend/config.py",
    "backend/database.py",
    "backend/api/v1/endpoints/users.py",
    "backend/api/v1/endpoints/admin.py",
    "backend/api/v1/endpoints/subscriptions.py",
    "backend/api/v1/endpoints/payments.py",
    "backend/api/v1/endpoints/servers.py",
    "backend/api/v1/endpoints/auth.py",
    "backend/api/v1/router.py",
    "backend/api/deps.py",
    "backend/models/user.py",
    "backend/models/subscription.py",
    "backend/models/config.py",
    "backend/services/user_service.py",
    "backend/services/subscription_service.py",
    "backend/services/payment_service.py",
    "backend/services/xui_service_mock.py",
    "backend/utils/security.py",
    "bot/main.py",
    "bot/config.py",
    "bot/loader.py",
    "bot/handlers/start.py",
    "bot/handlers/admin.py",
    "bot/handlers/payment.py",
    "bot/handlers/cabinet.py",
    "bot/handlers/free_trial.py",
    "bot/handlers/instructions.py",
    "bot/handlers/referral.py",
    "bot/handlers/notifications.py",
    "bot/keyboards/main_menu.py",
    "bot/keyboards/admin_kb.py",
    "bot/keyboards/payment_kb.py",
    "bot/keyboards/subscription_kb.py",
    "bot/states/admin_states.py",
    "bot/utils/api_client.py",
    "bot/utils/formatters.py",
    "bot/middlewares/auth.py",
]

syntax_errors = 0
for rel_path in python_files:
    full_path = ROOT / rel_path
    if not full_path.exists():
        fail(f"{rel_path} — файл не найден")
        continue
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(full_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            ok(f"{rel_path}")
        else:
            fail(f"{rel_path}", result.stderr.strip()[:120])
            syntax_errors += 1
    except Exception as e:
        fail(f"{rel_path}", str(e))

if syntax_errors == 0:
    print(f"\n  → Синтаксических ошибок не найдено в {len(python_files)} файлах")


# ── 3. Импорты backend ────────────────────────────────────────
section("3. Импорты и конфигурация backend")

# Патчим env для теста
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-predeploy")
os.environ.setdefault("JWT_SECRET_KEY", "test-predeploy")
os.environ.setdefault("BOT_TOKEN", env_vars.get("BOT_TOKEN", "1234567890:TEST"))
os.environ.setdefault("VPN_MOCK_MODE", "true")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", env_vars.get("BOT_TOKEN", "1234567890:TEST"))
os.environ.setdefault("ADMIN_IDS", env_vars.get("ADMIN_IDS", "0"))
os.environ.setdefault("TELEGRAM_ADMIN_IDS", env_vars.get("ADMIN_IDS", "0"))

imports_to_test = [
    ("backend.config", "settings"),
    ("backend.database", "Base"),
    ("backend.models.user", "User"),
    ("backend.models.subscription", "Subscription"),
    ("backend.models.config", "BotText, PlanPrice"),
    ("backend.utils.security", "create_access_token, decode_token, generate_referral_code"),
    ("backend.services.xui_service_mock", "XUIServiceMock, get_xui_service"),
    ("backend.api.v1.router", "api_router"),
]

for module, attrs in imports_to_test:
    try:
        import importlib
        mod = importlib.import_module(module)
        for attr in attrs.split(","):
            attr = attr.strip()
            if attr and not hasattr(mod, attr):
                raise AttributeError(f"No attribute '{attr}'")
        ok(f"import {module} ({attrs})")
    except Exception as e:
        fail(f"import {module}", str(e)[:100])


# ── 4. Security JWT ───────────────────────────────────────────
section("4. JWT Безопасность")

try:
    from backend.utils.security import create_access_token, decode_token, generate_referral_code
    import uuid

    token = create_access_token({"sub": "test-user"})
    decoded = decode_token(token)
    assert decoded and decoded.get("sub") == "test-user"
    ok("create_access_token + decode_token работают")

    expired = create_access_token({"sub": "u"}, expires_delta=timedelta(seconds=-1))
    assert decode_token(expired) is None
    ok("Истёкший токен корректно отклоняется")

    codes = {generate_referral_code(str(uuid.uuid4())) for _ in range(50)}
    assert len(codes) == 50 and all(len(c) >= 6 for c in codes)
    ok("generate_referral_code: 50 уникальных кодов")
except Exception as e:
    fail("Security JWT", str(e))


# ── 5. Mock VPN сервис ────────────────────────────────────────
section("5. Mock VPN сервис (заглушка)")

try:
    from backend.services.xui_service_mock import XUIServiceMock, get_xui_service
    import asyncio, time, uuid as _uuid

    svc = get_xui_service("http://localhost", "admin", "admin", 1)
    assert isinstance(svc, XUIServiceMock)
    ok("get_xui_service() → XUIServiceMock")

    async def _test():
        s = XUIServiceMock("http://localhost", "admin", "admin", 1)
        exp = int((time.time() + 86400) * 1000)
        cid = str(_uuid.uuid4())
        assert await s.login() is True
        assert await s.add_client(cid, 100, exp) is True
        stats = await s.get_client_stats(str(_uuid.uuid4()))
        assert isinstance(stats, dict) and "up" in stats
        assert await s.delete_client(str(_uuid.uuid4())) is True
        await s.close()

    if sys.platform == "win32":
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
            if policy:
                asyncio.set_event_loop_policy(policy())
    asyncio.run(_test())
    ok("Mock VPN: login/add_client/stats/delete/close работают")
except Exception as e:
    fail("Mock VPN сервис", str(e))


# ── 6. Docker файлы ───────────────────────────────────────────
section("6. Docker файлы и конфигурация")

docker_files = [
    "docker-compose.yml",
    "backend/Dockerfile",
    "bot/Dockerfile",
    "worker/Dockerfile",
    "admin-panel/Dockerfile",
    "nginx/nginx.conf",
    ".env",
    "requirements.txt",
    "backend/requirements.txt",
    "bot/requirements.txt",
]

for f in docker_files:
    path = ROOT / f
    if path.exists() and path.stat().st_size > 0:
        ok(f"{f} существует")
    else:
        fail(f"{f} не найден или пустой")


# ── 7. Admin panel ────────────────────────────────────────────
section("7. Admin панель (React)")

package_json = ROOT / "admin-panel" / "package.json"
if package_json.exists():
    try:
        pkg = json.loads(package_json.read_text())
        ok(f"package.json: {pkg.get('name', '?')} v{pkg.get('version', '?')}")
        deps = pkg.get("dependencies", {})
        required_deps = ["react", "react-router-dom", "@tanstack/react-query"]
        for dep in required_deps:
            if dep in deps:
                ok(f"  Зависимость: {dep} {deps[dep]}")
            else:
                fail(f"  Зависимость {dep} не найдена в package.json")
    except Exception as e:
        fail("package.json", str(e))

panel_pages = [
    "admin-panel/src/App.jsx",
    "admin-panel/src/pages/Dashboard.jsx",
    "admin-panel/src/pages/Users.jsx",
    "admin-panel/src/pages/Broadcast.jsx",
    "admin-panel/src/pages/BotTexts.jsx",
    "admin-panel/src/pages/BotButtons.jsx",
    "admin-panel/src/pages/BotSettings.jsx",
    "admin-panel/src/pages/AddBalance.jsx",
    "admin-panel/src/pages/PlanPrices.jsx",
    "admin-panel/src/components/Sidebar.jsx",
]
for f in panel_pages:
    path = ROOT / f
    if path.exists():
        ok(f"{f}")
    else:
        fail(f"{f} не найден")


# ── ИТОГ ──────────────────────────────────────────────────────
total = passed + failed
print(f"\n{'=' * 55}")
print(f"  Итого: {total} проверок  |  ✅ {passed}  |  ❌ {failed}")
if warnings:
    print(f"\n  ⚠️  Предупреждения ({len(warnings)}):")
    for w in warnings:
        print(f"    • {w}")
print(f"{'=' * 55}")

if failed == 0:
    print("\n  🚀 Система готова к деплою!")
    print("\n  Команды для запуска:")
    print("    docker-compose up -d --build")
    print("    docker-compose logs -f backend")
else:
    print(f"\n  ⛔ Исправьте {failed} ошибок перед деплоем.")
    sys.exit(1)
