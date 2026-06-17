"""
Shared dependency container.

server.py populates these attributes on startup. Route modules import this
file and read the (mutable) attributes — avoids circular imports while still
giving every router access to the singletons.
"""

from typing import Optional, Callable

# Database handle (set in server.py at import time)
db = None  # type: ignore

# Service singletons (set in startup_chat_and_location)
outfit_generator = None  # type: ignore
affiliate_engine = None  # type: ignore
stripe_connect_provider = None  # type: ignore
paypal_payouts_provider = None  # type: ignore
fraud_service = None  # type: ignore

# Auth helper (assigned in server.py once defined)
get_current_user: Optional[Callable] = None
