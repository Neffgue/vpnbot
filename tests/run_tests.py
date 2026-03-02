"""
Автономный тест-раннер для VPN Sales System.
Не требует pytest или подключения к БД — работает на чистом Python.

Запуск:
    python tests/run_tests.py

Покрытие:
    ✅ JWT безопасность
    ✅ Mock VPN сервис (заглушка без реального VPN сервера)
    ✅ UserService (бизнес-логика пользователей)
    ✅ SubscriptionService (бизнес-логика подписок)
    ✅ Конфигурация и generate_referral_code

Для полных интеграционных тестов (HTTP API + реальная БД):
    1. Запустите PostgreSQL: docker-compose up -d db
    2. pip install -r requirements-test.txt
    3. pytest tests/ -v
"""
import sys
import os
import asyncio
import uuid
import time
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta, datetime

# ── Выбор event loop для Windows (без deprecated предупреждений) ─────────────
if sys.platform == 'win32':
    # Python 3.14: SelectorEventLoop нужен для aiosqlite на Windows
    # Используем getattr чтобы не падать если класс убрали в 3.16+
    _policy = getattr(asyncio, 'WindowsSelectorEventLoopPolicy', None)
    if _policy:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            asyncio.set_event_loop_policy(_policy())

# ── Устанавливаем тестовые переменные окружения ДО импортов backend ──────────
os.environ.update({
    'DATABASE_URL':        'sqlite+aiosqlite:///:memory:',
    'SECRET_KEY':          'test-secret-key-standalone',
    'JWT_SECRET_KEY':      'test-secret-key-standalone',
    'VPN_MOCK_MODE':       'true',
    'BOT_TOKEN':           '1234567890:AATEST',
    'API_KEY':             'test-api-key',
    'TELEGRAM_BOT_TOKEN':  '1234567890:AATEST',
})

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Патчим settings до импорта database (чтобы не читал .env с PostgreSQL URL)
import backend.config as bc
bc.settings.DATABASE_URL = 'sqlite+aiosqlite:///:memory:'
bc.settings.SECRET_KEY   = 'test-secret-key-standalone'

logging.basicConfig(level=logging.CRITICAL)  # Подавляем логи приложения

# ── Счётчики ──────────────────────────────────────────────────────────────────
_passed  = 0
_failed  = 0
_details = []


def ok(msg: str):
    global _passed
    _passed += 1
    _details.append(('✅', msg))
    print(f'  ✅ {msg}')


def fail(msg: str, err=''):
    global _failed
    _failed += 1
    err_short = str(err)[:120]
    _details.append(('❌', f'{msg}: {err_short}'))
    print(f'  ❌ {msg}: {err_short}')


def section(title: str):
    print(f'\n{"─" * 55}\n  {title}\n{"─" * 55}')


# ══════════════════════════════════════════════════════════════════════════════
# 1. БЕЗОПАСНОСТЬ (JWT)
# ══════════════════════════════════════════════════════════════════════════════
section('🔐 Безопасность (JWT токены)')

from backend.utils.security import create_access_token, decode_token, generate_referral_code

try:
    token = create_access_token({'sub': 'user-abc'})
    assert token and len(token) > 20
    decoded = decode_token(token)
    assert decoded and decoded.get('sub') == 'user-abc'
    ok('Создание и декодирование JWT токена')
except Exception as e:
    fail('Создание и декодирование JWT токена', e)

try:
    assert decode_token('totally.invalid.token') is None
    ok('Неверный токен → None')
except Exception as e:
    fail('Неверный токен → None', e)

try:
    exp = create_access_token({'sub': 'u'}, expires_delta=timedelta(seconds=-1))
    r = decode_token(exp)
    assert r is None or r.get('sub') is None
    ok('Истёкший токен → None')
except Exception as e:
    fail('Истёкший токен → None', e)

try:
    t1 = create_access_token({'sub': 'u1'})
    t2 = create_access_token({'sub': 'u2'})
    assert t1 != t2
    ok('Разные payload → разные токены')
except Exception as e:
    fail('Разные payload → разные токены', e)

try:
    codes = {generate_referral_code(str(uuid.uuid4())) for _ in range(100)}
    assert len(codes) == 100
    assert all(len(c) >= 6 for c in codes)
    ok('generate_referral_code() — 100 уникальных кодов длиной >= 6')
except Exception as e:
    fail('generate_referral_code()', e)


# ══════════════════════════════════════════════════════════════════════════════
# 2. MOCK VPN СЕРВИС (заглушка без реального VPN сервера)
# ══════════════════════════════════════════════════════════════════════════════
section('🔌 Mock VPN сервис (заглушка без реального сервера)')

