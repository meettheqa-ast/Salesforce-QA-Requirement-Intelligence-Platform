"""Pydantic DTOs for the tenants module public API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr

from .models import MemberRole, TenantTier


class TenantCreate(BaseModel):
    name: str
    tier: TenantTier = TenantTier.POOLED
    region: str = "us-east-1"


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    tier: str
    region: str
    status: str

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    sso_subject: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    sso_subject: str | None

    model_config = {"from_attributes": True}


class MembershipCreate(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: MemberRole = MemberRole.QA_ENGINEER


class MembershipOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str

    model_config = {"from_attributes": True}
