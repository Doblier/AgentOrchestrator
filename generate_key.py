import base64
import json
import secrets

import redis

# Generate new API key
key = f"aorbit_{base64.urlsafe_b64encode(secrets.token_bytes(24)).decode().rstrip('=')}"

# Connect to Redis
r = redis.Redis(host="localhost", port=6379, db=0)

# Create API key data
api_key_data = {
    "key": key,
    "name": "new_key",
    "roles": ["read", "write"],
    "rate_limit": 100,
}

# Store in Redis
r.hset("api_keys", key, json.dumps(api_key_data))

print(f"Generated API key: {key}")