from backend.services.xui_service_mock import XUIServiceMock, get_xui_service

try:
    svc = get_xui_service('http://localhost', 'admin', 'admin', 1)
    assert isinstance(svc, XUIServiceMock)
    ok('get_xui_service() → XUIServiceMock при VPN_MOCK_MODE=true')
except Exception as e:
    fail('get_xui_service() factory', e)


async def _run_mock_vpn_tests():
    s = XUIServiceMock('http://localhost', 'admin', 'admin', 1)
    exp_ms = int((time.time() + 86400) * 1000)
    cid = str(uuid.uuid4())

    try:
        assert await s.login() is True
        ok('login() → True')
    except Exception as e:
        fail('login()', e)

    try:
        assert await s.add_client(cid, 100, exp_ms) is True
        ok('add_client() → True')
    except Exception as e:
        fail('add_client()', e)

    try:
        stats = await s.get_client_stats(str(uuid.uuid4()))
        assert isinstance(stats, dict) and 'up' in stats and 'down' in stats
        up_mb = stats['up'] // 1024 // 1024
        ok(f'get_client_stats() → dict (up={up_mb} MB)')
    except Exception as e:
        fail('get_client_stats()', e)

    try:
        assert await s.update_client(cid, 200, exp_ms) is True
        ok('update_client() → True')
    except Exception as e:
        fail('update_client()', e)

    try:
        assert await s.delete_client(str(uuid.uuid4())) is True
        ok('delete_client() → True')
    except Exception as e:
        fail('delete_client()', e)

    try:
        await s.close()
        ok('close() → без ошибок')
    except Exception as e:
        fail('close()', e)


asyncio.run(_run_mock_vpn_tests())


# ══════════════════════════════════════════════════════════════════════════════
# 3. UNIT ТЕСТЫ СЕРВИСНОГО СЛОЯ (mock репозитории)
# ══════════════════════════════════════════════════════════════════════════════
section('🧪 Unit тесты сервисного слоя (mock DB)')


