"""
Redis-backed Job Store Implementation

This module provides a Redis-backed data store for jobs, job groups, and workers.
It provides the same interface as the in-memory job store but with persistence.
"""

import json
import threading
from typing import Dict, List, Optional
from datetime import datetime
import redis
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import JobStatus, JobTarget, Job, JobGroup, Worker

logger = logging.getLogger(__name__)


class RedisJobStore:
    """Redis-backed store for jobs, groups, and workers"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis connection"""
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis.ping()
            logger.info(f"Connected to Redis at {redis_url}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        
        self._lock = threading.RLock()
        
        # Redis key prefixes
        self.JOB_PREFIX = "job:"
        self.GROUP_PREFIX = "group:"
        self.WORKER_PREFIX = "worker:"
        self.JOB_LIST = "jobs"
        self.GROUP_LIST = "groups"
        self.WORKER_LIST = "workers"
    
    def _serialize_job(self, job: Job) -> dict:
        """Serialize job object to Redis-compatible dict"""
        data = job.to_dict()
        # Convert datetime objects to ISO format strings
        for key in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if data.get(key):
                if isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
        
        # Convert complex objects to JSON strings
        serialized_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                serialized_data[key] = json.dumps(value)
            else:
                serialized_data[key] = str(value) if value is not None else ""
        
        return serialized_data
    
    def _deserialize_job(self, data: dict) -> Job:
        """Deserialize Redis dict to Job object"""
        from shared import JobPayload
        
        # Convert ISO format strings back to datetime objects
        for key in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        
        # Reconstruct JobPayload
        payload_data = data['payload']
        payload = JobPayload.from_dict(payload_data)
        
        # Create Job object
        job = Job(
            job_id=data['job_id'],
            payload=payload,
            status=JobStatus(data['status']),
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            worker_id=data.get('worker_id'),
            result=data.get('result'),
            error_message=data.get('error_message'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3)
        )
        return job
    
    def _serialize_group(self, group: JobGroup) -> dict:
        """Serialize group object to Redis-compatible dict"""
        data = group.to_dict()
        if isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        
        # Convert complex objects to JSON strings
        serialized_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                serialized_data[key] = json.dumps(value)
            else:
                serialized_data[key] = str(value) if value is not None else ""
        
        return serialized_data
    
    def _deserialize_group(self, data: dict) -> JobGroup:
        """Deserialize Redis dict to JobGroup object"""
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        group = JobGroup(
            group_id=data['group_id'],
            org_id=data['org_id'],
            app_version_id=data['app_version_id'],
            jobs=data['jobs'],
            status=JobStatus(data['status']),
            created_at=data['created_at'],
            assigned_worker=data.get('assigned_worker')
        )
        return group
    
    def _serialize_worker(self, worker: Worker) -> dict:
        """Serialize worker object to Redis-compatible dict"""
        data = worker.to_dict()
        if isinstance(data['last_heartbeat'], datetime):
            data['last_heartbeat'] = data['last_heartbeat'].isoformat()
        
        # Convert complex objects to JSON strings
        serialized_data = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                serialized_data[key] = json.dumps(value)
            else:
                serialized_data[key] = str(value) if value is not None else ""
        
        return serialized_data
    
    def _deserialize_worker(self, data: dict) -> Worker:
        """Deserialize Redis dict to Worker object"""
        if isinstance(data['last_heartbeat'], str):
            data['last_heartbeat'] = datetime.fromisoformat(data['last_heartbeat'])
        
        worker = Worker(
            worker_id=data['worker_id'],
            name=data['name'],
            target_types=[JobTarget(t) for t in data['target_types']],
            status=data['status'],
            current_jobs=data['current_jobs'],
            last_heartbeat=data['last_heartbeat'],
            metadata=data.get('metadata', {})
        )
        return worker
    
    # Job operations
    def add_job(self, job: Job) -> None:
        """Add a new job to the store"""
        with self._lock:
            pipe = self.redis.pipeline()
            job_data = self._serialize_job(job)
            pipe.hset(f"{self.JOB_PREFIX}{job.job_id}", mapping=job_data)
            pipe.sadd(self.JOB_LIST, job.job_id)
            pipe.execute()
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        with self._lock:
            data = self.redis.hgetall(f"{self.JOB_PREFIX}{job_id}")
            if data:
                # Parse nested JSON fields
                if 'payload' in data:
                    data['payload'] = json.loads(data['payload'])
                if 'result' in data and data['result']:
                    data['result'] = json.loads(data['result'])
                return self._deserialize_job(data)
            return None
    
    def update_job(self, job: Job) -> None:
        """Update an existing job"""
        with self._lock:
            if self.redis.exists(f"{self.JOB_PREFIX}{job.job_id}"):
                job_data = self._serialize_job(job)
                self.redis.hset(f"{self.JOB_PREFIX}{job.job_id}", mapping=job_data)
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job"""
        with self._lock:
            pipe = self.redis.pipeline()
            pipe.delete(f"{self.JOB_PREFIX}{job_id}")
            pipe.srem(self.JOB_LIST, job_id)
            result = pipe.execute()
            return result[0] > 0
    
    def list_jobs(self, org_id: Optional[str] = None, 
                  status: Optional[JobStatus] = None,
                  app_version_id: Optional[str] = None) -> List[Job]:
        """List jobs with optional filtering"""
        with self._lock:
            job_ids = self.redis.smembers(self.JOB_LIST)
            jobs = []
            
            for job_id in job_ids:
                job = self.get_job(job_id)
                if job:
                    # Apply filters
                    if org_id and job.payload.org_id != org_id:
                        continue
                    if status and job.status != status:
                        continue
                    if app_version_id and job.payload.app_version_id != app_version_id:
                        continue
                    jobs.append(job)
            
            return jobs
    
    # Group operations
    def add_group(self, group: JobGroup) -> None:
        """Add a new job group"""
        with self._lock:
            pipe = self.redis.pipeline()
            group_data = self._serialize_group(group)
            pipe.hset(f"{self.GROUP_PREFIX}{group.group_id}", mapping=group_data)
            pipe.sadd(self.GROUP_LIST, group.group_id)
            pipe.execute()
    
    def get_group(self, group_id: str) -> Optional[JobGroup]:
        """Get a job group by ID"""
        with self._lock:
            data = self.redis.hgetall(f"{self.GROUP_PREFIX}{group_id}")
            if data:
                # Parse jobs list
                if 'jobs' in data:
                    data['jobs'] = json.loads(data['jobs'])
                return self._deserialize_group(data)
            return None
    
    def update_group(self, group: JobGroup) -> None:
        """Update an existing job group"""
        with self._lock:
            if self.redis.exists(f"{self.GROUP_PREFIX}{group.group_id}"):
                group_data = self._serialize_group(group)
                self.redis.hset(f"{self.GROUP_PREFIX}{group.group_id}", mapping=group_data)
    
    def delete_group(self, group_id: str) -> bool:
        """Delete a job group"""
        with self._lock:
            pipe = self.redis.pipeline()
            pipe.delete(f"{self.GROUP_PREFIX}{group_id}")
            pipe.srem(self.GROUP_LIST, group_id)
            result = pipe.execute()
            return result[0] > 0
    
    def list_groups(self, org_id: Optional[str] = None,
                    status: Optional[JobStatus] = None) -> List[JobGroup]:
        """List job groups with optional filtering"""
        with self._lock:
            group_ids = self.redis.smembers(self.GROUP_LIST)
            groups = []
            
            for group_id in group_ids:
                group = self.get_group(group_id)
                if group:
                    # Apply filters
                    if org_id and group.org_id != org_id:
                        continue
                    if status and group.status != status:
                        continue
                    groups.append(group)
            
            return groups
    
    def find_group_by_app_version(self, org_id: str, app_version_id: str) -> Optional[JobGroup]:
        """Find an existing pending group for the same app version"""
        with self._lock:
            groups = self.list_groups(org_id=org_id, status=JobStatus.PENDING)
            for group in groups:
                if group.app_version_id == app_version_id:
                    return group
            return None
    
    def get_group_by_app_version(self, org_id: str, app_version_id: str) -> Optional[JobGroup]:
        """Alias for find_group_by_app_version for compatibility"""
        return self.find_group_by_app_version(org_id, app_version_id)
    
    # Worker operations
    def add_worker(self, worker: Worker) -> None:
        """Add a new worker"""
        with self._lock:
            pipe = self.redis.pipeline()
            worker_data = self._serialize_worker(worker)
            pipe.hset(f"{self.WORKER_PREFIX}{worker.worker_id}", mapping=worker_data)
            pipe.sadd(self.WORKER_LIST, worker.worker_id)
            pipe.execute()
    
    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get a worker by ID"""
        with self._lock:
            data = self.redis.hgetall(f"{self.WORKER_PREFIX}{worker_id}")
            if data:
                # Parse nested JSON fields
                if 'target_types' in data:
                    data['target_types'] = json.loads(data['target_types'])
                if 'current_jobs' in data:
                    data['current_jobs'] = json.loads(data['current_jobs'])
                if 'metadata' in data:
                    data['metadata'] = json.loads(data['metadata'])
                return self._deserialize_worker(data)
            return None
    
    def update_worker(self, worker: Worker) -> None:
        """Update an existing worker"""
        with self._lock:
            if self.redis.exists(f"{self.WORKER_PREFIX}{worker.worker_id}"):
                worker_data = self._serialize_worker(worker)
                self.redis.hset(f"{self.WORKER_PREFIX}{worker.worker_id}", mapping=worker_data)
    
    def delete_worker(self, worker_id: str) -> bool:
        """Delete a worker"""
        with self._lock:
            pipe = self.redis.pipeline()
            pipe.delete(f"{self.WORKER_PREFIX}{worker_id}")
            pipe.srem(self.WORKER_LIST, worker_id)
            result = pipe.execute()
            return result[0] > 0
    
    def list_workers(self, target_type: Optional[JobTarget] = None,
                     status: Optional[str] = None) -> List[Worker]:
        """List workers with optional filtering"""
        with self._lock:
            worker_ids = self.redis.smembers(self.WORKER_LIST)
            workers = []
            
            for worker_id in worker_ids:
                worker = self.get_worker(worker_id)
                if worker:
                    # Apply filters
                    if target_type and target_type not in worker.target_types:
                        continue
                    if status and worker.status != status:
                        continue
                    workers.append(worker)
            
            return workers
    
    def get_available_workers(self, target_type: JobTarget) -> List[Worker]:
        """Get workers that can handle a specific target type and are available"""
        with self._lock:
            workers = self.list_workers(target_type=target_type, status="idle")
            return [w for w in workers if len(w.current_jobs) == 0]
    
    def assign_job_to_worker(self, job_id: str, worker_id: str) -> bool:
        """Assign a job to a worker"""
        with self._lock:
            worker = self.get_worker(worker_id)
            job = self.get_job(job_id)
            
            if worker and job:
                if job_id not in worker.current_jobs:
                    worker.current_jobs.append(job_id)
                    worker.status = "busy"
                    self.update_worker(worker)
                
                job.worker_id = worker_id
                job.status = JobStatus.QUEUED
                job.updated_at = datetime.utcnow()
                self.update_job(job)
                return True
            return False
    
    def get_statistics(self) -> Dict:
        """Get system statistics"""
        with self._lock:
            jobs = self.list_jobs()
            groups = self.list_groups()
            workers = self.list_workers()
            
            job_status_counts = {}
            for status in JobStatus:
                job_status_counts[status.value] = len([j for j in jobs if j.status == status])
            
            idle_workers = len([w for w in workers if w.status == "idle"])
            busy_workers = len([w for w in workers if w.status == "busy"])
            
            return {
                "total_jobs": len(jobs),
                "pending": job_status_counts.get("pending", 0),
                "queued": job_status_counts.get("queued", 0),
                "running": job_status_counts.get("running", 0),
                "completed": job_status_counts.get("completed", 0),
                "failed": job_status_counts.get("failed", 0),
                "cancelled": job_status_counts.get("cancelled", 0),
                "total_groups": len(groups),
                "total_workers": len(workers),
                "idle_workers": idle_workers,
                "busy_workers": busy_workers
            }
    
    def clear_all(self) -> None:
        """Clear all data - useful for testing"""
        with self._lock:
            pipe = self.redis.pipeline()
            
            # Delete all jobs
            job_ids = self.redis.smembers(self.JOB_LIST)
            for job_id in job_ids:
                pipe.delete(f"{self.JOB_PREFIX}{job_id}")
            pipe.delete(self.JOB_LIST)
            
            # Delete all groups
            group_ids = self.redis.smembers(self.GROUP_LIST)
            for group_id in group_ids:
                pipe.delete(f"{self.GROUP_PREFIX}{group_id}")
            pipe.delete(self.GROUP_LIST)
            
            # Delete all workers
            worker_ids = self.redis.smembers(self.WORKER_LIST)
            for worker_id in worker_ids:
                pipe.delete(f"{self.WORKER_PREFIX}{worker_id}")
            pipe.delete(self.WORKER_LIST)
            
            pipe.execute()
            logger.info("Cleared all Redis data") 