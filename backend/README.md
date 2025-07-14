# QualGent Job Orchestrator Backend

The backend service provides REST API endpoints for job submission, status checking, and worker management. It implements intelligent job grouping by `app_version_id` to minimize app installation overhead.

## Features

- **Job Grouping**: Automatically groups jobs with the same `app_version_id` to optimize device setup
- **Priority Scheduling**: Supports job prioritization (urgent, high, normal, low)
- **Worker Management**: Handles worker registration, heartbeats, and assignment
- **Fault Tolerance**: Automatic retry mechanisms and worker failure detection
- **REST API**: RESTful endpoints for all operations

## Quick Start

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Server**:

   ```bash
   python app.py
   ```

3. **Server will be available at**: `http://localhost:5000`

## API Endpoints

### Jobs

- `POST /jobs` - Submit a new test job
- `GET /jobs/{job_id}` - Get job status and details
- `PUT /jobs/{job_id}` - Update job status (used by workers)
- `GET /jobs` - List jobs with optional filtering

### Workers

- `POST /workers` - Register a new worker
- `GET /workers` - List all workers
- `POST /workers/{worker_id}/heartbeat` - Worker heartbeat

### Monitoring

- `GET /health` - Health check
- `GET /stats` - System statistics
- `GET /groups` - List job groups

## Job Submission Example

```bash
curl -X POST http://localhost:5000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "qualgent",
    "app_version_id": "xyz123",
    "test_path": "tests/onboarding.spec.js",
    "target": "emulator",
    "priority": "normal"
  }'
```

## Worker Registration Example

```bash
curl -X POST http://localhost:5000/workers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Android Emulator Worker",
    "target_types": ["emulator", "device"]
  }'
```

## Architecture

The backend consists of three main components:

1. **Flask API** (`app.py`) - REST endpoints
2. **Job Store** (`job_store.py`) - In-memory data storage
3. **Job Scheduler** (`scheduler.py`) - Job grouping and assignment logic

### Job Grouping Logic

Jobs with the same `org_id` and `app_version_id` are automatically grouped together. This ensures that:

- The app is only installed once per device
- Related tests can be run in sequence efficiently
- Resource utilization is optimized

### Worker Assignment

The scheduler assigns job groups to workers based on:

- Target type compatibility (emulator, device, browserstack)
- Worker availability
- Job priority
- Load balancing

## Configuration

Environment variables:

- `PORT` - Server port (default: 5000)
- `DEBUG` - Enable debug mode (default: false)

## Monitoring and Logging

The service provides comprehensive logging and monitoring:

- Job status tracking
- Worker health monitoring
- System statistics
- Error handling and retry logic

Check `/stats` endpoint for real-time system metrics.
