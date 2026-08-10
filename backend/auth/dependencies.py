"""backend/auth/dependencies.py — FastAPI RBAC dependencies.

Enforces role-based access controls for backend routes.
Extracts user identity and role from request headers/auth tokens.
"""
from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from backend.security.rbac import UserContext, UserRole, Permission, ROLE_PERMISSIONS

async def get_current_user(
    x_user_name: Optional[str] = Header(None, alias="X-User-Name"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role")
) -> UserContext:
    """Extracts user information from the HTTP headers."""
    # Default to developer if headers are missing for local simplicity, or error out
    username = x_user_name or "anonymous"
    role_str = x_user_role or "developer"

    try:
        role = UserRole(role_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role_str}"
        )

    return UserContext(username=username, role=role)

def require_permission(required_permission: Permission):
    """Enforces that the current authenticated user has a specific permission."""
    async def dependency(user: UserContext = Depends(get_current_user)):
        if not user.has_permission(required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Requires {required_permission.value}"
            )
        return user
    return dependency

def require_role(required_role: UserRole):
    """Enforces that the current authenticated user has a specific role."""
    async def dependency(user: UserContext = Depends(get_current_user)):
        if not user.is_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Requires role {required_role.value}"
            )
        return user
    return dependency
