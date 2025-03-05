from typing import Optional
from redis.asyncio import Redis as RedisClient

__all__ = ['Redis']

class Redis:
    """A wrapper around the redis-py client for handling Redis operations."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """Initialize the Redis client.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
        """
        self.client = RedisClient(host=host, port=port, db=db)
    
    def pipeline(self):
        """Get a Redis pipeline for atomic operations.
        
        Returns:
            A Redis pipeline object
        """
        return self.client.pipeline()
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis.
        
        Args:
            key: The key to get
            
        Returns:
            The value if found, None otherwise
        """
        return await self.client.get(key)
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set a value in Redis.
        
        Args:
            key: The key to set
            value: The value to set
            expire: Optional expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        return await self.client.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> bool:
        """Delete a key from Redis.
        
        Args:
            key: The key to delete
            
        Returns:
            True if successful, False otherwise
        """
        return bool(await self.client.delete(key))
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        return bool(await self.client.exists(key))
    
    async def incr(self, key: str) -> int:
        """Increment a counter in Redis.
        
        Args:
            key: The key to increment
            
        Returns:
            The new value
        """
        return await self.client.incr(key)
    
    async def hset(self, name: str, key: str, value: str) -> bool:
        """Set a hash field in Redis.
        
        Args:
            name: The hash name
            key: The field name
            value: The field value
            
        Returns:
            True if successful, False otherwise
        """
        return bool(await self.client.hset(name, key, value))
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get a hash field from Redis.
        
        Args:
            name: The hash name
            key: The field name
            
        Returns:
            The field value if found, None otherwise
        """
        return await self.client.hget(name, key)
    
    async def sadd(self, name: str, value: str) -> bool:
        """Add a member to a set in Redis.
        
        Args:
            name: The set name
            value: The value to add
            
        Returns:
            True if successful, False otherwise
        """
        return bool(await self.client.sadd(name, value))
    
    async def sismember(self, name: str, value: str) -> bool:
        """Check if a value is a member of a set in Redis.
        
        Args:
            name: The set name
            value: The value to check
            
        Returns:
            True if the value is a member, False otherwise
        """
        return bool(await self.client.sismember(name, value))
    
    async def close(self) -> None:
        """Close the Redis connection."""
        await self.client.close() 