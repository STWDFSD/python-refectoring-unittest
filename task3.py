from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from logging import getLogger
from typing_extensions import TypedDict

# Initialize logger for capturing debug and error information
logger = getLogger(__name__)

# Define a TypedDict to provide structure and type hints for user data
class UserData(TypedDict):
    id: str
    name: str
    email: str
    status: str
    type: str
    transactions: List[Dict[str, float]]
    login_count: int
    premium: bool

# Define a dataclass for processed user information that will be returned after processing
@dataclass
class ProcessedUser:
    id: str
    name: str
    email: str
    score: float

def validate_item(item: Optional[dict]) -> bool:
    """Validate the structure and types of the user data item.
    
    Args:
        item: Dictionary representing user data.
        
    Returns:
        bool: True if the item is valid, False otherwise.
    """
    if item is None:
        return False
        
    # Define required fields for validation
    required_fields = {"id", "name", "email", "status", "type", "transactions", "login_count", "premium"}
    
    # Check that all required fields are present
    if not all(field in item for field in required_fields):
        return False
        
    # Validate the type of each field
    try:
        return (isinstance(item["id"], str) and
                isinstance(item["name"], str) and
                isinstance(item["email"], str) and
                isinstance(item["status"], str) and
                isinstance(item["type"], str) and
                isinstance(item["transactions"], list) and
                isinstance(item["login_count"], int) and
                isinstance(item["premium"], bool))
    except Exception:
        return False

def calculate_score(item: UserData) -> float:
    """Calculate user score based on transactions, login count, and premium status.
    
    Args:
        item: User data dictionary containing relevant scoring fields
        
    Returns:
        float: Calculated score for the user
    """
    try:
        score = 0.0
        
        # Calculate transaction score by summing amounts from transactions
        if 'transactions' in item:
            score += sum(t['amount'] for t in item['transactions'] if 'amount' in t)
        
        # Add login bonus (2 points per login)
        score += item.get('login_count', 0) * 2
            
        # Apply premium multiplier (1.5x if premium)
        if item.get('premium', False):
            score *= 1.5
            
        return score
    except Exception as e:
        logger.error(f"Error calculating score for user {item.get('id')}: {str(e)}")
        return 0.0

def process_single_item(item: Optional[UserData]) -> Optional[ProcessedUser]:
    """Process a single user item to extract relevant information and calculate score.
    
    Args:
        item: User data item to be processed.
        
    Returns:
        Optional[ProcessedUser]: Processed user object or None if invalid.
    """
    if item is None:
        return None

    try:
        # Validate the user data item structure and types
        if not validate_item(item):
            logger.warning(f"Invalid item format: {item.get('id', 'unknown')}")
            return None

        # Ensure the user is both active and of type 'user'
        if item['status'] != 'active' or item['type'] != 'user':
            return None
        
        # Calculate user score
        score = calculate_score(item)
        if score <= 50:
            return None  # Exclude users with a score of 50 or lower
        
        # Return the processed user with transformed name and email for consistency
        return ProcessedUser(
            id=item['id'],
            name=item['name'].upper(),  # Normalize name to uppercase
            email=item['email'].lower(),  # Normalize email to lowercase
            score=score
        )
    except Exception as e:
        logger.error(f"Error processing item {item.get('id')}: {str(e)}")
        return None

def process_large_dataset(data_list: List[Optional[dict]]) -> List[str]:
    """Process a large dataset of user data in parallel to improve efficiency.
    
    Args:
        data_list: List of user data items to be processed.
        
    Returns:
        List[str]: List of formatted strings representing processed users.
    """
    try:
        with ThreadPoolExecutor() as executor:
            # Filter out None values before processing to avoid unnecessary computation
            filtered_data = [item for item in data_list if item is not None]
            processed_items = filter(None, executor.map(process_single_item, filtered_data))
        
        # Sort processed users by score in descending order and generate report
        sorted_results = sorted(processed_items, key=lambda x: x.score, reverse=True)
        return [f"User {result.name}: {result.score}" for result in sorted_results]
    except Exception as e:
        logger.error(f"Error processing dataset: {str(e)}")
        return []