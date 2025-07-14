"""
Job Store Implementation

This module provides an in-memory data store for jobs, job groups, and workers.
In a production environment, this would be backed by Redis or a database.
"""

import threading
from typing import Dict, List, Optional
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import JobStatus, JobTarget, Job, JobGroup, Worker


class JobStore:
    """In-memory store for jobs, groups, and workers"""
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.groups: Dict[str, JobGroup] = {}
        self.workers: Dict[str, Worker] = {}
        self._lock = threading.RLock()
    
    # Job operations
    def add_job(self, job: Job) -> None:
        """Add a new job to the store"""
        with self._lock:
            self.jobs[job.job_id] = job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        with self._lock:
            return self.jobs.get(job_id)
    
    def update_job(self, job: Job) -> None:
        """Update an existing job"""
        with self._lock:
            if job.job_id in self.jobs:
                self.jobs[job.job_id] = job
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                return True
            return False
    
    def list_jobs(self, org_id: Optional[str] = None, 
                  status: Optional[JobStatus] = None,
                  app_version_id: Optional[str] = None) -> List[Job]:
        """List jobs with optional filtering"""
        with self._lock:
            jobs = list(self.jobs.values())
            
            if org_id:
                jobs = [j for j in jobs if j.payload.org_id == org_id]
            
            if status:
                jobs = [j for j in jobs if j.status == status]
            
            if app_version_id:
                jobs = [j for j in jobs if j.payload.app_version_id == app_version_id]
            
            return jobs
    
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get all jobs with a specific status"""
        with self._lock:
            return [job for job in self.jobs.values() if job.status == status]
    
    def get_jobs_by_group(self, group_id: str) -> List[Job]:
        """Get all jobs in a specific group"""
        with self._lock:
            group = self.groups.get(group_id)
            if not group:
                return []
            
            return [self.jobs[job_id] for job_id in group.jobs if job_id in self.jobs]
    
    # Group operations
    def add_group(self, group: JobGroup) -> None:
        """Add a new job group"""
        with self._lock:
            self.groups[group.group_id] = group
    
    def get_group(self, group_id: str) -> Optional[JobGroup]:
        """Get a group by ID"""
        with self._lock:
            return self.groups.get(group_id)
    
    def update_group(self, group: JobGroup) -> None:
        """Update an existing group"""
        with self._lock:
            if group.group_id in self.groups:
                self.groups[group.group_id] = group
    
    def get_group_by_app_version(self, org_id: str, app_version_id: str) -> Optional[JobGroup]:
        """Get group for a specific org and app version"""
        with self._lock:
            for group in self.groups.values():
                if (group.org_id == org_id and 
                    group.app_version_id == app_version_id and
                    group.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING]):
                    return group
            return None
    
    def list_groups(self, org_id: Optional[str] = None) -> List[JobGroup]:
        """List job groups with optional filtering"""
        with self._lock:
            groups = list(self.groups.values())
            
            if org_id:
                groups = [g for g in groups if g.org_id == org_id]
            
            return groups
    
    def add_job_to_group(self, job_id: str, group_id: str) -> bool:
        """Add a job to an existing group"""
        with self._lock:
            group = self.groups.get(group_id)
            if group and job_id not in group.jobs:
                group.jobs.append(job_id)
                return True
            return False
    
    # Worker operations
    def add_worker(self, worker: Worker) -> None:
        """Add a new worker"""
        with self._lock:
            self.workers[worker.worker_id] = worker
    
    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get a worker by ID"""
        with self._lock:
            return self.workers.get(worker_id)
    
    def update_worker(self, worker: Worker) -> None:
        """Update an existing worker"""
        with self._lock:
            if worker.worker_id in self.workers:
                self.workers[worker.worker_id] = worker
    
    def list_workers(self, target_type: Optional[JobTarget] = None,
                     status: Optional[str] = None) -> List[Worker]:
        """List workers with optional filtering"""
        with self._lock:
            workers = list(self.workers.values())
            
            if target_type:
                workers = [w for w in workers if target_type in w.target_types]
            
            if status:
                workers = [w for w in workers if w.status == status]
            
            return workers
    
    def get_available_workers(self, target_type: JobTarget) -> List[Worker]:
        """Get workers that can handle a specific target type and are available"""
        with self._lock:
            available = []
            for worker in self.workers.values():
                if (target_type in worker.target_types and 
                    worker.status == "idle" and
                    len(worker.current_jobs) == 0):
                    available.append(worker)
            return available
    
    def assign_job_to_worker(self, job_id: str, worker_id: str) -> bool:
        """Assign a job to a worker"""
        with self._lock:
            worker = self.workers.get(worker_id)
            job = self.jobs.get(job_id)
            
            if worker and job:
                if job_id not in worker.current_jobs:
                    worker.current_jobs.append(job_id)
                    worker.status = "busy"
                job.worker_id = worker_id
                job.status = JobStatus.QUEUED
                job.updated_at = datetime.utcnow()
                return True
            return False
    
    def complete_job_for_worker(self, job_id: str, worker_id: str) -> bool:
        """Remove a completed job from worker's current jobs"""
        with self._lock:
            worker = self.workers.get(worker_id)
            
            if worker and job_id in worker.current_jobs:
                worker.current_jobs.remove(job_id)
                if len(worker.current_jobs) == 0:
                    worker.status = "idle"
                return True
            return False
    
    # Utility methods
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        with self._lock:
            stats = {
                "total_jobs": len(self.jobs),
                "pending": 0,
                "queued": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }
            
            for job in self.jobs.values():
                stats[job.status.value] += 1
            
            stats["total_groups"] = len(self.groups)
            stats["total_workers"] = len(self.workers)
            stats["idle_workers"] = len([w for w in self.workers.values() if w.status == "idle"])
            stats["busy_workers"] = len([w for w in self.workers.values() if w.status == "busy"])
            
            return stats
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed jobs"""
        with self._lock:
            cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
            jobs_to_remove = []
            
            for job_id, job in self.jobs.items():
                if (job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED] and
                    job.completed_at and job.completed_at.timestamp() < cutoff_time):
                    jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
            
            return len(jobs_to_remove) 