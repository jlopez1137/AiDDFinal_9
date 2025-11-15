"""Dataclass-style entity representations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from flask_login import UserMixin


@dataclass
class User(UserMixin):
    """User entity compatible with Flask-Login."""

    user_id: int
    name: str
    email: str
    password_hash: str
    role: str
    profile_image: Optional[str]
    department: Optional[str]
    created_at: datetime
    is_active: bool = True

    def get_id(self) -> str:
        return str(self.user_id)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_staff(self) -> bool:
        return self.role == "staff"

    def has_role(self, roles: Iterable[str]) -> bool:
        return self.role in set(roles)


@dataclass
class Resource:
    """Campus resource listing."""

    resource_id: int
    owner_id: int
    title: str
    description: str
    category: str
    location: str
    capacity: int
    images: Optional[str]
    availability_rules: Optional[str]
    requires_approval: bool
    status: str
    created_at: datetime
    average_rating: Optional[float] = None


@dataclass
class Booking:
    """Resource booking request."""

    booking_id: int
    resource_id: int
    requester_id: int
    start_datetime: datetime
    end_datetime: datetime
    status: str
    approval_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class Message:
    """A message exchanged between two parties regarding a resource or booking."""

    message_id: int
    thread_id: int
    sender_id: int
    receiver_id: int
    content: str
    timestamp: datetime


@dataclass
class Thread:
    """Discussion thread grouping related messages."""

    thread_id: int
    context_type: str
    context_id: Optional[int]
    created_by: int
    created_at: datetime


@dataclass
class Review:
    """Review for a resource."""

    review_id: int
    resource_id: int
    reviewer_id: int
    rating: int
    comment: str
    timestamp: datetime

