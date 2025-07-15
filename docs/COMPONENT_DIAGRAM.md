# TestPilot Component Diagram

## System Components Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TestPilot Components                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Client Layer                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   CLI Tool  │  │   Web UI    │  │   CI/CD     │  │   SDK       │ │   │
│  │  │  (qgjob)    │  │  (Future)   │  │  Integration│  │  (Future)   │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                    API Gateway Layer                                 │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    Flask Application                            │ │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │ │ │
│  │  │  │   Routes    │  │  Middleware │  │  Validation │  │  CORS   │ │ │ │
│  │  │  │  (app.py)   │  │   (CORS)    │  │   (Input)   │  │ Support │ │ │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │ │ │
│  │  └─────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                   │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                    Business Logic Layer                              │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │   Job Store │  │  Scheduler  │  │   Workers   │  │   Groups    │   │ │
│  │  │   Manager   │  │   Manager   │  │   Manager   │  │   Manager   │   │ │
│  │  │             │  │             │  │             │  │             │   │ │
│  │  │ • Redis     │  │ • Grouping  │  │ • Register  │  │ • Create    │   │ │
│  │  │ • In-Memory │  │ • Scheduling│  │ • Heartbeat │  │ • Track     │   │ │
│  │  │ • CRUD      │  │ • Retry     │  │ • Load Bal. │  │ • Assign    │   │ │
│  │  │ • Fallback  │  │ • Priority  │  │ • Monitor   │  │ • Status    │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                   │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                    Data Layer                                       │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │ │
│  │  │   Redis Store   │    │  In-Memory Store│    │   Shared        │   │ │
│  │  │   (Primary)     │    │   (Fallback)    │    │   Schemas       │   │ │
│  │  │                 │    │                 │    │                 │   │ │
│  │  │ • Jobs          │    │ • Jobs          │    │ • Job           │   │ │
│  │  │ • Groups        │    │ • Groups        │    │ • JobPayload    │   │ │
│  │  │ • Workers       │    │ • Workers       │    │ • JobGroup      │   │ │
│  │  │ • Statistics    │    │ • Statistics    │    │ • Worker        │   │ │
│  │  │ • Pub/Sub       │    │ • Temporary     │    │ • Enums         │   │ │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Component Relationships

### 1. CLI Component (`cli/qgjob/cli.py`)

**Dependencies**:

- `requests`: HTTP client for API communication
- `click`: Command-line interface framework
- `tabulate`: Table formatting for output
- `colorama`: Cross-platform colored output

**Key Classes**:

- `QGJobClient`: HTTP client wrapper
- Command functions: `submit`, `status`, `list`, `stats`, `health`

**API Endpoints Used**:

- `POST /jobs`: Submit new jobs
- `GET /jobs/{id}`: Get job status
- `GET /jobs`: List jobs with filters
- `GET /stats`: Get system statistics
- `GET /health`: Health check

### 2. Backend API Component (`backend/app.py`)

**Dependencies**:

- `flask`: Web framework
- `flask_cors`: Cross-origin resource sharing
- `shared.schemas`: Data models
- `job_store`: Storage abstraction
- `scheduler`: Job scheduling logic

**Key Routes**:

- `GET /health`: Health check endpoint
- `POST /jobs`: Job submission
- `GET /jobs/{id}`: Job status retrieval
- `PUT /jobs/{id}`: Job status updates
- `GET /jobs`: Job listing with filters
- `GET /groups`: Group listing
- `POST /workers`: Worker registration
- `GET /workers`: Worker listing
- `POST /workers/{id}/heartbeat`: Worker heartbeat
- `GET /stats`: System statistics

### 3. Job Store Component (`backend/job_store.py`)

**Purpose**: Abstract storage interface

**Key Methods**:

- `add_job(job)`: Add new job
- `get_job(job_id)`: Retrieve job by ID
- `update_job(job)`: Update job status
- `list_jobs()`: List jobs with filters
- `add_group(group)`: Add job group
- `get_group(group_id)`: Get group by ID
- `list_groups()`: List groups
- `add_worker(worker)`: Register worker
- `get_worker(worker_id)`: Get worker by ID
- `update_worker_heartbeat()`: Update worker heartbeat

### 4. Redis Job Store Component (`backend/redis_job_store.py`)

**Dependencies**:

- `redis`: Redis client library
- `json`: JSON serialization
- `job_store`: Base class

**Key Features**:

- Redis connection management
- JSON serialization/deserialization
- Atomic operations
- Error handling and fallback
- Connection pooling

**Data Structures**:

