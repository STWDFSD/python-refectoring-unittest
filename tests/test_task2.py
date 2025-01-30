import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from task2 import process_api_request, process_user_data, update_database, APIError
    
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_redis():
    with patch('task2.redis_client') as mock:
        yield mock

@pytest.fixture
def mock_aiohttp_session():
    class MockResponse:
        def __init__(self, status, data):
            self.status = status
            self._data = data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def json(self):
            return self._data

    class MockSession:
        def __init__(self, status=200, data=None):
            self.status = status
            self.data = data if data is not None else {"name": "Test User", "email": "test@example.com", "id": 1}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def get(self, url):
            return MockResponse(self.status, self.data)

    return MockSession

@pytest.fixture
async def mock_db_connection():
    """Fixture to mock database connection"""
    mock_conn = AsyncMock()
    mock_cur = AsyncMock()
    
    # Configure the cursor's execute method to return None
    mock_cur.execute.return_value = None
    
    # Make the connection return the cursor
    mock_conn.cursor.return_value = mock_cur
    
    # Configure the connection's commit and close methods
    mock_conn.commit.return_value = None
    mock_conn.close.return_value = None
    
    # Return as a tuple to match what get_db_connection returns
    return mock_conn, mock_cur

@pytest.fixture
async def mock_get_db_connection(mock_db_connection):
    """Fixture to mock get_db_connection function"""
    with patch('task2.get_db_connection', return_value=mock_db_connection):
        yield

# Happy Path Tests
@pytest.mark.asyncio
async def test_process_api_request_cache_hit(mock_redis):
    """Test successful cache hit"""
    cached_data = '{"name": "Cached User", "email": "cached@example.com"}'
    mock_redis.get.return_value = cached_data
    
    result = await process_api_request(1)
    
    assert result["status"] == "success"
    assert result["source"] == "cache"
    mock_redis.get.assert_called_once_with("user:1")

@pytest.fixture
async def mock_get_db_connection(mock_db_connection):
    """Fixture to mock get_db_connection function"""
    with patch('task2.get_db_connection', return_value=mock_db_connection):
        yield

@pytest.mark.asyncio
async def test_process_api_request_api_success(mock_redis, mock_aiohttp_session):
    """Test successful API call"""
    mock_redis.get.return_value = None
    
    # Create a proper async mock for the database connection
    class MockConnection(AsyncMock):
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, tb):
            return None
            
        def transaction(self):
            return self
    
    # Create and configure the mock connection
    mock_conn = MockConnection()
    mock_conn.execute = AsyncMock()
    mock_conn.close = AsyncMock()
    
    # Create an async mock for get_db_connection
    async def mock_get_db():
        return mock_conn
    
    with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session()), \
         patch('task2.get_db_connection', side_effect=mock_get_db):
        result = await process_api_request(1)
    
    assert result["status"] == "success"
    assert result["source"] == "api"
    assert "name" in result["data"]
    assert "email" in result["data"]
    
    # Verify the database calls
    mock_conn.execute.assert_called_once()
    mock_conn.close.assert_called_once()

# Edge Cases
@pytest.mark.asyncio
async def test_process_api_request_empty_response(mock_redis, mock_aiohttp_session):
    """Test API returning empty data"""
    mock_redis.get.return_value = None
    
    # Create a session instance with empty data
    empty_session = mock_aiohttp_session(status=200, data={})
    
    with patch('aiohttp.ClientSession', return_value=empty_session), \
         patch('task2.update_database'), \
         patch('task2.process_user_data'):  # Skip database operations to prevent null reference
        result = await process_api_request(1)
    
    assert result["status"] == "success"
    assert result["source"] == "api"
    assert result["data"] == {}

# Error Conditions
@pytest.mark.asyncio
async def test_process_api_request_api_error(mock_redis, mock_aiohttp_session):
    """Test API error handling"""
    mock_redis.get.return_value = None
    
    with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session(status=404, data=None)):
        with pytest.raises(APIError) as exc_info:
            await process_api_request(1)
    
    assert "API request failed with status 404" in str(exc_info.value)

@pytest.mark.asyncio
async def test_process_api_request_timeout(mock_redis):
    """Test timeout handling"""
    mock_redis.get.return_value = None
    
    with patch('aiohttp.ClientSession', side_effect=asyncio.TimeoutError):
        with pytest.raises(APIError) as exc_info:
            await process_api_request(1)
    
    assert "Request timed out" in str(exc_info.value)

# Process User Data Tests
@pytest.mark.asyncio
async def test_process_user_data_success():
    """Test successful user data processing"""
    test_data = {"name": "Test User", "email": "test@example.com"}
    with patch('logging.info') as mock_logging:
        await process_user_data(test_data)
        mock_logging.assert_called_once_with("Processing data for user: Test User")

# Database Update Tests
@pytest.mark.asyncio
async def test_update_database_success(mock_get_db_connection):
    """Test successful database update"""
    test_data = {"name": "Test User", "email": "test@example.com", "id": 1}
    await update_database(test_data)

@pytest.mark.asyncio
async def test_update_database_error():
    """Test database update error handling"""
    test_data = {"name": "Test User", "email": "test@example.com", "id": 1}
    
    # Create a mock that raises an exception when called
    mock_db_error = AsyncMock(side_effect=Exception("DB Error"))
    
    with patch('task2.get_db_connection', side_effect=mock_db_error):
        with pytest.raises(APIError) as exc_info:
            await update_database(test_data)
    
    assert "Database update failed" in str(exc_info.value)

# Performance Benchmark
@pytest.mark.benchmark
def test_api_request_performance(benchmark, mock_redis, mock_aiohttp_session):
    """Benchmark API request performance"""
    mock_redis.get.return_value = None
    
    async def run_request():
        with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session()), \
             patch('task2.update_database'), \
             patch('task2.process_user_data'):
            return await process_api_request(1)
    
    result = benchmark(lambda: asyncio.run(run_request()))
    assert result["status"] == "success"