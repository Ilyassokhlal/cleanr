"""Shared rate limiter — separate module so routers and main can both import it."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)