- `jobs:{job_id}`: Job data
- `groups:{group_id}`: Group data
- `workers:{worker_id}`: Worker data
- `org_jobs:{org_id}`: Organization job index
- `app_jobs:{app_version_id}`: App version job index

### 5. Scheduler Component (`backend/scheduler.py`)

**Dependencies**:

- `job_store`: Storage interface
- `shared.schemas`: Data models
- `threading`: Background processing
- `time`: Timing utilities

**Key Features**:

- Job grouping by app version
- Priority-based scheduling
- Retry logic with exponential backoff
- Worker load balancing
- Background job processing

**Key Methods**:

- `queue_job(job)`: Add job to scheduler
- `process_jobs()`: Process pending jobs
- `assign_job_to_worker()`: Assign job to available worker
- `handle_job_completion()`: Handle job completion
- `retry_failed_job()`: Retry failed jobs

### 6. Shared Schemas Component (`shared/schemas.py`)

**Purpose**: Common data models and validation

**Key Classes**:

- `JobStatus`: Enum for job states
- `JobTarget`: Enum for execution targets
- `JobPriority`: Enum for job priorities
- `JobPayload`: Job submission data
- `Job`: Complete job record
- `JobGroup`: Group of related jobs
- `Worker`: Worker/agent representation

**Key Methods**:

- `to_dict()`: Serialize to dictionary
- `from_dict()`: Deserialize from dictionary
- `generate_job_id()`: Generate unique job ID
- `generate_group_id()`: Generate unique group ID
- `generate_worker_id()`: Generate unique worker ID

## Data Flow Between Components

### Job Submission Flow

```
CLI Client → Flask App → Job Store → Scheduler → Worker Assignment
     ↓           ↓           ↓           ↓              ↓
  User Input  Validation  Persistence  Grouping    Execution
```

### Job Status Update Flow

```
Worker → Flask App → Job Store → Scheduler → CLI Client
   ↓         ↓           ↓           ↓           ↓
Execution  Validation  Persistence  Processing  Display
```

### Worker Management Flow

```
Worker → Flask App → Job Store → Scheduler
   ↓         ↓           ↓           ↓
Heartbeat  Validation  Persistence  Load Balance
```

## Component Communication Patterns

### 1. Synchronous Communication

- CLI to API: HTTP requests/responses
- API to Storage: Direct method calls
- Scheduler to Storage: Direct method calls

### 2. Asynchronous Communication

- Scheduler background processing
- Worker heartbeat monitoring
- Job retry scheduling

### 3. Event-Driven Communication

- Job status changes trigger scheduler updates
- Worker registration triggers load balancing
- Job completion triggers group status updates

## Error Handling and Resilience

### 1. Storage Layer

- Redis connection failure → In-memory fallback
- Data serialization errors → Validation and retry
- Storage full → Error response to client

### 2. API Layer

- Invalid input → Validation error response
- Storage errors → Graceful error handling
- Network errors → Timeout and retry

### 3. Scheduler Layer

- Worker failures → Job retry logic
- Group processing errors → Individual job processing
- Priority conflicts → FIFO fallback

### 4. CLI Layer

- Network errors → User-friendly error messages
- API errors → Detailed error reporting
- Timeout errors → Retry with exponential backoff

## Performance Characteristics

### 1. Storage Performance

- Redis: O(1) for key-based operations
- In-Memory: O(1) for all operations
- JSON serialization: O(n) where n is data size

### 2. API Performance

- Job submission: O(1) + storage operation
- Job retrieval: O(1) storage lookup
- Job listing: O(n) where n is number of jobs
- Statistics: O(1) cached values

### 3. Scheduler Performance

- Job queuing: O(1) append operation
- Job grouping: O(log n) binary search
- Worker assignment: O(m) where m is number of workers
- Background processing: O(1) per job

## Scalability Considerations

### 1. Horizontal Scaling

- Multiple API instances behind load balancer
- Redis cluster for storage
- Multiple scheduler instances
- Worker pool scaling

### 2. Vertical Scaling

- Increased memory for in-memory storage
- Larger Redis instance
- More CPU cores for processing
- Faster storage (SSD)

### 3. Performance Bottlenecks

- Redis connection limits
- JSON serialization overhead
- Background thread contention
- Network latency

## Security Considerations

### 1. Input Validation

- All API inputs validated
- CLI parameter validation
- Schema-based validation
- Type checking

### 2. Data Protection

- No sensitive data in logs
- Secure storage connections
- Data isolation by organization
- Access control (future)

### 3. Network Security

- HTTPS for production
- CORS configuration
- Rate limiting (future)
- Authentication (future)