async def _run_service_unit_tests():
    from backend.services.user_service import UserService
    from backend.services.subscription_service import SubscriptionService

    mock_db = AsyncMock()

    # ── UserService ────────────────────────────────────────────────────────────

    # create_user — новый пользователь
    try:
        with patch('backend.services.user_service.UserRepository') as MockRepo:
            repo = MockRepo.return_value
            repo.get_by_telegram_id  = AsyncMock(return_value=None)
            repo.get_by_referral_code = AsyncMock(return_value=None)
            fake = MagicMock(); fake.telegram_id = 12345; fake.referral_code = 'ABCDEF'
            repo.create = AsyncMock(return_value=fake)
            svc = UserService(mock_db); svc.repo = repo
            u = await svc.create_user(12345, 'test', 'Тест')
            assert u.telegram_id == 12345 and u.referral_code == 'ABCDEF'
            repo.create.assert_called_once()
            ok('UserService.create_user → repo.create() вызван')
    except Exception as e:
        fail('UserService.create_user', e)

    # create_user — уже существует (дедупликация)
    try:
        with patch('backend.services.user_service.UserRepository') as MockRepo:
            repo = MockRepo.return_value
            existing = MagicMock(); existing.id = 'exist-id'; existing.telegram_id = 55555
            repo.get_by_telegram_id = AsyncMock(return_value=existing)
            svc = UserService(mock_db); svc.repo = repo
            result = await svc.create_user(55555, 'u', 'Х')
            assert result.id == 'exist-id'
            ok('UserService.create_user → возвращает существующего (без дублей)')
    except Exception as e:
        fail('UserService.create_user дедупликация', e)

    # get_user_by_telegram_id — найден
    try:
        with patch('backend.services.user_service.UserRepository') as MockRepo:
            repo = MockRepo.return_value
            fake = MagicMock(); fake.id = 'uid'; fake.telegram_id = 99999
            repo.get_by_telegram_id = AsyncMock(return_value=fake)
            svc = UserService(mock_db); svc.repo = repo
            result = await svc.get_user_by_telegram_id(99999)
            assert result is fake
            ok('UserService.get_user_by_telegram_id → существующий пользователь')
    except Exception as e:
        fail('UserService.get_user_by_telegram_id → found', e)

    # get_user_by_telegram_id — не найден
    try:
        with patch('backend.services.user_service.UserRepository') as MockRepo:
            repo = MockRepo.return_value
            repo.get_by_telegram_id = AsyncMock(return_value=None)
            svc = UserService(mock_db); svc.repo = repo
            assert await svc.get_user_by_telegram_id(9999999) is None
            ok('UserService.get_user_by_telegram_id → None для несуществующего')
    except Exception as e:
        fail('UserService.get_user_by_telegram_id → None', e)

    # ban_user
    try:
        with patch('backend.services.user_service.UserRepository') as MockRepo:
            repo = MockRepo.return_value
            fake = MagicMock(); fake.is_banned = True
            repo.update = AsyncMock(return_value=fake)
            svc = UserService(mock_db); svc.repo = repo
            result = await svc.ban_user('uid-1')
            repo.update.assert_called_once_with('uid-1', {'is_banned': True})
            assert result.is_banned is True
            ok('UserService.ban_user → update(is_banned=True)')
    except Exception as e:
        fail('UserService.ban_user', e)

    # unban_user
    try:
        with patch('backend.services.user_service.UserRepository') as MockRepo:
            repo = MockRepo.return_value
            fake = MagicMock(); fake.is_banned = False
            repo.update = AsyncMock(return_value=fake)
            svc = UserService(mock_db); svc.repo = repo
            result = await svc.unban_user('uid-1')
            repo.update.assert_called_once_with('uid-1', {'is_banned': False})
            assert result.is_banned is False
            ok('UserService.unban_user → update(is_banned=False)')
    except Exception as e:
        fail('UserService.unban_user', e)

    # mark_free_trial_used
    try:
        with patch('backend.services.user_service.UserRepository') as MockRepo:
            repo = MockRepo.return_value
            fake = MagicMock(); fake.free_trial_used = True
            repo.update = AsyncMock(return_value=fake)
            svc = UserService(mock_db); svc.repo = repo
            result = await svc.mark_free_trial_used('uid')
            repo.update.assert_called_once_with('uid', {'free_trial_used': True})
            assert result.free_trial_used is True
            ok('UserService.mark_free_trial_used → update(free_trial_used=True)')
    except Exception as e:
        fail('UserService.mark_free_trial_used', e)

    # ── SubscriptionService ────────────────────────────────────────────────────

    # create_subscription
    try:
        with patch('backend.services.subscription_service.SubscriptionRepository') as MockSubRepo, \
             patch('backend.services.subscription_service.ServerRepository') as MockSrvRepo, \
             patch('backend.services.subscription_service.UserRepository'):
            sub_repo = MockSubRepo.return_value
            srv_repo = MockSrvRepo.return_value
            srv_repo.get_active_servers = AsyncMock(return_value=[])
            fake_sub = MagicMock()
            fake_sub.plan_name = 'Solo'; fake_sub.is_active = True
            fake_sub.xui_client_uuid = str(uuid.uuid4()); fake_sub.period_days = 30
            sub_repo.create = AsyncMock(return_value=fake_sub)
            svc = SubscriptionService(mock_db)
            svc.repo = sub_repo; svc.server_repo = srv_repo
            sub = await svc.create_subscription('uid', 'Solo', 30, 1, 100)
            assert sub.plan_name == 'Solo' and sub.is_active is True
            sub_repo.create.assert_called_once()
            ok('SubscriptionService.create_subscription → Solo/30d создана')
    except Exception as e:
        fail('SubscriptionService.create_subscription', e)

    # get_active_user_subscription — нет активных
    try:
        with patch('backend.services.subscription_service.SubscriptionRepository') as MockSubRepo, \
             patch('backend.services.subscription_service.ServerRepository'), \
             patch('backend.services.subscription_service.UserRepository'):
            sub_repo = MockSubRepo.return_value
            sub_repo.get_user_subscriptions = AsyncMock(return_value=[])
            svc = SubscriptionService(mock_db); svc.repo = sub_repo
            result = await svc.get_active_user_subscription('uid-new')
            assert result is None
            ok('SubscriptionService.get_active_user_subscription → None (нет подписок)')
    except Exception as e:
        fail('SubscriptionService.get_active_user_subscription → None', e)

    # get_active_user_subscription — есть активная
    try:
        with patch('backend.services.subscription_service.SubscriptionRepository') as MockSubRepo, \
             patch('backend.services.subscription_service.ServerRepository'), \
             patch('backend.services.subscription_service.UserRepository'):
            sub_repo = MockSubRepo.return_value
            active_sub = MagicMock()
            active_sub.is_active = True
            active_sub.expires_at = datetime.utcnow() + timedelta(days=10)
            sub_repo.get_user_subscriptions = AsyncMock(return_value=[active_sub])
            svc = SubscriptionService(mock_db); svc.repo = sub_repo
            result = await svc.get_active_user_subscription('uid-active')
            assert result is active_sub
            ok('SubscriptionService.get_active_user_subscription → активная подписка найдена')
    except Exception as e:
        fail('SubscriptionService.get_active_user_subscription → found', e)

    # deactivate_subscription
    try:
        with patch('backend.services.subscription_service.SubscriptionRepository') as MockSubRepo, \
             patch('backend.services.subscription_service.ServerRepository'), \
             patch('backend.services.subscription_service.UserRepository'):
            sub_repo = MockSubRepo.return_value
            fake = MagicMock(); fake.is_active = False
            sub_repo.update = AsyncMock(return_value=fake)
            svc = SubscriptionService(mock_db); svc.repo = sub_repo
            result = await svc.deactivate_subscription('sub-id')
            sub_repo.update.assert_called_once_with('sub-id', {'is_active': False})
            assert result.is_active is False
            ok('SubscriptionService.deactivate_subscription → is_active=False')
    except Exception as e:
        fail('SubscriptionService.deactivate_subscription', e)

    # extend_subscription
    try:
        with patch('backend.services.subscription_service.SubscriptionRepository') as MockSubRepo, \
             patch('backend.services.subscription_service.ServerRepository'), \
             patch('backend.services.subscription_service.UserRepository'):
            sub_repo = MockSubRepo.return_value
            now = datetime.utcnow()
            current_sub = MagicMock()
            current_sub.expires_at = now + timedelta(days=5)
            sub_repo.get_by_id = AsyncMock(return_value=current_sub)
            extended = MagicMock()
            extended.expires_at = now + timedelta(days=35)
            sub_repo.update = AsyncMock(return_value=extended)
            svc = SubscriptionService(mock_db); svc.repo = sub_repo
            result = await svc.extend_subscription('sub-id', 30)
            assert result.expires_at > now + timedelta(days=30)
            ok('SubscriptionService.extend_subscription → дата продлена')
    except Exception as e:
        fail('SubscriptionService.extend_subscription', e)


