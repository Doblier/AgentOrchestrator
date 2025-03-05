# AORBIT Enterprise Security Framework

A comprehensive, enterprise-grade security framework designed specifically for financial applications and AI agent orchestration.

## Overview

The AORBIT Enterprise Security Framework provides robust security features that meet the strict requirements of financial institutions:

- **Role-Based Access Control (RBAC)**: Fine-grained permission management with hierarchical roles
- **Comprehensive Audit Logging**: Immutable audit trail for all system activities with compliance reporting
- **Data Encryption**: Both at-rest and in-transit encryption for sensitive financial data
- **API Key Management**: Enhanced API keys with role assignments and IP restrictions

## Components

### RBAC System (`rbac.py`)

The RBAC system provides:

- Hierarchical roles with inheritance
- Fine-grained permissions
- Resource-specific access controls
- Default roles for common use cases

### Audit Logging (`audit.py`)

The audit logging system includes:

- Comprehensive event tracking
- Immutable log storage
- Advanced search capabilities
- Compliance reporting
- Critical event alerting

### Data Encryption (`encryption.py`)

The encryption module provides:

- Field-level encryption for sensitive data
- Support for structured data encryption
- Key management utilities
- PII data masking

### Security Integration (`integration.py`)

The integration module connects all security components:

- Middleware for request processing
- Dependency functions for FastAPI routes
- Application startup/shutdown hooks

## Configuration

The security framework is configured through environment variables in your `.env` file:

```
# Enterprise Security Framework
SECURITY_ENABLED=true                 # Master switch for enhanced security features
RBAC_ENABLED=true                     # Enable Role-Based Access Control
AUDIT_ENABLED=true                    # Enable comprehensive audit logging
ENCRYPTION_ENABLED=true               # Enable data encryption features

# Encryption Configuration
# ENCRYPTION_KEY=                     # Base64 encoded 32-byte key for encryption

# RBAC Configuration
RBAC_ADMIN_KEY=aorbit-admin-key       # Default admin API key
RBAC_DEFAULT_ROLE=read_only           # Default role for new API keys

# Audit Configuration
AUDIT_RETENTION_DAYS=90               # Number of days to retain audit logs
AUDIT_COMPLIANCE_MODE=true            # Enables stricter compliance features
```

## Usage Examples

### Requiring Permissions on a Route

```python
from agentorchestrator.security.integration import security

@router.get("/financial-data/{account_id}")
async def get_financial_data(
    account_id: str,
    permission: dict = Depends(security.require_permission("FINANCE_READ"))
):
    # Process the request with guaranteed permission check
    return {"data": "sensitive financial information"}
```

### Logging Audit Events

```python
from agentorchestrator.security.audit import audit_logger

# Log a financial transaction event
audit_logger.log_event(
    event_type=AuditEventType.FINANCIAL,
    user_id="user123",
    resource_type="account",
    resource_id="acct_456",
    action="transfer",
    status="completed",
    message="Transferred $1000 to external account",
    metadata={"amount": 1000, "destination": "acct_789"}
)
```

### Encrypting Sensitive Data

```python
from agentorchestrator.security.encryption import data_protection

# Encrypt sensitive fields in a dictionary
data = {
    "account_number": "1234567890",
    "social_security": "123-45-6789",
    "name": "John Doe",
    "balance": 10000
}

# Encrypt specific fields
protected_data = data_protection.encrypt_fields(
    data, 
    sensitive_fields=["account_number", "social_security"]
)
```

## Security Best Practices

1. **Production Deployments**: Always set a persistent `ENCRYPTION_KEY` in production
2. **API Keys**: Rotate API keys regularly and use the most restrictive roles possible
3. **Audit Logs**: Monitor audit logs for suspicious activities
4. **Regular Reviews**: Conduct periodic reviews of roles and permissions
5. **Testing**: Include security tests in your CI/CD pipeline 