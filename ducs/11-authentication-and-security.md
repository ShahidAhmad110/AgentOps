# 11 — Authentication, Authorization & Security Specification

## Roles
At minimum:
- User
- Admin

## Requirements
- Authentication for protected platform access.
- Role-based access control.
- Normal users cannot access administrative functionality.
- Sensitive operations require authorization.
- Data access must be scoped to the authenticated user/organization as applicable.

## Secrets
Never hardcode:
- API keys
- Database passwords
- LLM credentials
- Secret keys
- Production URLs

Use environment variables and provide `.env.example`.

## Security Areas
Authentication, authorization, input validation, file validation, secure secrets, access control, audit logging and safe tool execution.