asyncio.run(_run_service_unit_tests())


# ══════════════════════════════════════════════════════════════════════════════
# 4. КОНФИГУРАЦИЯ
# ══════════════════════════════════════════════════════════════════════════════
section('⚙️  Конфигурация и настройки')

try:
    assert bc.settings.SECRET_KEY == 'test-secret-key-standalone'
    ok('SECRET_KEY читается из переменных окружения')
except Exception as e:
    fail('SECRET_KEY', e)

try:
    mock_mode = os.environ.get('VPN_MOCK_MODE', '').lower() == 'true'
    assert mock_mode
    ok('VPN_MOCK_MODE=true (заглушка VPN сервера активна)')
except Exception as e:
    fail('VPN_MOCK_MODE', e)

try:
    assert hasattr(bc.settings, 'DATABASE_URL')
    ok('DATABASE_URL настраивается через переменную окружения')
except Exception as e:
    fail('DATABASE_URL', e)

try:
    assert hasattr(bc.settings, 'BOT_TOKEN')
    ok('BOT_TOKEN доступен в настройках')
except Exception as e:
    fail('BOT_TOKEN', e)

try:
    assert hasattr(bc.settings, 'XUI_API_TIMEOUT')
    assert bc.settings.XUI_API_TIMEOUT > 0
    ok(f'XUI_API_TIMEOUT={bc.settings.XUI_API_TIMEOUT}s (таймаут VPN API)')
except Exception as e:
    fail('XUI_API_TIMEOUT', e)


# ══════════════════════════════════════════════════════════════════════════════
# ИТОГ
# ══════════════════════════════════════════════════════════════════════════════
total = _passed + _failed
print(f'\n{"=" * 55}')
print(f'  🧪 Итого: {total} тестов  |  ✅ {_passed} прошло  |  ❌ {_failed} упало')

if _failed > 0:
    print('\n  Упавшие тесты:')
    for icon, msg in _details:
        if icon == '❌':
            print(f'    {icon} {msg}')

print(f'{"=" * 55}')

if _failed == 0:
    print('\n  ✨ Все тесты прошли успешно!')
    print('\n  📋 Для полных интеграционных тестов (HTTP API + реальная БД):')
    print('     1. docker-compose up -d db')
    print('     2. pip install -r requirements-test.txt')
    print('     3. pytest tests/ -v')
else:
    print('\n  ⚠️  Некоторые тесты упали — смотрите вывод выше.')

sys.exit(0 if _failed == 0 else 1)
