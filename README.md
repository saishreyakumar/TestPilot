# QualGent Backend Coding Challenge

A CLI tool and GitHub Actions integration to queue, group, and deploy AppWright tests across local devices, emulators, and BrowserStack.

## Architecture Overview

This project consists of three main components:

1. **Backend Service** (`job-server`) - Handles job queuing, grouping by app_version_id, and worker assignment
2. **CLI Tool** (`qgjob`) - Command-line interface for submitting jobs and checking status
3. **GitHub Actions Integration** - CI/CD workflow for automated test execution

## Project Structure

```
TestPilot/
├── backend/           # Job orchestrator service
├── cli/              # qgjob CLI tool
├── shared/           # Common schemas and utilities
├── .github/workflows/# GitHub Actions workflows
├── examples/         # Example test scripts
├── docs/            # Documentation and diagrams
└── README.md        # This file
```

## Key Features

- **Job Grouping**: Tests targeting the same `app_version_id` are grouped together to minimize app installation overhead
- **Multi-Target Support**: Deploy tests to emulators, physical devices, or BrowserStack
- **Priority Queuing**: Support for job prioritization within organizations
- **Fault Tolerance**: Retry mechanisms and crash recovery
- **Scalability**: Designed for horizontal scaling across multiple workers

## Quick Start

1. **Setup Backend Service**:

   ```bash
   cd backend
   pip install -r requirements.txt
   python app.py
   ```

2. **Install CLI Tool**:

   ```bash
   cd cli
   pip install -e .
   ```

3. **Submit a Test Job**:

   ```bash
   qgjob submit --org-id=qualgent --app-version-id=xyz123 --test=tests/onboarding.spec.js
   ```

4. **Check Job Status**:
   ```bash
   qgjob status --job-id=abc456
   ```

## Architecture

The system consists of three main components working together:

1. **Backend Service** (`backend/`) - Job orchestrator with REST API
2. **CLI Tool** (`cli/`) - Command-line interface for job management
3. **GitHub Actions** (`.github/workflows/`) - CI/CD integration

### Key Features

- **Intelligent Job Grouping**: Jobs with the same `app_version_id` are automatically grouped to minimize app installation overhead
- **Multi-Platform Support**: Deploy tests to emulators, physical devices, or BrowserStack
- **Priority Scheduling**: Support for job prioritization and load balancing
- **Fault Tolerance**: Automatic retry mechanisms and worker failure detection
- **Scalability**: Designed for horizontal scaling across multiple workers

### Job Grouping Logic

The core innovation is automatic job grouping by `app_version_id`:

```
Jobs for app_version_id "v1.2.3":
├── tests/onboarding.spec.js
├── tests/login.spec.js
└── tests/checkout.spec.js

All grouped together → Single worker → Install app once → Run all tests
```

This minimizes setup time and maximizes resource efficiency.

## End-to-End Example

Here's a complete workflow from development to test execution:

### 1. Submit Test Jobs

```bash
# Submit individual test
qgjob submit --org-id=qualgent --app-version-id=v1.2.3 --test=tests/onboarding.spec.js

# Submit via GitHub Actions (automatic on push)
git push origin main
```

### 2. Monitor Execution

```bash
# Check job status
qgjob status --job-id=abc123 --watch

# View all jobs
qgjob list --org-id=qualgent

# Check system stats
qgjob stats
```

### 3. Review Results

Jobs are automatically grouped and executed efficiently:

```
Group: group-xyz789 (app_version_id: v1.2.3)
├── Job abc123: tests/onboarding.spec.js → ✅ COMPLETED
├── Job def456: tests/login.spec.js → ✅ COMPLETED
└── Job ghi789: tests/checkout.spec.js → ❌ FAILED

Worker: worker-123 (emulator)
App installed once, 3 tests executed sequentially
Total time: 8 minutes (vs 15 minutes without grouping)
```

## Sample Output Logs

### Job Submission

```bash
$ qgjob submit --org-id=qualgent --app-version-id=v1.2.3 --test=tests/onboarding.spec.js

ℹ Submitting job...
ℹ   Organization: qualgent
ℹ   App Version: v1.2.3
ℹ   Test: tests/onboarding.spec.js
ℹ   Target: emulator
ℹ   Priority: normal
✓ Job submitted successfully!
ℹ Job ID: 550e8400-e29b-41d4-a716-446655440000
ℹ Status: PENDING
ℹ Use 'qgjob status --job-id 550e8400-e29b-41d4-a716-446655440000' to check status
```

### Job Status Monitoring

```bash
$ qgjob status --job-id 550e8400-e29b-41d4-a716-446655440000

Job Status: 550e8400-e29b-41d4-a716-446655440000
==================================================
Job ID          550e8400-e29b-41d4-a716-446655440000
Status          RUNNING
Organization    qualgent
App Version     v1.2.3
Test Path       tests/onboarding.spec.js
Target          emulator
Priority        normal
Worker ID       worker-abc123
Created         2024-01-15T10:30:00
Updated         2024-01-15T10:32:15
Started         2024-01-15T10:31:30
```

### Server Statistics

```bash
$ qgjob stats

ℹ Server Statistics:

Job Statistics:
Metric      Count
----------  -------
Total Jobs  47
Pending     3
Running     8
Completed   35
Failed      1

Worker Statistics:
Metric          Count
--------------  -------
Total Workers   5
Active Workers  4
Total Groups    12
```

### GitHub Actions Output

```
✅ Test Discovery
Found 8 test files:
- tests/onboarding.spec.js
- tests/login.spec.js
- tests/checkout/payment.spec.js
- tests/checkout/shipping.spec.js

✅ Job Submission
Submitted 8 jobs for app_version_id: abc123def
Jobs grouped into 2 groups for efficiency

✅ Test Execution
Group group-001: 4 jobs → worker-emulator-1 → ✅ All passed
Group group-002: 4 jobs → worker-device-1 → ❌ 1 failed

❌ Build Failed
Failed test: tests/checkout/payment.spec.js
Error: Payment gateway timeout after 30 seconds
```

## Development

See individual component READMEs for detailed setup and development instructions:

- [Backend Service](./backend/README.md)
- [CLI Tool](./cli/README.md)
- [GitHub Actions](./docs/github-actions.md)

## Deployment

### Production Setup

1. **Deploy Backend Service**:

   ```bash
   cd backend
   pip install -r requirements.txt
   gunicorn --bind 0.0.0.0:5000 app:app
   ```

2. **Register Workers**:

   ```bash
   curl -X POST http://your-server:5000/workers \
     -H "Content-Type: application/json" \
     -d '{"name": "Production Emulator", "target_types": ["emulator"]}'
   ```

3. **Configure GitHub Actions**:
   - Set `QGJOB_SERVER_URL` secret to your production server
   - Update workflow triggers as needed

### Docker Deployment

```dockerfile
# Backend Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY backend/ .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### Scaling Considerations

- **Horizontal Scaling**: Add more workers to handle increased load
- **Database Backend**: Replace in-memory store with Redis/PostgreSQL for persistence
- **Load Balancing**: Use nginx or cloud load balancer for high availability
- **Monitoring**: Add metrics collection and alerting
