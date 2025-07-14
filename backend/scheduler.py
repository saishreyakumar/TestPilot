"""
Job Scheduler Implementation

This module handles the core scheduling logic:
- Groups jobs by app_version_id to minimize app installation overhead
- Assigns job groups to available workers
- Handles priority scheduling and load balancing
"""

import threading
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import JobStatus, JobTarget, JobPriority, Job, JobGroup, Worker, generate_group_id
from job_store import JobStore


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobScheduler:
    """Job scheduler that groups jobs by app_version_id and assigns to workers"""
    
    def __init__(self, job_store: JobStore):
        self.job_store = job_store
        self._running = False
        self._scheduler_thread = None
        self._lock = threading.RLock()
        
        # Scheduling configuration
        self.schedule_interval = 5  # seconds
        self.worker_timeout = 300   # 5 minutes
        self.max_retries = 3
        
        # Priority weights for scheduling
        self.priority_weights = {
            JobPriority.URGENT: 4,
            JobPriority.HIGH: 3,
            JobPriority.NORMAL: 2,
            JobPriority.LOW: 1
        }
    
    def start(self) -> None:
        """Start the scheduler background thread"""
        if not self._running:
            self._running = True
            self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._scheduler_thread.start()
            logger.info("Job scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join()
        logger.info("Job scheduler stopped")
    
    def queue_job(self, job: Job) -> None:
        """Queue a new job for scheduling"""
        with self._lock:
            # Find or create a group for this job
            group = self.job_store.get_group_by_app_version(
                job.payload.org_id, 
                job.payload.app_version_id
            )
            
            if not group:
                # Create new group
                group_id = generate_group_id()
                group = JobGroup(
                    group_id=group_id,
                    org_id=job.payload.org_id,
                    app_version_id=job.payload.app_version_id,
                    jobs=[job.job_id]
                )
                self.job_store.add_group(group)
                logger.info(f"Created new job group {group_id} for app_version_id {job.payload.app_version_id}")
            else:
                # Add to existing group
                self.job_store.add_job_to_group(job.job_id, group.group_id)
                logger.info(f"Added job {job.job_id} to existing group {group.group_id}")
            
            # Update job status
            job.status = JobStatus.PENDING
            job.updated_at = datetime.utcnow()
            self.job_store.update_job(job)
    
    def get_next_job_for_worker(self, worker: Worker) -> Optional[Job]:
        """Get the next job for a specific worker"""
        with self._lock:
            # Find jobs that this worker can handle
            available_jobs = []
            
            for job in self.job_store.get_jobs_by_status(JobStatus.QUEUED):
                if (job.payload.target in worker.target_types and 
                    job.worker_id == worker.worker_id):
                    available_jobs.append(job)
            
            if available_jobs:
                # Sort by priority and creation time
                available_jobs.sort(
                    key=lambda j: (
                        -self.priority_weights.get(j.payload.priority, 1),
                        j.created_at
                    )
                )
                return available_jobs[0]
            
            return None
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop"""
        while self._running:
            try:
                self._schedule_jobs()
                self._cleanup_stale_workers()
                self._handle_failed_jobs()
                time.sleep(self.schedule_interval)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(self.schedule_interval)
    
    def _schedule_jobs(self) -> None:
        """Schedule pending jobs to available workers"""
        with self._lock:
            # Get all pending job groups
            pending_groups = []
            for group in self.job_store.groups.values():
                if group.status == JobStatus.PENDING and group.jobs:
                    pending_groups.append(group)
            
            if not pending_groups:
                return
            
            # Sort groups by priority (based on highest priority job in group)
            pending_groups.sort(key=self._get_group_priority, reverse=True)
            
            # Assign groups to workers
            for group in pending_groups:
                self._assign_group_to_worker(group)
    
    def _get_group_priority(self, group: JobGroup) -> int:
        """Calculate priority score for a job group"""
        max_priority = JobPriority.LOW
        
        for job_id in group.jobs:
            job = self.job_store.get_job(job_id)
            if job and job.payload.priority.value > max_priority.value:
                max_priority = job.payload.priority
        
        return self.priority_weights.get(max_priority, 1)
    
    def _assign_group_to_worker(self, group: JobGroup) -> bool:
        """Assign a job group to an available worker"""
        # Determine target type needed (use first job's target)
        if not group.jobs:
            return False
        
        first_job = self.job_store.get_job(group.jobs[0])
        if not first_job:
            return False
        
        target_type = first_job.payload.target
        
        # Find available workers for this target type
        available_workers = self.job_store.get_available_workers(target_type)
        
        if not available_workers:
            logger.debug(f"No available workers for target type {target_type.value}")
            return False
        
        # Select worker (simple round-robin for now)
        worker = available_workers[0]
        
        # Assign all jobs in the group to this worker
        assigned_jobs = []
        for job_id in group.jobs:
            if self.job_store.assign_job_to_worker(job_id, worker.worker_id):
                assigned_jobs.append(job_id)
        
        if assigned_jobs:
            # Update group status
            group.status = JobStatus.QUEUED
            group.assigned_worker = worker.worker_id
            self.job_store.update_group(group)
            
            logger.info(f"Assigned group {group.group_id} with {len(assigned_jobs)} jobs to worker {worker.worker_id}")
            return True
        
        return False
    
    def _cleanup_stale_workers(self) -> None:
        """Mark workers as offline if they haven't sent heartbeat recently"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.worker_timeout)
        
        for worker in self.job_store.workers.values():
            if (worker.last_heartbeat < cutoff_time and 
                worker.status != "offline"):
                
                logger.warning(f"Worker {worker.worker_id} marked offline due to missing heartbeat")
                worker.status = "offline"
                
                # Reassign any jobs from this worker
                self._reassign_worker_jobs(worker.worker_id)
                
                self.job_store.update_worker(worker)
    
    def _reassign_worker_jobs(self, worker_id: str) -> None:
        """Reassign jobs from a failed worker"""
        jobs_to_reassign = []
        
        for job in self.job_store.jobs.values():
            if (job.worker_id == worker_id and 
                job.status in [JobStatus.QUEUED, JobStatus.RUNNING]):
                jobs_to_reassign.append(job)
        
        for job in jobs_to_reassign:
            logger.info(f"Reassigning job {job.job_id} from failed worker {worker_id}")
            
            # Reset job status
            job.worker_id = None
            job.status = JobStatus.PENDING
            job.updated_at = datetime.utcnow()
            
            # Increment retry count
            job.retry_count += 1
            
            if job.retry_count >= job.max_retries:
                job.status = JobStatus.FAILED
                job.error_message = f"Max retries exceeded due to worker failures"
                job.completed_at = datetime.utcnow()
            
            self.job_store.update_job(job)
    
    def _handle_failed_jobs(self) -> None:
        """Handle jobs that have been running too long or failed"""
        current_time = datetime.utcnow()
        job_timeout = timedelta(minutes=30)  # 30 minute timeout for jobs
        
        for job in self.job_store.jobs.values():
            if (job.status == JobStatus.RUNNING and 
                job.started_at and 
                current_time - job.started_at > job_timeout):
                
                logger.warning(f"Job {job.job_id} timed out after 30 minutes")
                
                # Mark job as failed
                job.status = JobStatus.FAILED
                job.error_message = "Job execution timeout"
                job.completed_at = current_time
                
                # Free up the worker
                if job.worker_id:
                    self.job_store.complete_job_for_worker(job.job_id, job.worker_id)
                
                self.job_store.update_job(job)
    
    def retry_job(self, job_id: str) -> bool:
        """Retry a failed job"""
        with self._lock:
            job = self.job_store.get_job(job_id)
            
            if not job or job.status != JobStatus.FAILED:
                return False
            
            if job.retry_count >= job.max_retries:
                logger.warning(f"Cannot retry job {job_id}: max retries exceeded")
                return False
            
            # Reset job for retry
            job.status = JobStatus.PENDING
            job.worker_id = None
            job.started_at = None
            job.completed_at = None
            job.error_message = None
            job.retry_count += 1
            job.updated_at = datetime.utcnow()
            
            self.job_store.update_job(job)
            
            # Re-queue the job
            self.queue_job(job)
            
            logger.info(f"Retrying job {job_id} (attempt {job.retry_count})")
            return True
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        with self._lock:
            job = self.job_store.get_job(job_id)
            
            if not job:
                return False
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return False
            
            # Cancel the job
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            
            # Free up worker if assigned
            if job.worker_id:
                self.job_store.complete_job_for_worker(job.job_id, job.worker_id)
            
            self.job_store.update_job(job)
            
            logger.info(f"Cancelled job {job_id}")
            return True
    
    def get_scheduler_stats(self) -> Dict:
        """Get scheduler statistics"""
        with self._lock:
            stats = self.job_store.get_queue_stats()
            
            # Add scheduler-specific stats
            stats.update({
                "scheduler_running": self._running,
                "schedule_interval": self.schedule_interval,
                "worker_timeout": self.worker_timeout,
                "max_retries": self.max_retries
            })
            
            return stats 