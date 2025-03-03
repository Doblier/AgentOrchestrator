"""
AORBIT Security Manager CLI

This module provides a command-line interface for managing security settings
in AORBIT, including API keys, roles, and permissions.
"""

import os
import sys
import uuid
import json
import click
import logging
import redis.asyncio as redis
from typing import List, Optional, Dict, Any
import asyncio
import base64
import secrets
import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('aorbit.security.cli')


@click.group()
def security():
    """
    Manage AORBIT security settings, API keys, roles, and permissions.
    """
    pass


@security.command('generate-key')
@click.option('--role', '-r', required=True, help='Role to assign to this API key')
@click.option('--name', '-n', required=True, help='Name/description for this API key')
@click.option('--expires', '-e', type=int, default=0, help='Days until expiration (0 = no expiration)')
@click.option('--ip-whitelist', '-i', multiple=True, help='IP addresses allowed to use this key')
@click.option('--redis-url', '-u', default=None, help='Redis URL (defaults to REDIS_URL env var)')
def generate_api_key(role: str, name: str, expires: int, ip_whitelist: List[str], redis_url: Optional[str]):
    """
    Generate a new API key and assign it to a role.
    """
    # Connect to Redis
    redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    async def _generate_key():
        try:
            r = redis.from_url(redis_url)
            await r.ping()
            
            # Generate a secure random API key
            key_bytes = secrets.token_bytes(24)
            prefix = "aorbit"
            key = f"{prefix}_{base64.urlsafe_b64encode(key_bytes).decode('utf-8')}"
            
            # Set expiration date if provided
            expiration = None
            if expires > 0:
                expiration = datetime.datetime.now() + datetime.timedelta(days=expires)
                expiration_str = expiration.isoformat()
            else:
                expiration_str = "never"
            
            # Create API key metadata
            metadata = {
                "name": name,
                "role": role,
                "created": datetime.datetime.now().isoformat(),
                "expires": expiration_str,
                "ip_whitelist": list(ip_whitelist) if ip_whitelist else []
            }
            
            # Store API key in Redis
            await r.set(f"apikey:{key}", role)
            await r.set(f"apikey:{key}:metadata", json.dumps(metadata))
            
            # If this role doesn't exist yet, create it
            role_exists = await r.exists(f"role:{role}")
            if not role_exists:
                await r.sadd("roles", role)
                logger.info(f"Created new role: {role}")
            
            # Display the generated key
            click.echo("\n🔐 API Key Generated Successfully 🔐\n")
            click.echo(f"API Key: {key}")
            click.echo(f"Role: {role}")
            click.echo(f"Name: {name}")
            click.echo(f"Expires: {expiration_str}")
            click.echo(f"IP Whitelist: {', '.join(ip_whitelist) if ip_whitelist else 'None (all IPs allowed)'}")
            click.echo("\n⚠️  IMPORTANT: Store this key securely. It will not be shown again. ⚠️\n")
            
            await r.close()
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            click.echo(f"Error connecting to Redis: {e}", err=True)
            return False
    
    if asyncio.run(_generate_key()):
        sys.exit(0)
    else:
        sys.exit(1)


@security.command('list-keys')
@click.option('--redis-url', '-u', default=None, help='Redis URL (defaults to REDIS_URL env var)')
def list_api_keys(redis_url: Optional[str]):
    """
    List all API keys (shows metadata only, not the actual keys).
    """
    # Connect to Redis
    redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    async def _list_keys():
        try:
            r = redis.from_url(redis_url)
            await r.ping()
            
            # Get all API keys (pattern match on prefix)
            keys = await r.keys("apikey:*:metadata")
            
            if not keys:
                click.echo("No API keys found.")
                await r.close()
                return True
            
            click.echo("\n🔑 API Keys 🔑\n")
            for key in keys:
                key_id = key.decode('utf-8').split(':')[1]
                metadata_str = await r.get(key)
                if metadata_str:
                    metadata = json.loads(metadata_str)
                    click.echo(f"Key ID: {key_id}")
                    click.echo(f"  Name: {metadata.get('name', 'Unknown')}")
                    click.echo(f"  Role: {metadata.get('role', 'Unknown')}")
                    click.echo(f"  Created: {metadata.get('created', 'Unknown')}")
                    click.echo(f"  Expires: {metadata.get('expires', 'Unknown')}")
                    click.echo(f"  IP Whitelist: {', '.join(metadata.get('ip_whitelist', [])) or 'None'}")
                    click.echo("")
            
            await r.close()
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            click.echo(f"Error connecting to Redis: {e}", err=True)
            return False
    
    if asyncio.run(_list_keys()):
        sys.exit(0)
    else:
        sys.exit(1)


@security.command('revoke-key')
@click.argument('key_id')
@click.option('--redis-url', '-u', default=None, help='Redis URL (defaults to REDIS_URL env var)')
def revoke_api_key(key_id: str, redis_url: Optional[str]):
    """
    Revoke an API key by its ID.
    """
    # Connect to Redis
    redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    async def _revoke_key():
        try:
            r = redis.from_url(redis_url)
            await r.ping()
            
            # Check if key exists
            key_exists = await r.exists(f"apikey:{key_id}")
            if not key_exists:
                click.echo(f"API key not found: {key_id}", err=True)
                await r.close()
                return False
            
            # Delete the key and its metadata
            await r.delete(f"apikey:{key_id}")
            await r.delete(f"apikey:{key_id}:metadata")
            
            click.echo(f"API key successfully revoked: {key_id}")
            await r.close()
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            click.echo(f"Error connecting to Redis: {e}", err=True)
            return False
    
    if asyncio.run(_revoke_key()):
        sys.exit(0)
    else:
        sys.exit(1)


