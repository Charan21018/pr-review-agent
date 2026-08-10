"""backend/security/rbac.py — Role-based access control and user permission manager.

Defines roles and maps permissions required for endpoints like HITL queues,
economics dashboard, and configuration updates.
"""
from enum import Enum
from typing import Set, Dict, List, Optional
from pydantic import BaseModel

class UserRole(str, Enum):
    DEVELOPER = "developer"         # Can view reviews, request reviews
    REVIEWER = "reviewer"           # Can view and approve/reject HITL items
    SECURITY_ADMIN = "security_admin" # Can view all audits, configure sandbox/security settings
    SYSTEM = "system"               # Background processes and webhook handlers

class Permission(str, Enum):
    VIEW_REVIEW = "view_review"
    SUBMIT_REVIEW = "submit_review"
    APPROVE_HITL = "approve_hitl"
    VIEW_ECONOMICS = "view_economics"
    MANAGE_POLICY = "manage_policy"
    READ_AUDIT = "read_audit"

# Map roles to their specific set of permissions
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.DEVELOPER: {
        Permission.VIEW_REVIEW,
        Permission.SUBMIT_REVIEW,
    },
    UserRole.REVIEWER: {
        Permission.VIEW_REVIEW,
        Permission.SUBMIT_REVIEW,
        Permission.APPROVE_HITL,
        Permission.VIEW_ECONOMICS,
    },
    UserRole.SECURITY_ADMIN: {
        Permission.VIEW_REVIEW,
        Permission.SUBMIT_REVIEW,
        Permission.APPROVE_HITL,
        Permission.VIEW_ECONOMICS,
        Permission.MANAGE_POLICY,
        Permission.READ_AUDIT,
    },
    UserRole.SYSTEM: {
        Permission.VIEW_REVIEW,
        Permission.SUBMIT_REVIEW,
        Permission.APPROVE_HITL,
        Permission.VIEW_ECONOMICS,
        Permission.MANAGE_POLICY,
        Permission.READ_AUDIT,
    }
}

class UserContext(BaseModel):
    username: str
    role: UserRole

    def has_permission(self, permission: Permission) -> bool:
        permissions = ROLE_PERMISSIONS.get(self.role, set())
        return permission in permissions

    def is_role(self, role: UserRole) -> bool:
        return self.role == role
