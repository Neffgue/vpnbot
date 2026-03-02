# Testing Guide

## Unit Testing

### Setup

```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

### Example Test File

Create `tests/test_user_service.py`:

```python
import pytest
from decimal import Decimal
from backend.models.user import User
from backend.services.user_service import UserService
from backend.database import AsyncSessionLocal


@pytest.mark.asyncio
async def test_create_user():
    """Test user creation."""
    async with AsyncSessionLocal() as db:
        service = UserService(db)
        
        user = await service.create_user(
            telegram_id=123456789,
            username="testuser",
            first_name="Test"
        )
        
        assert user is not None
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.referral_code is not None


@pytest.mark.asyncio
async def test_get_user_by_telegram_id():
    """Test retrieving user by Telegram ID."""
    async with AsyncSessionLocal() as db:
        service = UserService(db)
        
        # Create user
        created = await service.create_user(telegram_id=987654321)
        
        # Retrieve user
        retrieved = await service.get_user_by_telegram_id(987654321)
        
        assert retrieved is not None
        assert retrieved.telegram_id == 987654321


@pytest.mark.asyncio
async def test_add_balance():
    """Test adding balance to user."""
    async with AsyncSessionLocal() as db:
        service = UserService(db)
        
        user = await service.create_user(telegram_id=111111111)
        updated = await service.add_balance(user.id, Decimal("50.00"))
        
        assert updated.balance == Decimal("50.00")


@pytest.mark.asyncio
async def test_ban_user():
    """Test banning a user."""
    async with AsyncSessionLocal() as db:
        service = UserService(db)
        
        user = await service.create_user(telegram_id=222222222)
        banned = await service.ban_user(user.id)
        
        assert banned.is_banned is True
```

### Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_user_service.py

# Run with coverage
pytest --cov=backend tests/

# Run with verbose output
pytest -v tests/
```

## API Testing

### Using curl

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_id": 123456789,
    "username": "testuser",
    "first_name": "Test"
  }'

# Get token
curl -X POST http://localhost:8000/api/v1/auth/token?telegram_id=123456789

# Get current user (replace TOKEN)
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer TOKEN"

# Get active servers
curl -X GET http://localhost:8000/api/v1/servers

# Create payment (replace TOKEN and USER_ID)
curl -X POST http://localhost:8000/api/v1/subscriptions/purchase \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_name": "Solo",
    "period_days": 30
  }'
```

### Using Python requests

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Register
response = requests.post(
    f"{BASE_URL}/auth/register",
    json={
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Test"
    }
)
user = response.json()
print(f"User registered: {user['id']}")

# Get token
response = requests.post(
    f"{BASE_URL}/auth/token?telegram_id=123456789"
)
tokens = response.json()
access_token = tokens['access_token']
print(f"Access token: {access_token}")

# Get current user
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(
    f"{BASE_URL}/users/me",
    headers=headers
)
user = response.json()
print(f"Current user: {user}")

# List servers
response = requests.get(f"{BASE_URL}/servers")
servers = response.json()
print(f"Active servers: {len(servers)}")

# Purchase subscription
response = requests.post(
    f"{BASE_URL}/subscriptions/purchase",
    headers=headers,
    json={
        "plan_name": "Solo",
        "period_days": 30
    }
)
payment = response.json()
print(f"Payment created: {payment}")
```

### Using Postman

1. **Create Environment**
   - Set `base_url = http://localhost:8000/api/v1`
   - Set `token = ` (empty initially)

2. **Register Request**
   - Method: POST
   - URL: `{{base_url}}/auth/register`
   - Body:
     ```json
     {
       "telegram_id": 123456789,
       "username": "postman_user",
       "first_name": "Postman"
     }
     ```

3. **Get Token Request**
   - Method: POST
   - URL: `{{base_url}}/auth/token?telegram_id=123456789`
   - Tests (script):
     ```javascript
     var jsonData = pm.response.json();
     pm.environment.set("token", jsonData.access_token);
     ```

4. **Protected Requests**
   - Add header: `Authorization: Bearer {{token}}`

