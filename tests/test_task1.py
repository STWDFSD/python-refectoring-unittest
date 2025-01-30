import pytest
from unittest.mock import Mock, patch
from task1 import get_db_connection, fetch_user_data

# Remove the first import of task1 functions


# Add this patch decorator to mock the SimpleConnectionPool before importing task1
@pytest.fixture(autouse=True)
def mock_db_pool_creation():
    """Mock the SimpleConnectionPool creation before importing task1"""
    with patch('psycopg2.pool.SimpleConnectionPool') as mock_pool:
        # Create a mock pool instance
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        yield mock_pool_instance

# Keep only one import of task1 after the mock is set up

def test_get_db_connection(mock_db_pool):
    """Test get_db_connection to ensure it does not make a real DB connection."""
    conn, cur = get_db_connection()
    assert conn is not None
    assert cur is not None

# Mock data for testing
MOCK_USER_DATA = (1, "John Doe", "john@example.com")
MOCK_EMPTY_DATA = None

@pytest.fixture
def mock_db_pool():
    """Fixture to mock the database pool"""
    with patch('task1.db_pool') as mock_pool:
        yield mock_pool

@pytest.fixture
def mock_connection():
    """Fixture to create a mock database connection"""
    connection = Mock()
    cursor = Mock()
    connection.cursor.return_value = cursor
    return connection, cursor

# Happy Path Tests
def test_get_db_connection_success(mock_db_pool, mock_connection):
    """Test successful database connection"""
    connection, cursor = mock_connection
    mock_db_pool.getconn.return_value = connection
    
    conn, cur = get_db_connection()
    
    assert conn == connection
    assert cur == cursor
    mock_db_pool.getconn.assert_called_once()

def test_fetch_user_data_success(mock_db_pool, mock_connection):
    """Test successful user data fetch"""
    connection, cursor = mock_connection
    mock_db_pool.getconn.return_value = connection
    cursor.fetchone.return_value = MOCK_USER_DATA
    
    result = fetch_user_data(1)
    
    assert result == MOCK_USER_DATA
    cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = %s", (1,))
    cursor.close.assert_called_once()
    mock_db_pool.putconn.assert_called_once_with(connection)

# Edge Cases
def test_fetch_user_data_not_found(mock_db_pool, mock_connection):
    """Test fetching non-existent user"""
    connection, cursor = mock_connection
    mock_db_pool.getconn.return_value = connection
    cursor.fetchone.return_value = None
    
    result = fetch_user_data(999)
    
    assert result is None
    cursor.execute.assert_called_once()
    cursor.close.assert_called_once()

def test_fetch_user_data_with_zero_id(mock_db_pool, mock_connection):
    """Test fetching user with ID 0"""
    connection, cursor = mock_connection
    mock_db_pool.getconn.return_value = connection
    
    result = fetch_user_data(0)
    
    cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = %s", (0,))

def test_fetch_user_data_with_negative_id(mock_db_pool, mock_connection):
    """Test fetching user with negative ID"""
    connection, cursor = mock_connection
    mock_db_pool.getconn.return_value = connection
    
    result = fetch_user_data(-1)
    
    cursor.execute.assert_called_once_with("SELECT * FROM users WHERE id = %s", (-1,))

# Error Conditions
def test_get_db_connection_failure(mock_db_pool):
    """Test database connection failure"""
    mock_db_pool.getconn.side_effect = Exception("Connection failed")
    
    conn, cur = get_db_connection()
    
    assert conn is None
    assert cur is None
    mock_db_pool.getconn.assert_called_once()

def test_fetch_user_data_no_connection(mock_db_pool):
    """Test fetch user data with no connection"""
    mock_db_pool.getconn.side_effect = Exception("Connection failed")
    
    result = fetch_user_data(1)
    
    assert result is None

def test_fetch_user_data_execution_error(mock_db_pool, mock_connection):
    """Test fetch user data with database execution error"""
    connection, cursor = mock_connection
    mock_db_pool.getconn.return_value = connection
    cursor.execute.side_effect = Exception("Query failed")
    cursor.fetchone.return_value = None
    
    result = fetch_user_data(1)
    
    assert result is None
    cursor.close.assert_called_once()
    mock_db_pool.putconn.assert_called_once_with(connection)

def test_fetch_user_data_cursor_close_error(mock_db_pool, mock_connection):
    """Test handling of cursor close error"""
    connection, cursor = mock_connection
    mock_db_pool.getconn.return_value = connection
    cursor.close.side_effect = Exception("Close failed")
    cursor.fetchone.return_value = None
    
    result = fetch_user_data(1)
    
    assert result is None
    mock_db_pool.putconn.assert_called_once_with(connection)

# Performance Tests
@pytest.mark.benchmark
def test_fetch_user_data_performance(mock_db_pool, mock_connection, benchmark):
    """Test performance of fetch_user_data"""
    connection, cursor = mock_connection
    mock_db_pool.getconn.return_value = connection
    cursor.fetchone.return_value = MOCK_USER_DATA
    
    def run_fetch():
        return fetch_user_data(1)
    
    result = benchmark(run_fetch)
    assert result == MOCK_USER_DATA

# Connection Pool Tests
def test_connection_pool_reuse(mock_db_pool, mock_connection):
    """Test that connections are properly reused"""
    connection, cursor = mock_connection
    mock_db_pool.getconn.return_value = connection
    
    # Make multiple calls
    for _ in range(3):
        result = fetch_user_data(1)
        
    # Should have gotten connection 3 times
    assert mock_db_pool.getconn.call_count == 3
    # Should have returned connection 3 times
    assert mock_db_pool.putconn.call_count == 3