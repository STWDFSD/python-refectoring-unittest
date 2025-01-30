import pytest
import math
import time
import sys
import logging
from concurrent.futures import ThreadPoolExecutor

from unittest.mock import patch, MagicMock
from task3 import (
    UserData,
    ProcessedUser,
    validate_item,
    calculate_score,
    process_single_item,
    process_large_dataset,
)


# Test data fixtures
@pytest.fixture
def valid_user_data() -> UserData:
    return {
        "id": "123",
        "name": "John Doe",
        "email": "john@example.com",
        "status": "active",
        "type": "user",
        "transactions": [{"amount": 100.0}, {"amount": 50.0}],
        "login_count": 10,
        "premium": True
    }

@pytest.fixture
def invalid_user_data() -> dict:
    return {
        "id": "456",
        "name": "Jane Doe",
        # missing email and other required fields
    }

# Test validation
def test_validate_item_valid(valid_user_data):
    assert validate_item(valid_user_data) is True

def test_validate_item_invalid(invalid_user_data):
    assert validate_item(invalid_user_data) is False

# Additional validation tests
def test_validate_item_empty_dict():
    assert validate_item({}) is False

def test_validate_item_none():
    assert validate_item(None) is False

def test_validate_item_invalid_types():
    invalid_data = {
        "id": 123,  # should be string
        "name": ["invalid"],  # should be string
        "email": None,  # should be string
        "status": "active",
        "type": "user",
        "transactions": "invalid",  # should be list
        "login_count": "10",  # should be int
        "premium": "true"  # should be bool
    }
    assert validate_item(invalid_data) is False

# Test score calculation
def test_calculate_score_full(valid_user_data):
    expected_score = (150.0 + 20.0) * 1.5  # (transactions + login_bonus) * premium
    assert calculate_score(valid_user_data) == expected_score

def test_calculate_score_no_transactions():
    user_data: UserData = {
        "id": "789",
        "name": "Alice",
        "email": "alice@example.com",
        "status": "active",
        "type": "user",
        "transactions": [],
        "login_count": 5,
        "premium": False
    }
    assert calculate_score(user_data) == 10.0  # just login bonus

def test_calculate_score_error():
    invalid_data = {"id": "error"}  # Will cause exception
    assert calculate_score(invalid_data) == 0.0

# Additional score calculation tests
def test_calculate_score_negative_values():
    user_data: UserData = {
        "id": "789",
        "name": "Alice",
        "email": "alice@example.com",
        "status": "active",
        "type": "user",
        "transactions": [{"amount": -100.0}],  # negative transaction
        "login_count": -5,  # negative login count
        "premium": True
    }
    expected_score = (-100.0 + -10.0) * 1.5  # (transactions + login_bonus) * premium
    assert calculate_score(user_data) == expected_score

# Test single item processing
def test_process_single_item_valid(valid_user_data):
    result = process_single_item(valid_user_data)
    assert isinstance(result, ProcessedUser)
    assert result.name == "JOHN DOE"
    assert result.email == "john@example.com"
    assert result.id == "123"

def test_process_single_item_invalid_status(valid_user_data):
    valid_user_data["status"] = "inactive"
    assert process_single_item(valid_user_data) is None

def test_process_single_item_invalid_type(valid_user_data):
    valid_user_data["type"] = "admin"
    assert process_single_item(valid_user_data) is None

def test_process_single_item_low_score(valid_user_data):
    valid_user_data["transactions"] = [{"amount": 10.0}]
    valid_user_data["login_count"] = 0
    assert process_single_item(valid_user_data) is None

# Additional edge cases for process_single_item
def test_process_single_item_max_values(valid_user_data):
    valid_user_data.update({
        "transactions": [{"amount": 1e6}],  # Use a large but finite number instead of inf
        "login_count": 999999999,
        "premium": True
    })
    result = process_single_item(valid_user_data)
    assert result is not None
    assert isinstance(result.score, float)
    assert not math.isinf(result.score)

def test_process_single_item_unicode_name(valid_user_data):
    valid_user_data["name"] = "José María 🌟"
    result = process_single_item(valid_user_data)
    assert result is not None
    assert result.name == "JOSÉ MARÍA 🌟"

# Test large dataset processing
def test_process_large_dataset():
    test_data = [
        {
            "id": "1",
            "name": "User1",
            "email": "user1@example.com",
            "status": "active",
            "type": "user",
            "transactions": [{"amount": 200.0}],
            "login_count": 5,
            "premium": True
        },
        {
            "id": "2",
            "name": "User2",
            "email": "user2@example.com",
            "status": "active",
            "type": "user",
            "transactions": [{"amount": 100.0}],
            "login_count": 3,
            "premium": False
        }
    ]
    
    result = process_large_dataset(test_data)
    assert len(result) == 2
    assert "USER1" in result[0]  # Higher score should be first
    assert "USER2" in result[1]

@patch('task3.ThreadPoolExecutor')
def test_process_large_dataset_parallel_processing(mock_executor):
    # Mock the ThreadPoolExecutor
    mock_executor_instance = MagicMock()
    mock_executor.return_value.__enter__.return_value = mock_executor_instance
    
    test_data = [{"id": "1", "name": "Test", "email": "test@example.com", 
                  "status": "active", "type": "user", "transactions": [], 
                  "login_count": 1, "premium": False}]
    
    process_large_dataset(test_data)
    
    # Verify that map was called on the executor
    assert mock_executor_instance.map.called

def test_process_large_dataset_empty():
    assert process_large_dataset([]) == []

def test_process_large_dataset_error():
    with patch('task3.ThreadPoolExecutor') as mock_executor:
        mock_executor.side_effect = Exception("Test error")
        assert process_large_dataset([{"invalid": "data"}]) == []

# Performance benchmarks
@pytest.mark.benchmark
def test_process_large_dataset_performance(benchmark):
    """Benchmark performance of processing large dataset"""
    # Generate test dataset
    large_dataset = [
        {
            "id": str(i),
            "name": f"User{i}",
            "email": f"user{i}@example.com",
            "status": "active",
            "type": "user",
            "transactions": [{"amount": 100.0}] * 10,
            "login_count": 5,
            "premium": i % 2 == 0
        }
        for i in range(1000)
    ]
    
    result = benchmark(process_large_dataset, large_dataset)
    assert len(result) == 1000

# Additional error cases for process_large_dataset
def test_process_large_dataset_mixed_errors(caplog):
    mixed_data = [
        {"id": "1", "name": "Valid", "email": "valid@example.com", "status": "active", "type": "user", "transactions": [], "login_count": 1, "premium": False},
        {"invalid": "data"},  # This is invalid and should be handled
        None,  # This is None and should be skipped
        {"id": "2", "name": "Also Valid", "email": "valid2@example.com", "status": "active", "type": "user", "transactions": [], "login_count": 1, "premium": False}
    ]

    caplog.set_level(logging.WARNING)
    result = process_large_dataset(mixed_data)

    # Check for warning in logs
    assert "Invalid item format" in caplog.text or "Error processing item" in caplog.text

    # Filter out None values after processing
    valid_results = [r for r in result if r is not None]
    assert len(valid_results) == 0  # Should only process valid items