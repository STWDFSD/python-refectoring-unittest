from functools import wraps
import asyncio
import aiohttp
import asyncpg
from typing import Dict, Any, Optional
import redis
from ratelimit import limits, sleep_and_retry
import backoff
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration from environment variables
DB_CONFIG = {
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '123456'),
    'database': os.getenv('DB_NAME', 'testtask'),
    'host': os.getenv('DB_HOST', 'localhost')
}

# Configure Redis for caching
redis_client = redis.Redis(host='localhost', port=6379, db=0)
CACHE_TTL = 300  # Time-to-live for cache entries (5 minutes)
CALLS_PER_MINUTE = 60  # Rate limit for API calls

class APIError(Exception):
    """Base exception for API related errors, facilitating error handling."""
    pass

class RateLimitExceeded(APIError):
    """Raised when the rate limit for API requests is exceeded."""
    pass

class DatabaseError(APIError):
    """Raised when there's an issue with the database connection or operations."""
    pass

@sleep_and_retry  # Automatically retries the function if rate limit is exceeded
@limits(calls=CALLS_PER_MINUTE, period=60)  # Limits the number of calls made in a 60-second period
@backoff.on_exception(
    backoff.expo,  # Exponential backoff strategy for retries
    (aiohttp.ClientError, asyncio.TimeoutError),  # Exceptions to catch
    max_tries=3  # Retry up to 3 times
)
async def get_db_connection():
    """Get a database connection from the pool."""
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logging.error(f"Database connection failed: {str(e)}")
        raise DatabaseError(f"Database connection failed: {str(e)}")

async def process_api_request(user_id: int) -> Dict[str, Any]:
    """Handle API requests with enhanced features including caching and rate limiting."""
    cache_key = f"user:{user_id}"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return {"status": "success", "data": cached_data, "source": "cache"}

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"http://localhost:3000/users/{user_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    redis_client.setex(cache_key, CACHE_TTL, str(data))
                    await process_user_data(data)
                    await update_database(data)
                    return {"status": "success", "data": data, "source": "api"}
                else:
                    raise APIError(f"API request failed with status {response.status}")

    except aiohttp.ClientError as e:
        logging.error(f"API request failed: {str(e)}")
        raise APIError(f"API request failed: {str(e)}")
    except asyncio.TimeoutError:
        logging.error("API request timed out")
        raise APIError("Request timed out")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise APIError(f"Unexpected error: {str(e)}")

async def process_user_data(data: Dict[str, Any]) -> None:
    """Process user data asynchronously, potentially involving complex logic."""
    user_name = data['name']
    user_email = data['email']
    logging.info(f"Processing data for user: {user_name}")  # Log processing activity
    # Add async processing logic here, such as notifying other services or updating analytics

async def update_database(data: Dict[str, Any]) -> None:
    """Update user information in the database asynchronously."""
    try:
        conn = await get_db_connection()
        try:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE users
                    SET name = $1, email = $2
                    WHERE id = $3
                    """,
                    data['name'], data['email'], data['id']
                )
        finally:
            await conn.close()
    except Exception as e:
        logging.error(f"Database update failed: {str(e)}")
        raise APIError(f"Database update failed: {str(e)}")
