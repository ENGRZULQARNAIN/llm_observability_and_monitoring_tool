from functools import lru_cache
from utils.auth_utils import AuthManager

@lru_cache()
def get_auth_manager():
    return AuthManager() 