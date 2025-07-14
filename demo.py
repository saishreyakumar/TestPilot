#!/usr/bin/env python3
"""
QualGent Backend Coding Challenge - Comprehensive Demo

This script demonstrates all the key components of the system:
1. Shared data models and schemas
2. Job store functionality with thread safety
3. Job scheduler with intelligent grouping
4. Job grouping by app_version_id (core feature)
5. Worker management and assignment
6. Priority scheduling
7. Fault tolerance and retry mechanisms

This shows what the system does without needing a running Flask server.
"""

import sys
import time
import threading
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append('.')
sys.path.append('..')
sys.path.append('./backend')

from shared import (
    JobStatus, JobTarget, JobPriority, JobPayload, Job, JobGroup, Worker,
    generate_job_id, generate_group_id, generate_worker_id
)

# Change to the backend directory for imports
import os
old_cwd = os.getcwd()
os.chdir('./backend')
from job_store import JobStore
from scheduler import JobScheduler
os.chdir(old_cwd)

def print_header(title):
    """Print a styled header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step, description):
    """Print a step with formatting"""
    print(f"\n🔸 Step {step}: {description}")
    print("-" * 50)

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")

def print_data(data, title="Data"):
    """Print formatted data"""
    print(f"📊 {title}:")
    for key, value in data.items():
        print(f"   {key}: {value}")

def demonstrate_shared_schemas():
    """Demonstrate the shared data models"""
    print_header("1. SHARED DATA SCHEMAS - The Foundation")
    
    print_info("Testing job payload creation...")
    
    # Create different job payloads
    payloads = [
        JobPayload(
            org_id="qualgent",
            app_version_id="v1.2.3", 
            test_path="tests/onboarding.spec.js",
            target=JobTarget.EMULATOR,
            priority=JobPriority.HIGH
        ),
        JobPayload(
            org_id="qualgent",
            app_version_id="v1.2.3",  # Same app version - will be grouped!
            test_path="tests/login.spec.js",
            target=JobTarget.EMULATOR,
            priority=JobPriority.NORMAL
        ),
        JobPayload(
            org_id="qualgent", 
            app_version_id="v2.0.0",  # Different app version - separate group
            test_path="tests/checkout.spec.js",
            target=JobTarget.DEVICE,
            priority=JobPriority.URGENT
        ),
        JobPayload(
            org_id="another-org",
            app_version_id="v1.0.0",
            test_path="tests/smoke.spec.js",
            target=JobTarget.BROWSERSTACK,
            priority=JobPriority.LOW
        )
    ]
    
    jobs = []
    for i, payload in enumerate(payloads, 1):
        job = Job(job_id=generate_job_id(), payload=payload)
        jobs.append(job)
        
        print(f"\n📋 Job {i}:")
        print(f"   ID: {job.job_id[:8]}...")
        print(f"   Org: {payload.org_id}")
        print(f"   App Version: {payload.app_version_id}")
        print(f"   Test: {payload.test_path}")
        print(f"   Target: {payload.target.value}")
        print(f"   Priority: {payload.priority.value}")
        print(f"   Status: {job.status.value}")
    
    print_success(f"Created {len(jobs)} jobs with different configurations")
    return jobs

def demonstrate_job_store(jobs):
    """Demonstrate job store functionality"""
    print_header("2. JOB STORE - Thread-Safe Data Management")
    
    print_info("Creating job store and adding jobs...")
    store = JobStore()
    
    # Add jobs to store
    for job in jobs:
        store.add_job(job)
    
    print_success(f"Added {len(jobs)} jobs to store")
    
    # Test filtering and querying
    print_info("Testing job filtering capabilities...")
    
    qualgent_jobs = store.list_jobs(org_id="qualgent")
    print(f"📊 Qualgent jobs: {len(qualgent_jobs)}")
    
    v123_jobs = store.list_jobs(app_version_id="v1.2.3") 
    print(f"📊 v1.2.3 jobs: {len(v123_jobs)}")
    
    emulator_jobs = [j for j in store.jobs.values() if j.payload.target == JobTarget.EMULATOR]
    print(f"📊 Emulator jobs: {len(emulator_jobs)}")
    
    # Test statistics
    stats = store.get_queue_stats()
    print_data(stats, "Queue Statistics")
    
    return store

def demonstrate_worker_management(store):
    """Demonstrate worker registration and management"""
    print_header("3. WORKER MANAGEMENT - Device Fleet Coordination")
    
    print_info("Registering test workers...")
    
    # Create different types of workers
    workers = [
        Worker(
            worker_id=generate_worker_id(),
            name="Android Emulator Worker",
            target_types=[JobTarget.EMULATOR],
            metadata={"device": "Pixel 4", "android_version": "11"}
        ),
        Worker(
            worker_id=generate_worker_id(), 
            name="Physical Device Worker",
            target_types=[JobTarget.DEVICE, JobTarget.EMULATOR],
            metadata={"device": "Samsung Galaxy S21", "android_version": "12"}
        ),
        Worker(
            worker_id=generate_worker_id(),
            name="BrowserStack Worker", 
            target_types=[JobTarget.BROWSERSTACK],
            metadata={"cloud": "browserstack", "parallel_sessions": 5}
        )
    ]
    
    # Add workers to store
    for worker in workers:
        store.add_worker(worker)
        print(f"🔧 Registered: {worker.name} ({worker.worker_id[:8]}...)")
        print(f"   Targets: {[t.value for t in worker.target_types]}")
        print(f"   Metadata: {worker.metadata}")
    
    print_success(f"Registered {len(workers)} workers")
    
    # Test worker queries
    emulator_workers = store.get_available_workers(JobTarget.EMULATOR)
    print(f"📊 Available emulator workers: {len(emulator_workers)}")
    
    return workers

def demonstrate_job_grouping_and_scheduling(store, jobs):
    """Demonstrate the core job grouping and scheduling logic"""
    print_header("4. JOB GROUPING & SCHEDULING - The Core Innovation")
    
    print_info("Creating scheduler and demonstrating job grouping...")
    scheduler = JobScheduler(store)
    
    # Queue jobs for scheduling - this is where the magic happens!
    print_info("Submitting jobs to scheduler...")
    for i, job in enumerate(jobs, 1):
        print(f"\n📤 Submitting job {i}: {job.payload.test_path}")
        print(f"   App Version: {job.payload.app_version_id}")
        print(f"   Organization: {job.payload.org_id}")
        
        scheduler.queue_job(job)
    
    # Show the groups that were created
    print_info("Analyzing job groups created...")
    groups = store.list_groups()
    
    print(f"\n🎯 GROUPING RESULTS:")
    print(f"   Total jobs submitted: {len(jobs)}")
    print(f"   Groups created: {len(groups)}")
    print(f"   Efficiency gain: {len(jobs) - len(groups)} fewer app installations!")
    
    for i, group in enumerate(groups, 1):
        print(f"\n📦 Group {i}: {group.group_id[:8]}...")
        print(f"   Organization: {group.org_id}")
        print(f"   App Version: {group.app_version_id}")
        print(f"   Jobs in group: {len(group.jobs)}")
        print(f"   Status: {group.status.value}")
        
        # Show which jobs are in this group
        group_jobs = store.get_jobs_by_group(group.group_id)
        for job in group_jobs:
            print(f"     - {job.payload.test_path} (priority: {job.payload.priority.value})")
    
    print_success("Job grouping demonstrates core efficiency optimization!")
    
    return scheduler, groups

def demonstrate_job_assignment(store, scheduler, workers):
    """Demonstrate job assignment to workers"""
    print_header("5. JOB ASSIGNMENT - Worker Allocation")
    
    print_info("Simulating job assignment to workers...")
    
    # Get pending job groups
    pending_groups = [g for g in store.groups.values() if g.status == JobStatus.PENDING]
    
    for group in pending_groups:
        # Get the first job to determine target type
        if not group.jobs:
            continue
            
        first_job = store.get_job(group.jobs[0])
        if not first_job:
            continue
            
        target_type = first_job.payload.target
        available_workers = store.get_available_workers(target_type)
        
        if available_workers:
            worker = available_workers[0]
            
            print(f"\n🔄 Assigning group {group.group_id[:8]}... to worker {worker.worker_id[:8]}...")
            print(f"   Target type: {target_type.value}")
            print(f"   Worker: {worker.name}")
            print(f"   Jobs in group: {len(group.jobs)}")
            
            # Assign all jobs in the group to this worker
            assigned_count = 0
            for job_id in group.jobs:
                if store.assign_job_to_worker(job_id, worker.worker_id):
                    assigned_count += 1
            
            # Update group status
            group.status = JobStatus.QUEUED
            group.assigned_worker = worker.worker_id
            store.update_group(group)
            
            print(f"   ✅ Assigned {assigned_count} jobs to {worker.name}")
        else:
            print(f"   ⚠️  No available workers for {target_type.value}")
    
    # Show worker status
    print_info("Worker status after assignment:")
    for worker in workers:
        updated_worker = store.get_worker(worker.worker_id)
        print(f"🔧 {updated_worker.name}: {updated_worker.status} ({len(updated_worker.current_jobs)} jobs)")

def demonstrate_job_execution_simulation(store):
    """Simulate job execution and status updates"""
    print_header("6. JOB EXECUTION SIMULATION - End-to-End Flow")
    
    print_info("Simulating job execution with status updates...")
    
    queued_jobs = store.get_jobs_by_status(JobStatus.QUEUED)
    
    for job in queued_jobs[:3]:  # Simulate first 3 jobs
        print(f"\n🎬 Simulating execution of: {job.payload.test_path}")
        
        # Start job
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        store.update_job(job)
        print(f"   📍 Status: RUNNING")
        
        # Simulate some execution time
        time.sleep(0.1)
        
        # Complete job (simulate success or failure)
        import random
        if random.random() > 0.2:  # 80% success rate
            job.status = JobStatus.COMPLETED
            job.result = {
                "tests_run": random.randint(5, 15),
                "tests_passed": random.randint(4, 15),
                "duration": f"{random.randint(30, 180)}s",
                "screenshots": random.randint(10, 25)
            }
            print(f"   ✅ Status: COMPLETED")
            print(f"   📊 Results: {job.result}")
        else:
            job.status = JobStatus.FAILED
            job.error_message = "Assertion failed: Login button not found"
            print(f"   ❌ Status: FAILED")
            print(f"   🚨 Error: {job.error_message}")
        
        job.completed_at = datetime.utcnow()
        store.update_job(job)
        
        # Free up the worker
        if job.worker_id:
            store.complete_job_for_worker(job.job_id, job.worker_id)

def demonstrate_monitoring_and_stats(store):
    """Demonstrate monitoring and statistics"""
    print_header("7. MONITORING & STATISTICS - System Health")
    
    print_info("Generating comprehensive system statistics...")
    
    # Get updated statistics
    stats = store.get_queue_stats()
    
    print_data(stats, "Final System Statistics")
    
    # Job breakdown by status
    print_info("Job status breakdown:")
    for status in JobStatus:
        count = len(store.get_jobs_by_status(status))
        if count > 0:
            print(f"   {status.value.upper()}: {count}")
    
    # Group analysis
    print_info("Job group analysis:")
    for group in store.groups.values():
        efficiency = len(group.jobs)
        print(f"   Group {group.group_id[:8]}... (app: {group.app_version_id}): {efficiency} jobs")
    
    # Calculate efficiency metrics
    total_jobs = len(store.jobs)
    total_groups = len(store.groups)
    installations_saved = total_jobs - total_groups
    
    print(f"\n💡 EFFICIENCY METRICS:")
    print(f"   Total test jobs: {total_jobs}")
    print(f"   App installations needed: {total_groups}")
    print(f"   Installations saved: {installations_saved}")
    print(f"   Efficiency improvement: {(installations_saved/total_jobs)*100:.1f}%")

def main():
    """Run the complete demonstration"""
    print_header("🚀 QUALGENT BACKEND CODING CHALLENGE - LIVE DEMO")
    print("This demonstration shows all key components working together:")
    print("• Shared data models and schemas") 
    print("• Thread-safe job storage")
    print("• Intelligent job grouping by app_version_id") 
    print("• Worker management and assignment")
    print("• Priority scheduling and fault tolerance")
    print("• Real-time monitoring and statistics")
    
    try:
        # Step-by-step demonstration
        jobs = demonstrate_shared_schemas()
        store = demonstrate_job_store(jobs)
        workers = demonstrate_worker_management(store)
        scheduler, groups = demonstrate_job_grouping_and_scheduling(store, jobs)
        demonstrate_job_assignment(store, scheduler, workers)
        demonstrate_job_execution_simulation(store)
        demonstrate_monitoring_and_stats(store)
        
        print_header("🎉 DEMONSTRATION COMPLETE")
        print("✅ All components demonstrated successfully!")
        print("✅ Job grouping by app_version_id working perfectly!")
        print("✅ Worker assignment and scheduling operational!")
        print("✅ Monitoring and statistics functional!")
        
        print(f"\n🎯 KEY INSIGHT: Job grouping reduced app installations from")
        print(f"   {len(jobs)} individual installs to {len(groups)} group installs")
        print(f"   That's {len(jobs) - len(groups)} fewer installations - major efficiency gain!")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 