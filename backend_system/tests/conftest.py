import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.services.stream_service import stream_service

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(autouse=True)
def reset_services():
    """Reset singleton services between tests"""
    stream_service.reset()
    yield

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture(scope="function")
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    # Create a session factory bound to the test engine
    async_session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Override get_db to create a new session for each request
    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        full_name="Test User",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def test_user_token(client: AsyncClient, test_user: User) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        json={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    return response.json()["access_token"]

# ------------------------------------------------------------------------------
# Test Logging Configuration
# ------------------------------------------------------------------------------
import os
import time
from datetime import datetime

def pytest_sessionstart(session):
    """记录测试开始时间"""
    session.results = dict(passed=0, failed=0, skipped=0, error=0)
    session.start_time = time.time()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """收集测试结果"""
    outcome = yield
    result = outcome.get_result()

    if result.when == 'call':
        if result.passed:
            item.session.results['passed'] += 1
        elif result.failed:
            item.session.results['failed'] += 1
        elif result.skipped:
            item.session.results['skipped'] += 1
    elif result.when == 'setup' and result.failed:
        # setup failure counts as error/fail
        item.session.results['error'] += 1

def pytest_sessionfinish(session, exitstatus):
    """测试结束时写入日志"""
    end_time = time.time()
    duration = end_time - session.start_time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 确保logs目录存在
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "test_execution_history.log")
    
    # 格式化日志条目
    log_entry = (
        f"[{timestamp}] "
        f"Status: {'PASSED' if exitstatus == 0 else 'FAILED'} | "
        f"Duration: {duration:.2f}s | "
        f"Passed: {session.results['passed']} | "
        f"Failed: {session.results['failed']} | "
        f"Skipped: {session.results['skipped']} | "
        f"Errors: {session.results['error']}\n"
    )
    
    # 追加到日志文件
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f"\nTest execution log appended to: {log_file}")
    except Exception as e:
        print(f"\nFailed to write test log: {e}")
