"""
Shared data schemas for QualGent Backend Coding Challenge

This module defines the common data structures used across
the CLI tool and backend service.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobTarget(Enum):
    """Job target enumeration"""
    EMULATOR = "emulator"
    DEVICE = "device"
    BROWSERSTACK = "browserstack"


class JobPriority(Enum):
    """Job priority enumeration"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class JobPayload:
    """Job submission payload schema"""
    org_id: str
    app_version_id: str
    test_path: str
    target: JobTarget = JobTarget.EMULATOR
    priority: JobPriority = JobPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "org_id": self.org_id,
            "app_version_id": self.app_version_id,
            "test_path": self.test_path,
            "target": self.target.value,
            "priority": self.priority.value,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobPayload':
        """Create from dictionary"""
        return cls(
            org_id=data["org_id"],
            app_version_id=data["app_version_id"],
            test_path=data["test_path"],
            target=JobTarget(data.get("target", "emulator")),
            priority=JobPriority(data.get("priority", "normal")),
            metadata=data.get("metadata", {})
        )


@dataclass
class Job:
    """Complete job record"""
    job_id: str
    payload: JobPayload
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "job_id": self.job_id,
            "payload": self.payload.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "worker_id": self.worker_id,
            "result": self.result,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }


@dataclass
class JobGroup:
    """Group of jobs sharing the same app_version_id"""
    group_id: str
    org_id: str
    app_version_id: str
    jobs: List[str] = field(default_factory=list)  # job_ids
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    assigned_worker: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "group_id": self.group_id,
            "org_id": self.org_id,
            "app_version_id": self.app_version_id,
            "jobs": self.jobs,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "assigned_worker": self.assigned_worker
        }


@dataclass
class Worker:
    """Worker/Agent representation"""
    worker_id: str
    name: str
    target_types: List[JobTarget]
    status: str = "idle"  # idle, busy, offline
    current_jobs: List[str] = field(default_factory=list)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "worker_id": self.worker_id,
            "name": self.name,
            "target_types": [t.value for t in self.target_types],
            "status": self.status,
            "current_jobs": self.current_jobs,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "metadata": self.metadata
        }


def generate_job_id() -> str:
    """Generate a unique job ID"""
    return str(uuid.uuid4())


def generate_group_id() -> str:
    """Generate a unique group ID"""
    return f"group-{str(uuid.uuid4())[:8]}"


def generate_worker_id() -> str:
    """Generate a unique worker ID"""
    return f"worker-{str(uuid.uuid4())[:8]}" 