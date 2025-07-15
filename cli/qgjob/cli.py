"""
QualGent Job CLI

Command-line interface for submitting and managing AppWright test jobs.
"""

import click
import requests
import time
import os
import sys
from typing import Optional, Dict, Any
from tabulate import tabulate
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

# Default configuration
DEFAULT_SERVER_URL = "http://localhost:8080"
DEFAULT_TIMEOUT = 30


class QGJobClient:
    """Client for communicating with the QualGent Job Server"""
    
    def __init__(self, server_url: str = DEFAULT_SERVER_URL, timeout: int = DEFAULT_TIMEOUT):
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def submit_job(self, org_id: str, app_version_id: str, test_path: str, 
                   target: str = "emulator", priority: str = "normal") -> Dict[str, Any]:
        """Submit a new test job"""
        payload = {
            "org_id": org_id,
            "app_version_id": app_version_id,
            "test_path": test_path,
            "target": target,
            "priority": priority
        }
        
        try:
            response = self.session.post(
                f"{self.server_url}/jobs",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"Failed to submit job: {e}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and details"""
        try:
            response = self.session.get(
                f"{self.server_url}/jobs/{job_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"Failed to get job status: {e}")
    
    def list_jobs(self, org_id: Optional[str] = None, status: Optional[str] = None,
                  app_version_id: Optional[str] = None) -> Dict[str, Any]:
        """List jobs with optional filtering"""
        params = {}
        if org_id:
            params['org_id'] = org_id
        if status:
            params['status'] = status
        if app_version_id:
            params['app_version_id'] = app_version_id
        
        try:
            response = self.session.get(
                f"{self.server_url}/jobs",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"Failed to list jobs: {e}")
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        try:
            response = self.session.get(
                f"{self.server_url}/stats",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"Failed to get server stats: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        try:
            response = self.session.get(
                f"{self.server_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"Server health check failed: {e}")


def get_client() -> QGJobClient:
    """Get a configured client instance"""
    server_url = os.environ.get('QGJOB_SERVER_URL', DEFAULT_SERVER_URL)
    timeout = int(os.environ.get('QGJOB_TIMEOUT', DEFAULT_TIMEOUT))
    return QGJobClient(server_url, timeout)


def print_success(message: str):
    """Print a success message in green"""
    click.echo(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")


def print_error(message: str):
    """Print an error message in red"""
    click.echo(f"{Fore.RED}✗ {message}{Style.RESET_ALL}", err=True)


def print_warning(message: str):
    """Print a warning message in yellow"""
    click.echo(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")


def print_info(message: str):
    """Print an info message in blue"""
    click.echo(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")


def format_status(status: str) -> str:
    """Format job status with colors"""
    status_colors = {
        "pending": Fore.YELLOW,
        "queued": Fore.CYAN,
        "running": Fore.BLUE,
        "completed": Fore.GREEN,
        "failed": Fore.RED,
        "cancelled": Fore.MAGENTA
    }
    
    color = status_colors.get(status.lower(), "")
    return f"{color}{status.upper()}{Style.RESET_ALL}"


@click.group()
@click.version_option(version="1.0.0")
@click.option('--server-url', envvar='QGJOB_SERVER_URL', default=DEFAULT_SERVER_URL,
              help='Server URL (can also use QGJOB_SERVER_URL env var)')
@click.pass_context
def main(ctx, server_url):
    """QualGent Job CLI - Submit and manage AppWright test jobs"""
    ctx.ensure_object(dict)
    ctx.obj['server_url'] = server_url


@main.command()
@click.option('--org-id', required=True, help='Organization ID')
@click.option('--app-version-id', required=True, help='App version ID')
@click.option('--test', 'test_path', required=True, help='Path to test file')
@click.option('--target', default='emulator', 
              type=click.Choice(['emulator', 'device', 'browserstack']),
              help='Target platform for test execution')
@click.option('--priority', default='normal',
              type=click.Choice(['low', 'normal', 'high', 'urgent']),
              help='Job priority')
@click.option('--wait', is_flag=True, help='Wait for job completion and show result')
@click.option('--poll-interval', default=5, help='Polling interval in seconds (when using --wait)')
@click.pass_context
def submit(ctx, org_id, app_version_id, test_path, target, priority, wait, poll_interval):
    """Submit a new test job"""
    
    # Validate test file exists
    if not os.path.exists(test_path):
        print_error(f"Test file not found: {test_path}")
        sys.exit(1)
    
    client = get_client()
    
    try:
        # Check server health first
        client.health_check()
        
        print_info(f"Submitting job...")
        print_info(f"  Organization: {org_id}")
        print_info(f"  App Version: {app_version_id}")
        print_info(f"  Test: {test_path}")
        print_info(f"  Target: {target}")
        print_info(f"  Priority: {priority}")
        
        result = client.submit_job(org_id, app_version_id, test_path, target, priority)
        
        job_id = result.get('job_id')
        print_success(f"Job submitted successfully!")
        print_info(f"Job ID: {job_id}")
        print_info(f"Status: {format_status(result.get('status', 'unknown'))}")
        
        if wait and job_id:
            print_info(f"Waiting for job completion (polling every {poll_interval}s)...")
            wait_for_completion(client, job_id, poll_interval)
        else:
            print_info(f"Use 'qgjob status --job-id {job_id}' to check status")
            
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


@main.command()
@click.option('--job-id', required=True, help='Job ID to check')
@click.option('--watch', is_flag=True, help='Watch job status (refresh every 5 seconds)')
@click.option('--poll-interval', default=5, help='Polling interval in seconds (when using --watch)')
def status(job_id, watch, poll_interval):
    """Check job status"""
    client = get_client()
    
    if watch:
        print_info(f"Watching job {job_id} (refresh every {poll_interval}s, Ctrl+C to stop)...")
        try:
            while True:
                show_job_status(client, job_id)
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            print_info("Stopped watching.")
    else:
        show_job_status(client, job_id)


@main.command()
@click.option('--org-id', help='Filter by organization ID')
@click.option('--status', help='Filter by job status')
@click.option('--app-version-id', help='Filter by app version ID')
@click.option('--limit', default=20, help='Maximum number of jobs to show')
def list(org_id, status, app_version_id, limit):
    """List jobs with optional filtering"""
    client = get_client()
    
    try:
        result = client.list_jobs(org_id, status, app_version_id)
        jobs = result.get('jobs', [])
        
        if not jobs:
            print_warning("No jobs found.")
            return
        
        # Limit results
        jobs = jobs[:limit]
        
        # Prepare table data
        headers = ['Job ID', 'Org ID', 'App Version', 'Test', 'Target', 'Status', 'Created']
        rows = []
        
        for job in jobs:
            payload = job.get('payload', {})
            rows.append([
                job.get('job_id', '')[:8] + '...',  # Truncate job ID
                payload.get('org_id', ''),
                payload.get('app_version_id', ''),
                os.path.basename(payload.get('test_path', '')),
                payload.get('target', ''),
                format_status(job.get('status', '')),
                job.get('created_at', '')[:19]  # Show date/time without microseconds
            ])
        
        print_info(f"Found {len(jobs)} jobs:")
        print(tabulate(rows, headers=headers, tablefmt='grid'))
        
        if len(result.get('jobs', [])) > limit:
            print_warning(f"Showing first {limit} jobs. Use --limit to show more.")
            
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


@main.command()
def stats():
    """Show server statistics"""
    client = get_client()
    
    try:
        stats = client.get_server_stats()
        
        print_info("Server Statistics:")
        
        # Job statistics
        job_stats = [
            ['Total Jobs', stats.get('total_jobs', 0)],
            ['Pending', stats.get('pending_jobs', 0)],
            ['Running', stats.get('running_jobs', 0)],
            ['Completed', stats.get('completed_jobs', 0)],
            ['Failed', stats.get('failed_jobs', 0)]
        ]
        
        print("\nJob Statistics:")
        print(tabulate(job_stats, headers=['Metric', 'Count'], tablefmt='simple'))
        
        # Worker statistics
        worker_stats = [
            ['Total Workers', stats.get('total_workers', 0)],
            ['Active Workers', stats.get('active_workers', 0)],
            ['Total Groups', stats.get('total_groups', 0)]
        ]
        
        print("\nWorker Statistics:")
        print(tabulate(worker_stats, headers=['Metric', 'Count'], tablefmt='simple'))
        
    except Exception as e:
        print_error(str(e))
        sys.exit(1)


@main.command()
def health():
    """Check server health"""
    client = get_client()
    
    try:
        health = client.health_check()
        
        if health.get('status') == 'healthy':
            print_success(f"Server is healthy")
            print_info(f"Version: {health.get('version', 'unknown')}")
            print_info(f"Timestamp: {health.get('timestamp', 'unknown')}")
        else:
            print_error(f"Server is unhealthy: {health}")
            sys.exit(1)
            
    except Exception as e:
        print_error(f"Server is unreachable: {e}")
        sys.exit(1)


def show_job_status(client: QGJobClient, job_id: str):
    """Show detailed job status"""
    try:
        job = client.get_job_status(job_id)
        payload = job.get('payload', {})
        
        # Clear screen for watch mode
        if os.name == 'nt':  # Windows
            os.system('cls')
        else:  # Unix/Linux/MacOS
            os.system('clear')
        
        print_info(f"Job Status: {job_id}")
        print("=" * 50)
        
        # Basic info
        info_rows = [
            ['Job ID', job.get('job_id', '')],
            ['Status', format_status(job.get('status', ''))],
            ['Organization', payload.get('org_id', '')],
            ['App Version', payload.get('app_version_id', '')],
            ['Test Path', payload.get('test_path', '')],
            ['Target', payload.get('target', '')],
            ['Priority', payload.get('priority', '')],
            ['Worker ID', job.get('worker_id', 'Not assigned')],
            ['Created', job.get('created_at', '')],
            ['Updated', job.get('updated_at', '')],
        ]
        
        if job.get('started_at'):
            info_rows.append(['Started', job.get('started_at', '')])
        
        if job.get('completed_at'):
            info_rows.append(['Completed', job.get('completed_at', '')])
        
        if job.get('error_message'):
            info_rows.append(['Error', job.get('error_message', '')])
        
        print(tabulate(info_rows, headers=['Field', 'Value'], tablefmt='simple'))
        
        # Show result if available
        if job.get('result'):
            print_info("\nJob Result:")
            result = job.get('result')
            if isinstance(result, dict):
                result_rows = [[k, v] for k, v in result.items()]
                print(tabulate(result_rows, headers=['Key', 'Value'], tablefmt='simple'))
            else:
                print(result)
                
    except Exception as e:
        print_error(str(e))


def wait_for_completion(client: QGJobClient, job_id: str, poll_interval: int):
    """Wait for job completion and show final result"""
    try:
        while True:
            job = client.get_job_status(job_id)
            status = job.get('status', '').lower()
            
            if status in ['completed', 'failed', 'cancelled']:
                print_info(f"\nJob finished with status: {format_status(status)}")
                
                if status == 'completed':
                    print_success("Job completed successfully!")
                    if job.get('result'):
                        print_info("Result:")
                        print(job.get('result'))
                elif status == 'failed':
                    print_error("Job failed!")
                    if job.get('error_message'):
                        print_error(f"Error: {job.get('error_message')}")
                    sys.exit(1)
                elif status == 'cancelled':
                    print_warning("Job was cancelled.")
                    sys.exit(1)
                break
            
            print_info(f"Status: {format_status(status)} (waiting...)")
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print_warning("\nStopped waiting. Job is still running.")
    except Exception as e:
        print_error(f"Error while waiting: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 