@security.command('assign-permission')
@click.argument('role')
@click.argument('permission')
@click.option('--redis-url', '-u', default=None, help='Redis URL (defaults to REDIS_URL env var)')
def assign_permission(role: str, permission: str, redis_url: Optional[str]):
    """
    Assign a permission to a role.
    """
    # Connect to Redis
    redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    async def _assign_permission():
        try:
            r = redis.from_url(redis_url)
            await r.ping()
            
            # Check if role exists
            role_exists = await r.sismember("roles", role)
            if not role_exists:
                click.echo(f"Role not found: {role}", err=True)
                click.echo("Creating new role...")
                await r.sadd("roles", role)
            
            # Assign permission to role
            await r.sadd(f"role:{role}:permissions", permission)
            
            click.echo(f"Permission '{permission}' assigned to role '{role}'")
            await r.close()
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            click.echo(f"Error connecting to Redis: {e}", err=True)
            return False
    
    if asyncio.run(_assign_permission()):
        sys.exit(0)
    else:
        sys.exit(1)


@security.command('list-roles')
@click.option('--redis-url', '-u', default=None, help='Redis URL (defaults to REDIS_URL env var)')
def list_roles(redis_url: Optional[str]):
    """
    List all roles and their permissions.
    """
    # Connect to Redis
    redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    async def _list_roles():
        try:
            r = redis.from_url(redis_url)
            await r.ping()
            
            # Get all roles
            roles = await r.smembers("roles")
            
            if not roles:
                click.echo("No roles found.")
                await r.close()
                return True
            
            click.echo("\n👥 Roles and Permissions 👥\n")
            for role in roles:
                role_name = role.decode('utf-8')
                click.echo(f"Role: {role_name}")
                
                # Get permissions for this role
                permissions = await r.smembers(f"role:{role_name}:permissions")
                if permissions:
                    click.echo("  Permissions:")
                    for perm in permissions:
                        click.echo(f"    - {perm.decode('utf-8')}")
                else:
                    click.echo("  Permissions: None")
                
                click.echo("")
            
            await r.close()
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            click.echo(f"Error connecting to Redis: {e}", err=True)
            return False
    
    if asyncio.run(_list_roles()):
        sys.exit(0)
    else:
        sys.exit(1)


@security.command('encrypt')
@click.argument('value')
@click.option('--key', '-k', default=None, help='Encryption key (defaults to ENCRYPTION_KEY env var)')
def encrypt_value(value: str, key: Optional[str]):
    """
    Encrypt a value using the configured encryption key.
    """
    from agentorchestrator.security.encryption import EncryptionManager
    
    # Get encryption key
    encryption_key = key or os.environ.get('ENCRYPTION_KEY')
    if not encryption_key:
        click.echo("Error: Encryption key not provided and ENCRYPTION_KEY environment variable not set", err=True)
        sys.exit(1)
    
    try:
        # Initialize encryption manager
        encryption_manager = EncryptionManager(encryption_key)
        
        # Encrypt the value
        encrypted = encryption_manager.encrypt(value)
        
        click.echo("\n🔒 Encrypted Value 🔒\n")
        click.echo(encrypted)
        click.echo("")
        
        sys.exit(0)
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        click.echo(f"Error encrypting value: {e}", err=True)
        sys.exit(1)


@security.command('decrypt')
@click.argument('value')
@click.option('--key', '-k', default=None, help='Encryption key (defaults to ENCRYPTION_KEY env var)')
def decrypt_value(value: str, key: Optional[str]):
    """
    Decrypt a value using the configured encryption key.
    """
    from agentorchestrator.security.encryption import EncryptionManager
    
    # Get encryption key
    encryption_key = key or os.environ.get('ENCRYPTION_KEY')
    if not encryption_key:
        click.echo("Error: Encryption key not provided and ENCRYPTION_KEY environment variable not set", err=True)
        sys.exit(1)
    
    try:
        # Initialize encryption manager
        encryption_manager = EncryptionManager(encryption_key)
        
        # Decrypt the value
        decrypted = encryption_manager.decrypt(value)
        
        click.echo("\n🔓 Decrypted Value 🔓\n")
        click.echo(decrypted)
        click.echo("")
        
        sys.exit(0)
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        click.echo(f"Error decrypting value: {e}", err=True)
        sys.exit(1)


@security.command('generate-key-file')
@click.argument('filename')
def generate_encryption_key_file(filename: str):
    """
    Generate a new encryption key and save it to a file.
    """
    try:
        # Generate a secure random key
        key_bytes = secrets.token_bytes(32)
        key = base64.b64encode(key_bytes).decode('utf-8')
        
        # Write the key to the file
        with open(filename, 'w') as f:
            f.write(key)
        
        click.echo(f"\n🔑 Encryption Key Generated 🔑\n")
        click.echo(f"Key saved to: {filename}")
        click.echo(f"To use this key, set ENCRYPTION_KEY={key} in your environment variables")
        click.echo("\n⚠️  IMPORTANT: Keep this key secure! Anyone with access to this key can decrypt your data. ⚠️\n")
        
        # Set appropriate permissions on the file (read/write for owner only)
        os.chmod(filename, 0o600)
        
        sys.exit(0)
    except Exception as e:
        logger.error(f"Key generation error: {e}")
        click.echo(f"Error generating encryption key: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    security() 