## Load Testing

### Using Apache Bench

```bash
# Install
sudo apt-get install apache2-utils

# Test with 100 requests, 10 concurrent
ab -n 100 -c 10 http://localhost:8000/health

# Test with custom header (token)
ab -n 100 -c 10 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/users/me
```

### Using Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between


class VPNAPIUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """Login on start."""
        response = self.client.post(
            "/api/v1/auth/token",
            params={"telegram_id": 123456789}
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task
    def get_servers(self):
        """Get servers."""
        self.client.get("/api/v1/servers")
    
    @task
    def get_user_profile(self):
        """Get user profile."""
        self.client.get("/api/v1/users/me", headers=self.headers)
    
    @task
    def get_subscriptions(self):
        """Get user subscriptions."""
        self.client.get("/api/v1/subscriptions", headers=self.headers)
```

Run:
```bash
pip install locust
locust -f locustfile.py --host=http://localhost:8000
```

Visit http://localhost:8089 to start testing.

## Integration Testing

### Database Setup for Tests

Create `tests/conftest.py`:

```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.database import Base
from backend.models import User, Subscription, Server, Payment, Referral


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    """Create test database engine."""
    # Use SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create async session for each test."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
```

## Performance Testing

### Database Query Performance

```python
import time
import asyncio
from backend.database import AsyncSessionLocal
from backend.repositories.user_repo import UserRepository


async def test_query_performance():
    """Test query performance."""
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        
        # Measure time
        start = time.time()
        users = await repo.get_all(limit=1000)
        elapsed = time.time() - start
        
        print(f"Retrieved {len(users)} users in {elapsed:.2f}s")
        assert elapsed < 1.0  # Should complete in under 1 second


asyncio.run(test_query_performance())
```

### API Response Time

```python
import httpx
import time


async def test_api_response_time():
    """Test API response times."""
    async with httpx.AsyncClient() as client:
        # Measure response time
        start = time.time()
        response = await client.get("http://localhost:8000/api/v1/servers")
        elapsed = time.time() - start
        
        print(f"API response: {elapsed:.2f}s")
        assert response.status_code == 200
        assert elapsed < 0.5  # Should respond in under 500ms


asyncio.run(test_api_response_time())
```

## Security Testing

### SQL Injection

```python
# Test that SQL injection attempts are prevented
response = client.get(
    "/api/v1/admin/users/search",
    params={"query": "' OR '1'='1"}
)
# Should return empty results or error, not execute injection
```

### XSS Prevention

```python
# Test that HTML/JS in user input is safely handled
response = client.post(
    "/api/v1/auth/register",
    json={
        "telegram_id": 123,
        "username": "<script>alert('xss')</script>"
    }
)
# Username should be stored safely
```

### CSRF Protection

```python
# Test that CSRF tokens are required for state-changing requests
response = client.post(
    "/api/v1/subscriptions/purchase",
    json={"plan_name": "Solo", "period_days": 30}
)
# Should fail without valid token
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
      run: |
        pytest --cov=backend tests/
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Manual Testing Checklist

- [ ] User registration works
- [ ] Authentication tokens are issued correctly
- [ ] Protected endpoints require valid token
- [ ] User profile can be viewed and updated
- [ ] Servers are listed correctly
- [ ] Payment creation works
- [ ] Payment webhooks are processed
- [ ] Subscriptions are created after payment
- [ ] Referral bonuses are awarded
- [ ] Admin functions work (ban, balance, etc.)
- [ ] Bot texts can be configured
- [ ] Plans can be created/updated
- [ ] Database migrations work
- [ ] Error handling is correct
- [ ] Logging is working

## Troubleshooting Tests

### ImportError with async

```python
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Or mark async tests
@pytest.mark.asyncio
async def test_something():
    ...
```

### Database locked

```python
# Use SQLite in-memory for testing instead of PostgreSQL
# Or ensure tests run sequentially
pytest -p no:xdist
```

### Timeout errors

```python
# Increase timeout for slow operations
@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_slow_operation():
    ...
```
