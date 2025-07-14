# QualGent Job CLI (qgjob)

A command-line interface for submitting and managing AppWright test jobs through the QualGent Job Server.

## Installation

### From Source

```bash
cd cli
pip install -e .
```

### Using pip (if published)

```bash
pip install qgjob
```

## Quick Start

1. **Start the backend server** (see [backend README](../backend/README.md))

2. **Submit a test job**:

   ```bash
   qgjob submit --org-id=qualgent --app-version-id=xyz123 --test=tests/onboarding.spec.js
   ```

3. **Check job status**:
   ```bash
   qgjob status --job-id=abc456
   ```

## Commands

### `qgjob submit`

Submit a new test job to the server.

```bash
qgjob submit [OPTIONS]
```

**Options:**

- `--org-id` (required): Organization ID
- `--app-version-id` (required): App version ID
- `--test` (required): Path to test file
- `--target`: Target platform (`emulator`, `device`, `browserstack`) [default: emulator]
- `--priority`: Job priority (`low`, `normal`, `high`, `urgent`) [default: normal]
- `--wait`: Wait for job completion and show result
- `--poll-interval`: Polling interval in seconds when using `--wait` [default: 5]

**Example:**

```bash
qgjob submit \
  --org-id=qualgent \
  --app-version-id=v1.2.3 \
  --test=tests/login.spec.js \
  --target=emulator \
  --priority=high \
  --wait
```

### `qgjob status`

Check the status of a specific job.

```bash
qgjob status --job-id=JOB_ID [OPTIONS]
```

**Options:**

- `--job-id` (required): Job ID to check
- `--watch`: Watch job status (refresh every 5 seconds)
- `--poll-interval`: Polling interval in seconds when using `--watch` [default: 5]

**Example:**

```bash
qgjob status --job-id=abc123 --watch
```

### `qgjob list`

List jobs with optional filtering.

```bash
qgjob list [OPTIONS]
```

**Options:**

- `--org-id`: Filter by organization ID
- `--status`: Filter by job status
- `--app-version-id`: Filter by app version ID
- `--limit`: Maximum number of jobs to show [default: 20]

**Examples:**

```bash
# List all jobs
qgjob list

# List jobs for specific org
qgjob list --org-id=qualgent

# List failed jobs
qgjob list --status=failed

# List jobs for specific app version
qgjob list --app-version-id=v1.2.3
```

### `qgjob stats`

Show server statistics including job counts and worker status.

```bash
qgjob stats
```

### `qgjob health`

Check if the server is healthy and reachable.

```bash
qgjob health
```

## Configuration

### Environment Variables

- `QGJOB_SERVER_URL`: Server URL (default: `http://localhost:5000`)
- `QGJOB_TIMEOUT`: Request timeout in seconds (default: 30)

### Command Line Options

You can also specify the server URL for individual commands:

```bash
qgjob --server-url=http://your-server:5000 submit --org-id=test --app-version-id=v1 --test=test.js
```

## Examples

### Basic Workflow

```bash
# 1. Check server health
qgjob health

# 2. Submit a test
qgjob submit --org-id=myorg --app-version-id=v1.0.0 --test=tests/smoke.spec.js

# Output: Job submitted with ID abc123...

# 3. Check status
qgjob status --job-id=abc123

# 4. List recent jobs
qgjob list --limit=10

# 5. View server stats
qgjob stats
```

### CI/CD Integration

```bash
# Submit job and wait for completion
qgjob submit \
  --org-id=$ORG_ID \
  --app-version-id=$APP_VERSION \
  --test=$TEST_FILE \
  --target=browserstack \
  --priority=high \
  --wait

# Exit code will be 0 for success, 1 for failure
```

### Monitoring Jobs

```bash
# Watch a specific job
qgjob status --job-id=abc123 --watch

# Monitor all jobs for an organization
qgjob list --org-id=myorg --limit=50
```

## Output Formats

The CLI provides colored output and formatted tables:

- ✓ Green checkmarks for success
- ✗ Red X marks for errors
- ⚠ Yellow warnings
- ℹ Blue info messages
- Color-coded job statuses

## Error Handling

The CLI provides helpful error messages and appropriate exit codes:

- Exit code 0: Success
- Exit code 1: Error (failed job, server unreachable, etc.)

Common error scenarios:

- Test file not found
- Server unreachable
- Invalid job ID
- Job execution failure

## Integration Examples

### Shell Scripts

```bash
#!/bin/bash
set -e

# Submit test and capture job ID
JOB_OUTPUT=$(qgjob submit --org-id=myorg --app-version-id=$1 --test=$2)
JOB_ID=$(echo "$JOB_OUTPUT" | grep "Job ID:" | cut -d' ' -f3)

echo "Submitted job: $JOB_ID"

# Wait for completion
qgjob status --job-id=$JOB_ID --watch
```

### Python Integration

```python
import subprocess
import sys

def submit_test(org_id, app_version_id, test_path):
    cmd = [
        'qgjob', 'submit',
        f'--org-id={org_id}',
        f'--app-version-id={app_version_id}',
        f'--test={test_path}',
        '--wait'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("Test passed!")
        return True
    else:
        print("Test failed!")
        print(result.stderr)
        return False
```
