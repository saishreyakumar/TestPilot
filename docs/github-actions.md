# GitHub Actions Integration

This document explains how to use the QualGent Job system with GitHub Actions for CI/CD automation.

## Overview

The provided GitHub Actions workflow (`appwright-test.yml`) automatically:

1. **Discovers test files** in your repository
2. **Submits jobs** to the QualGent Job Server using the `qgjob` CLI
3. **Monitors job progress** and waits for completion
4. **Reports results** with detailed logging and artifacts
5. **Fails the build** if any tests fail

## Workflow Features

### ✅ Automatic Test Discovery

- Finds all `*.spec.js` files in the `tests/` directory
- Supports filtering by directory or specific files
- Handles both single files and directory patterns

### ⚡ Parallel Job Submission

- Uses matrix strategy to submit multiple tests in parallel
- Groups jobs by `app_version_id` for efficient execution
- Supports different targets (emulator, device, browserstack)

### 🔍 Comprehensive Monitoring

- Real-time job status tracking
- Timeout handling (30 minutes default)
- Detailed error reporting for failed tests

### 📊 Rich Reporting

- Test execution summary
- Server statistics
- Downloadable test reports
- PR comments with results

## Setup Instructions

### 1. Add Workflow File

The workflow is already included at `.github/workflows/appwright-test.yml`. Customize it as needed for your project.

### 2. Configure Secrets

Add the following secret to your GitHub repository settings:

- `QGJOB_SERVER_URL`: URL of your QualGent Job Server (e.g., `https://jobs.yourcompany.com`)

**Note**: If not set, defaults to `http://localhost:5000`

### 3. Prepare Test Files

Ensure your test files are in the `tests/` directory and follow the naming pattern `*.spec.js`:

```
tests/
├── onboarding.spec.js
├── login.spec.js
├── checkout/
│   ├── payment.spec.js
│   └── shipping.spec.js
└── smoke/
    └── critical-path.spec.js
```

### 4. Start Your Job Server

Make sure your QualGent Job Server is running and accessible from GitHub Actions runners.

## Usage Examples

### Basic Usage (Automatic Triggers)

The workflow automatically runs on:

- Pushes to `main` and `develop` branches
- Pull requests to `main`

### Manual Execution

You can manually trigger the workflow with custom parameters:

1. Go to **Actions** tab in your GitHub repository
2. Select **AppWright Test** workflow
3. Click **Run workflow**
4. Configure parameters:
   - **Organization ID**: Your org identifier (default: `qualgent`)
   - **App Version ID**: Version to test (default: commit SHA)
   - **Test Filter**: Specific tests to run (default: `tests/`)
   - **Target Platform**: Where to run tests (default: `emulator`)
   - **Priority**: Job priority (default: `normal`)

### Test Filtering Examples

| Filter                | Description                  | Example                       |
| --------------------- | ---------------------------- | ----------------------------- |
| `tests/`              | All tests in tests directory | All `*.spec.js` files         |
| `tests/smoke/`        | All tests in smoke directory | Smoke test suite              |
| `tests/login.spec.js` | Specific test file           | Single test file              |
| `*checkout*`          | Pattern matching             | Files with "checkout" in name |

## Workflow Steps Explained

### 1. Test Discovery (`discover-tests`)

```yaml
- name: Find test files
  run: |
    TEST_FILTER="${{ github.event.inputs.test_filter || 'tests/' }}"
    TEST_FILES=$(find "$TEST_FILTER" -name "*.spec.js" -type f | jq -R -s -c 'split("\n")[:-1]')
```

This step:

- Searches for test files based on the filter
- Outputs a JSON array of test file paths
- Counts total tests found

### 2. Job Submission (`submit-tests`)

```yaml
strategy:
  matrix:
    test-file: ${{ fromJson(needs.discover-tests.outputs.test-files) }}
steps:
  - name: Submit test job
    run: |
      qgjob submit \
        --org-id="$ORG_ID" \
        --app-version-id="$APP_VERSION_ID" \
        --test="${{ matrix.test-file }}" \
        --target="$TARGET" \
        --priority="$PRIORITY"
```

This step:

- Runs in parallel for each discovered test file
- Submits jobs to the QualGent Job Server
- Captures job IDs for monitoring

### 3. Completion Monitoring (`wait-for-completion`)

```bash
while [[ ${#PENDING_JOBS[@]} -gt 0 && $ELAPSED_TIME -lt $MAX_WAIT_TIME ]]; do
  for job_id in "${PENDING_JOBS[@]}"; do
    STATUS=$(qgjob status --job-id="$job_id")
    # Handle status changes...
  done
  sleep $POLL_INTERVAL
done
```

This step:

- Polls all submitted jobs every 10 seconds
- Tracks completed, failed, and pending jobs
- Times out after 30 minutes
- Fails the build if any test fails

### 4. Result Reporting (`report-results`)

