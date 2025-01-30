import os
import logging
from psycopg2.pool import SimpleConnectionPool

# Initialize the connection pool to None
db_pool = None

def initialize_db_pool():
    """Initialize the database connection pool.

    This function sets up a connection pool using environment variables 
    to configure the database connection parameters. It ensures that the 
    pool is initialized only once to avoid redundant connections.

    Environment Variables:
    - MINCONN: Minimum number of connections in the pool (default: 1)
    - MAXCONN: Maximum number of connections in the pool (default: 10)
    - DATABASE: Name of the database (default: 'mydatabase')
    - USER: Database username (default: 'user')
    - PASSWORD: Database user's password (default: 'password')
    - HOST: Database host address (default: 'localhost')
    """
    global db_pool
    if db_pool is None:
        db_pool = SimpleConnectionPool(
            minconn=int(os.getenv("MINCONN", 1)),
            maxconn=int(os.getenv("MAXCONN", 10)),
            dbname=os.getenv("DATABASE", "mydatabase"),
            user=os.getenv("USER", "user"),
            password=os.getenv("PASSWORD", "password"),
            host=os.getenv("HOST", "localhost")
        )

def get_db_connection():
    """Retrieve a database connection from the pool.

    This function checks if the connection pool is initialized, and 
    retrieves a connection and a cursor from the pool. In case of an error, 
    it logs the issue and returns None for both connection and cursor.

    Returns:
        tuple: A tuple containing the database connection and cursor, or (None, None) if an error occurs.
    """
    if db_pool is None:
        initialize_db_pool()
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        return conn, cur
    except Exception as e:
        logging.error(f"Error getting DB connection: {e}")
        return None, None

def fetch_user_data(user_id):
    """Fetch user data from the database based on user ID.

    This function retrieves user information from the 'users' table 
    using the provided user ID. It ensures proper connection management 
    and error handling, logging any issues encountered during the process.

    Args:
        user_id (int): The ID of the user whose data is to be fetched.

    Returns:
        tuple or None: User data as a tuple if found, or None if an error occurs or user not found.
    """
    conn = None
    cur = None
    try:
        conn, cur = get_db_connection()
        if not conn or not cur:
            return None
            
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        return result
    except Exception as e:
        logging.error(f"Error fetching user data: {str(e)}")
        return None
    finally:
        # Ensure proper closure of cursor and return connection to the pool
        if cur:
            try:
                cur.close()
            except Exception as e:
                logging.error(f"Error closing cursor: {str(e)}")
        if conn:
            try:
                db_pool.putconn(conn)
            except Exception as e:
                logging.error(f"Error returning connection to pool: {str(e)}")