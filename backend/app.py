"""
QualGent Job Orchestrator Backend Service

This Flask application provides REST API endpoints for job submission,
status checking, and worker management.
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    JobStatus, JobTarget, JobPriority, JobPayload, Job, JobGroup, Worker,
    generate_job_id, generate_group_id, generate_worker_id
)
from job_store import JobStore
from redis_job_store import RedisJobStore
from scheduler import JobScheduler
from config import get_config

# Configure logging using config
config = get_config()
config.configure_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# --- Blueprint setup ---
jobs_bp = Blueprint('jobs', __name__)
workers_bp = Blueprint('workers', __name__)

def validate_required_fields(data, required_fields):
    missing = [f for f in required_fields if f not in data]
    if missing:
        return False, f"Missing required field(s): {', '.join(missing)}"
    return True, None

def error_response(message, code=400):
    return jsonify({"error": message}), code

# Move job routes to jobs_bp
@jobs_bp.route('/jobs', methods=['POST'])
def submit_job():
    """Submit a new test job"""
    try:
        data = request.get_json()
        
        ok, err = validate_required_fields(data, ['org_id', 'app_version_id', 'test_path'])
        if not ok:
            return error_response(err, 400)
        
        # Create job payload
        payload = JobPayload.from_dict(data)
        
        # Generate job ID and create job
        job_id = generate_job_id()
        job = Job(job_id=job_id, payload=payload)
        
        # Store job and add to scheduler
        job_store.add_job(job)
        scheduler.queue_job(job)
        
        return jsonify({
            "job_id": job_id,
            "status": job.status.value,
            "message": "Job submitted successfully"
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jobs_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Get job status and details"""
    try:
        job = job_store.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify(job.to_dict()), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jobs_bp.route('/jobs/<job_id>', methods=['PUT'])
def update_job_status(job_id: str):
    """Update job status (used by workers)"""
    try:
        data = request.get_json()
        job = job_store.get_job(job_id)
        
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        # Update job status and timestamps
        if 'status' in data:
            job.status = JobStatus(data['status'])
            job.updated_at = datetime.utcnow()
            
            if job.status == JobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.utcnow()
            elif job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job.completed_at = datetime.utcnow()
        
        if 'worker_id' in data:
            job.worker_id = data['worker_id']
            
        if 'result' in data:
            job.result = data['result']
            
        if 'error_message' in data:
            job.error_message = data['error_message']
        
        job_store.update_job(job)
        
        return jsonify(job.to_dict()), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@jobs_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List jobs with optional filtering"""
    try:
        org_id = request.args.get('org_id')
        status = request.args.get('status')
        app_version_id = request.args.get('app_version_id')
        
        jobs = job_store.list_jobs(
            org_id=org_id,
            status=JobStatus(status) if status else None,
            app_version_id=app_version_id
        )
        
        return jsonify({
            "jobs": [job.to_dict() for job in jobs],
            "count": len(jobs)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/groups', methods=['GET'])
def list_job_groups():
    """List job groups"""
    try:
        org_id = request.args.get('org_id')
        groups = job_store.list_groups(org_id=org_id)
        
        return jsonify({
            "groups": [group.to_dict() for group in groups],
            "count": len(groups)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Move worker routes to workers_bp
@workers_bp.route('/workers', methods=['POST'])
def register_worker():
    """Register a new worker"""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'target_types']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        worker_id = generate_worker_id()
        worker = Worker(
            worker_id=worker_id,
            name=data['name'],
            target_types=[JobTarget(t) for t in data['target_types']],
            metadata=data.get('metadata', {})
        )
        
        job_store.add_worker(worker)
        
        return jsonify({
            "worker_id": worker_id,
            "message": "Worker registered successfully"
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@workers_bp.route('/workers', methods=['GET'])
def list_workers():
    """List all workers"""
    try:
        workers = job_store.list_workers()
        return jsonify({
            "workers": [worker.to_dict() for worker in workers],
            "count": len(workers)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@workers_bp.route('/workers/<worker_id>/heartbeat', methods=['POST'])
def worker_heartbeat(worker_id: str):
    """Worker heartbeat endpoint"""
    try:
        worker = job_store.get_worker(worker_id)
        if not worker:
            return jsonify({"error": "Worker not found"}), 404
        
        worker.last_heartbeat = datetime.utcnow()
        job_store.update_worker(worker)
        
        # Get next job for worker if available
        next_job = scheduler.get_next_job_for_worker(worker)
        
        response = {"status": "ok"}
        if next_job:
            response["next_job"] = next_job.to_dict()
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        # Get all jobs and filter by status
        all_jobs = job_store.list_jobs()
        pending_jobs = job_store.list_jobs(status=JobStatus.PENDING)
        running_jobs = job_store.list_jobs(status=JobStatus.RUNNING)
        completed_jobs = job_store.list_jobs(status=JobStatus.COMPLETED)
        failed_jobs = job_store.list_jobs(status=JobStatus.FAILED)
        
        # Get groups and workers
        all_groups = job_store.list_groups()
        all_workers = job_store.list_workers()
        active_workers = [w for w in all_workers if w.status != "offline"]
        
        stats = {
            "total_jobs": len(all_jobs),
            "pending_jobs": len(pending_jobs),
            "running_jobs": len(running_jobs),
            "completed_jobs": len(completed_jobs),
            "failed_jobs": len(failed_jobs),
            "total_groups": len(all_groups),
            "total_workers": len(all_workers),
            "active_workers": len(active_workers)
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Initialize job store with Redis (fallback to in-memory)
    def create_job_store():
        """Create job store with Redis if available, fallback to in-memory"""
        config = get_config()
        
        if config.USE_REDIS:
            try:
                logger.info("Attempting to connect to Redis...")
                job_store = RedisJobStore(config.REDIS_URL)
                logger.info("✅ Using Redis for job storage")
                return job_store
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}")
                logger.info("🔄 Falling back to in-memory storage")
        
        # Fallback to in-memory storage
        logger.info("📝 Using in-memory job storage")
        return JobStore()

    # Initialize components
    job_store = create_job_store()
    scheduler = JobScheduler(job_store)
    
    # Start the scheduler in a background thread
    scheduler.start()
    
    # Register blueprints
    app.register_blueprint(jobs_bp)
    app.register_blueprint(workers_bp)
    
    # Run the Flask app
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG) 