```yaml
- name: Generate test report
  run: |
    echo "# AppWright Test Results" > test-report.md
    qgjob stats >> test-report.md
    qgjob list --org-id="$ORG_ID" --app-version-id="$APP_VERSION_ID" >> test-report.md
```

This step:

- Generates a markdown test report
- Uploads reports as artifacts
- Comments on PRs with results

## Configuration Options

### Environment Variables

You can customize the workflow behavior using environment variables:

```yaml
env:
  QGJOB_SERVER_URL: ${{ secrets.QGJOB_SERVER_URL }}
  ORG_ID: "your-org-id"
  APP_VERSION_ID: ${{ github.sha }}
  TARGET: "browserstack"
  PRIORITY: "high"
```

### Timeout Settings

Modify timeouts in the workflow:

```yaml
MAX_WAIT_TIME=3600    # 1 hour
POLL_INTERVAL=15      # 15 seconds
```

### Retry Configuration

Add retry logic for failed jobs:

```yaml
- name: Retry failed jobs
  if: failure()
  run: |
    for job_id in $FAILED_JOBS; do
      qgjob retry --job-id="$job_id"
    done
```

## Integration with Pull Requests

The workflow automatically:

1. **Runs on PR creation/updates**
2. **Posts results as comments**
3. **Shows status checks**
4. **Blocks merging if tests fail**

Example PR comment:

```markdown
## AppWright Test Results

**Organization:** qualgent
**App Version:** abc123def
**Target:** emulator
**Tests Found:** 12

## Test Summary

✅ 10 passed
❌ 2 failed

## Failed Tests

- tests/checkout/payment.spec.js (timeout)
- tests/login.spec.js (assertion failed)
```

## Troubleshooting

### Common Issues

#### 1. Server Unreachable

```
Error: Server health check failed: Connection refused
```

**Solution**: Ensure your job server is running and the `QGJOB_SERVER_URL` secret is correct.

#### 2. No Tests Found

```
Warning: No tests found with filter: tests/
```

**Solution**: Check that test files exist and match the naming pattern `*.spec.js`.

#### 3. Job Timeout

```
Error: Timeout waiting for jobs to complete after 1800 seconds
```

**Solution**: Increase `MAX_WAIT_TIME` or check if tests are hanging.

#### 4. Permission Denied

```
Error: Failed to submit job: 403 Forbidden
```

**Solution**: Verify organization permissions and API credentials.

### Debug Mode

Enable debug logging by adding to workflow:

```yaml
env:
  DEBUG: "true"
  QGJOB_VERBOSE: "true"
```

### Manual Testing

Test the CLI locally before committing:

```bash
# Install CLI
cd cli && pip install -e .

# Test server connection
qgjob health

# Submit a test job
qgjob submit --org-id=test --app-version-id=v1 --test=tests/sample.spec.js

# Monitor status
qgjob status --job-id=abc123 --watch
```

## Best Practices

### 1. Test Organization

- Group related tests in subdirectories
- Use descriptive test file names
- Keep test suites focused and independent

### 2. Resource Management

- Use appropriate priorities for different test types
- Consider target platform availability
- Monitor job queue capacity

### 3. Failure Handling

- Set up notifications for test failures
- Implement retry logic for flaky tests
- Monitor timeout patterns

### 4. Performance Optimization

- Minimize test execution time
- Parallelize where possible
- Use job grouping effectively

## Security Considerations

### 1. Secrets Management

- Store sensitive data in GitHub Secrets
- Use environment-specific servers
- Rotate credentials regularly

### 2. Network Access

- Ensure secure communication with job server
- Consider IP whitelisting for production
- Use HTTPS for all API calls

### 3. Test Data

- Avoid hardcoded credentials in tests
- Use test-specific data isolation
- Clean up test artifacts

## Advanced Usage

### Custom Workflow Variants

Create specialized workflows for different scenarios:

#### Smoke Tests Only

```yaml
name: Smoke Tests
on:
  schedule:
    - cron: "0 */6 * * *" # Every 6 hours
env:
  TEST_FILTER: "tests/smoke/"
  PRIORITY: "urgent"
```

#### Performance Tests

```yaml
name: Performance Tests
on:
  workflow_dispatch:
env:
  TARGET: "browserstack"
  TEST_FILTER: "tests/performance/"
```

#### Multi-Environment Testing

```yaml
strategy:
  matrix:
    environment: [staging, production]
    target: [emulator, device, browserstack]
env:
  QGJOB_SERVER_URL: ${{ matrix.environment == 'staging' && secrets.STAGING_SERVER || secrets.PROD_SERVER }}
  TARGET: ${{ matrix.target }}
```

### Integration with Other Tools

#### Slack Notifications

```yaml
- name: Notify Slack
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    text: "AppWright tests failed for ${{ github.sha }}"
```

#### Test Result Publishing

```yaml
- name: Publish results
  uses: dorny/test-reporter@v1
  with:
    name: AppWright Tests
    path: test-results.xml
    reporter: jest-junit
```

This comprehensive GitHub Actions integration provides a robust foundation for automated testing with the QualGent Job system.
