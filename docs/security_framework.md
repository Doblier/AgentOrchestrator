# AORBIT Enterprise Security Framework

AORBIT includes a comprehensive enterprise-grade security framework specifically designed for financial applications and sensitive data processing. This document provides an overview of the security features and how to use them.

## Core Components

The security framework consists of three main components:

### 1. Role-Based Access Control (RBAC)

The RBAC system provides fine-grained permission management with hierarchical roles:

- **Permissions**: Granular permissions for different operations (read, write, execute, etc.)
- **Roles**: Collections of permissions that can be assigned to API keys
- **Resources**: Protected items with specific permissions
- **Hierarchical Inheritance**: Roles can inherit permissions from parent roles
- **API Key Management**: Enhanced API keys with role assignments and IP whitelisting

### 2. Audit Logging

The audit logging system creates an immutable trail of all significant system activities:

- **Comprehensive Event Tracking**: All security-related events are logged
- **Immutable Logs**: Logs cannot be altered once created
- **Advanced Search**: Query logs by various parameters (user, time, event type)
- **Compliance Reporting**: Export logs in formats suitable for compliance audit
- **Critical Event Alerting**: Configure alerts for important security events

### 3. Data Encryption

The encryption module secures sensitive data:

- **Field-Level Encryption**: Encrypt specific fields in data structures
- **At-Rest Encryption**: Securely store sensitive data
- **In-Transit Protection**: Ensure data is protected during transfer
- **Key Management**: Secure generation and storage of encryption keys
- **PII Protection**: Automatically identify and mask personally identifiable information

## Configuration

Enable and configure the security framework through environment variables in your `.env` file:

```
# Security Framework Master Switch
SECURITY_ENABLED=true

# Component-Specific Toggles
RBAC_ENABLED=true
AUDIT_ENABLED=true
ENCRYPTION_ENABLED=true

# Encryption Configuration
ENCRYPTION_KEY=your-secure-key-here  # Base64-encoded 32-byte key

# RBAC Configuration
RBAC_ADMIN_KEY=your-admin-key
RBAC_DEFAULT_ROLE=read_only

# Audit Configuration
AUDIT_RETENTION_DAYS=90
AUDIT_COMPLIANCE_MODE=true
```

## Using the Security Framework in Your Code

### Requiring Permissions for API Routes

```python
from fastapi import Depends
from agentorchestrator.security.integration import get_security

@router.get("/financial-data")
async def get_financial_data(
    permission = Depends(get_security().require_permission("FINANCE_READ"))
):
    # This route is protected and requires the FINANCE_READ permission
    return {"data": "Sensitive financial information"}
```

### Logging Security Events

```python
from agentorchestrator.security.audit import log_api_request, AuditEventType

# Log a financial transaction event
await log_api_request(
    event_type=AuditEventType.FINANCE_TRANSACTION,
    action="transfer_funds",
    status="success",
    message="Transferred $1000 to external account",
    user_id="user123",
    resource_type="account",
    resource_id="acct_456",
    metadata={"amount": 1000, "destination": "acct_789"}
)
```

### Encrypting Sensitive Data

```python
from agentorchestrator.security.encryption import data_protection

# Encrypt sensitive fields in structured data
user_data = {
    "name": "John Doe",
    "email": "john@example.com",
    "ssn": "123-45-6789",
    "account_number": "1234567890"
}

# Encrypt only the sensitive fields
protected_data = data_protection.encrypt_sensitive_data(
    user_data, 
    sensitive_fields=["ssn", "account_number"]
)

# The result will have encrypted values for sensitive fields
# {"name": "John Doe", "email": "john@example.com", "ssn": "<encrypted>", "account_number": "<encrypted>"}
```

## Best Practices

### Production Security Checklist

1. **Set a Persistent Encryption Key**: Always set `ENCRYPTION_KEY` in production to avoid data loss
2. **Store Keys Securely**: Use a secure vault or key management service
3. **Rotate API Keys Regularly**: Establish a rotation schedule for API keys
4. **Least Privilege Principle**: Assign the minimum necessary permissions
5. **Audit Log Monitoring**: Regularly review audit logs for suspicious activities
6. **IP Whitelisting**: Restrict API access to trusted IP addresses
7. **Enable MFA**: Supplement API key authentication with multi-factor where possible
8. **Backup Strategy**: Regularly backup configuration and critical data
9. **Security Testing**: Include security tests in your CI/CD pipeline
10. **Updates**: Keep dependencies up-to-date with security patches

### Security Recommendations for Financial Applications

1. **Data Classification**: Classify data by sensitivity level
2. **Regulatory Compliance**: Ensure alignment with relevant regulations (GDPR, CCPA, PCI DSS)
3. **Transaction Logging**: Log all financial transactions in detail
4. **Approval Workflows**: Implement multi-level approvals for sensitive operations
5. **Rate Limiting**: Apply strict rate limits to prevent abuse
6. **Alerts**: Set up real-time alerts for suspicious activities
7. **Penetration Testing**: Conduct regular security assessments

## Extending the Security Framework

The security framework is designed to be extensible. To add custom security features:

1. **Custom Permissions**: Extend the Permission enum in rbac.py
2. **Custom Audit Events**: Add event types to AuditEventType enum
3. **Custom Security Rules**: Implement in the middleware or as dependencies
4. **Additional Encryption**: Add specialized encryption methods to EncryptionManager

For detailed implementation guidance, refer to the code documentation in the `agentorchestrator/security` directory. 