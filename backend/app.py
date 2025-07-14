"""
QualGent Job Orchestrator Backend Service

This Flask application provides REST API endpoints for job submission,
status checking, and worker management.
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import (
    JobStatus, JobTarget, JobPriority, JobPayload, Job, JobGroup, Worker,
    generate_job_id, generate_group_id, generate_worker_id
)
from job_store import JobStore
from scheduler import JobScheduler


app = Flask(__name__)
CORS(app)

# Initialize components
job_store = JobStore()
scheduler = JobScheduler(job_store)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })


@app.route('/jobs', methods=['POST'])
def submit_job():
    """Submit a new test job"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['org_id', 'app_version_id', 'test_path']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
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


@app.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Get job status and details"""
    try:
        job = job_store.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify(job.to_dict()), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/jobs/<job_id>', methods=['PUT'])
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


@app.route('/jobs', methods=['GET'])
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


@app.route('/workers', methods=['POST'])
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


@app.route('/workers', methods=['GET'])
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


@app.route('/workers/<worker_id>/heartbeat', methods=['POST'])
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
        stats = {
            "total_jobs": len(job_store.jobs),
            "pending_jobs": len([j for j in job_store.jobs.values() if j.status == JobStatus.PENDING]),
            "running_jobs": len([j for j in job_store.jobs.values() if j.status == JobStatus.RUNNING]),
            "completed_jobs": len([j for j in job_store.jobs.values() if j.status == JobStatus.COMPLETED]),
            "failed_jobs": len([j for j in job_store.jobs.values() if j.status == JobStatus.FAILED]),
            "total_groups": len(job_store.groups),
            "total_workers": len(job_store.workers),
            "active_workers": len([w for w in job_store.workers.values() if w.status != "offline"])
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Start the scheduler in a background thread
    scheduler.start()
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug) 