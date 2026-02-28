"""HTTP client management for Sonoplay."""

import aiohttp
from typing import Optional


class HttpClient:
    """Global HTTP client session manager.
    
    Usage:
        await http_client.start()
        response = await http_client.session.get(url)
        await http_client.stop()
    """
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def session(self) -> aiohttp.ClientSession:
        """Get the current HTTP session.
        
        Raises:
            RuntimeError: If session not started
        """
        if self._session is None:
            raise RuntimeError("HTTP session not started. Call start() first.")
        return self._session
    
    async def start(self, timeout_total: float = 10.0, timeout_connect: float = 5.0) -> None:
        """Start the HTTP session with configured timeouts."""
        if self._session is not None:
            return
        
        timeout = aiohttp.ClientTimeout(
            total=timeout_total,
            connect=timeout_connect
        )
        self._session = aiohttp.ClientSession(timeout=timeout)
    
    async def stop(self) -> None:
        """Close the HTTP session."""
        if self._session is not None:
            await self._session.close()
            self._session = None


# Global singleton - matches current g.http pattern
http_client = HttpClient()
