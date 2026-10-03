#!/usr/bin/env python3
"""
Server Resource Auditor - Daily audit for shared machine courtesy and cleanup.
Monitors active users, resource usage, stale files, and Docker images.
"""

import subprocess
import os
import json
import psutil
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Configuration
COURTESY_USERS = ["Bryan Sundhal", "Peter Chen", "Kirk Gossage"]
MAX_RESOURCE_PERCENT = 60
COURTESY_RESOURCE_PERCENT = 40
STALE_FILE_DAYS = 30
DOCKER_UNUSED_MONTHS = 12
TOTAL_THREADS = 64

def get_active_users():
    """Detect active users on the server."""
    try:
        result = subprocess.run(['who'], capture_output=True, text=True, timeout=5)
        users = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split()
                username = parts[0]
                if username not in users:
                    users.append(username)
        return users
    except Exception as e:
        print(f"Error getting active users: {e}")
        return []

def get_user_resource_usage(username):
    """Get CPU and memory usage for a specific user."""
    try:
        cpu_percent = 0
        memory_percent = 0
        thread_count = 0

        for proc in psutil.process_iter(['username', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['username'] == username:
                    cpu_percent += proc.info['cpu_percent'] or 0
                    memory_percent += proc.info['memory_percent'] or 0
                    thread_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        return {
            'cpu_percent': min(cpu_percent, 100),
            'memory_percent': min(memory_percent, 100),
            'threads': thread_count
        }
    except Exception as e:
        print(f"Error getting resource usage for {username}: {e}")
        return {'cpu_percent': 0, 'memory_percent': 0, 'threads': 0}

def get_overall_resource_usage():
    """Get overall server resource usage."""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'available_threads': TOTAL_THREADS * (100 - psutil.cpu_percent(interval=1)) / 100
        }
    except Exception as e:
        print(f"Error getting overall resource usage: {e}")
        return {'cpu_percent': 0, 'memory_percent': 0, 'disk_percent': 0, 'available_threads': TOTAL_THREADS}

def find_stale_files():
    """Find stale files in common locations."""
    stale_files = []
    cutoff_date = datetime.now() - timedelta(days=STALE_FILE_DAYS)

    scan_dirs = [
        Path('/tmp'),
        Path.home() / '.cache',
        Path.home() / 'Downloads',
        Path.cwd() / 'build',
        Path.cwd() / 'dist',
    ]

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue

        try:
            for file_path in scan_dir.rglob('*'):
                if not file_path.is_file():
                    continue

                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_date:
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        age_days = (datetime.now() - mtime).days
                        stale_files.append({
                            'path': str(file_path),
                            'size_mb': round(size_mb, 2),
                            'age_days': age_days,
                            'recommendation': 'DELETE' if size_mb > 100 or age_days > 90 else 'REVIEW'
                        })
                except (OSError, PermissionError):
                    pass
        except (PermissionError, OSError):
            pass

    return sorted(stale_files, key=lambda x: x['age_days'], reverse=True)[:20]

def get_docker_images():
    """Get Docker images and their usage info."""
    try:
        result = subprocess.run(['docker', 'images', '--format', '{{json .}}'],
                              capture_output=True, text=True, timeout=10)
        images = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    img_data = json.loads(line)
                    images.append(img_data)
                except json.JSONDecodeError:
                    pass
        return images
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"Error getting Docker images: {e}")
        return []

def audit_docker_unused():
    """Find Docker images unused 12+ months."""
    unused = []
    images = get_docker_images()
    cutoff_date = datetime.now() - timedelta(days=30 * DOCKER_UNUSED_MONTHS)

    for img in images:
        try:
            created_str = img.get('CreatedAt', img.get('CreatedSince', ''))
            # Try to parse creation date
            if created_str:
                # Simple heuristic: if "months" or "years" in string, it's old
                if 'month' in created_str or 'year' in created_str:
                    unused.append({
                        'name': img.get('Repository', 'unknown'),
                        'tag': img.get('Tag', 'latest'),
                        'created': created_str,
                        'owner': 'unknown',  # Would need docker inspect for owner
                        'recommendation': 'Ask owner to delete'
                    })
        except Exception:
            pass

    return unused

def check_courtesy_applies():
    """Check if courtesy rules apply (are COURTESY_USERS active?)."""
    active = get_active_users()
    for user in COURTESY_USERS:
        if user in active:
            return True, user
    return False, None

def generate_report(mode='daily'):
    """Generate audit report."""
    report = []
    report.append(f"# Server Audit — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Active users and resources
    if mode in ['daily', 'check']:
        report.append("## Active Users & Resource Usage")
        active_users = get_active_users()
        overall = get_overall_resource_usage()
        courtesy_applies, courtesy_user = check_courtesy_applies()

        if active_users:
            for user in active_users:
                usage = get_user_resource_usage(user)
                report.append(f"\n- **{user}**: {usage['threads']} threads, "
                            f"{usage['cpu_percent']:.1f}% CPU, {usage['memory_percent']:.1f}% mem")

            if courtesy_applies:
                report.append(f"\n⚠️  **Courtesy applies** — {courtesy_user} is active")
                report.append(f"   → You should stay ≤ {COURTESY_RESOURCE_PERCENT}% resources")
        else:
            report.append("\n(No other active users detected)")

        report.append(f"\nServer status:")
        report.append(f"- Overall CPU: {overall['cpu_percent']:.1f}%")
        report.append(f"- Overall Memory: {overall['memory_percent']:.1f}%")
        report.append(f"- Overall Disk: {overall['disk_percent']:.1f}%")
        report.append(f"- **Hard cap**: Stay ≤ {MAX_RESOURCE_PERCENT}% (={int(TOTAL_THREADS * MAX_RESOURCE_PERCENT / 100)} threads)")

    # Stale files
    if mode in ['daily', 'cleanup']:
        report.append(f"\n## Stale Files Detected (older than {STALE_FILE_DAYS} days)")
        stale = find_stale_files()
        if stale:
            for f in stale[:10]:
                report.append(f"\n- `{f['path']}` ({f['size_mb']}MB, {f['age_days']} days old)")
                report.append(f"  → **{f['recommendation']}**")
        else:
            report.append("\n(No stale files found)")

    # Docker images
    if mode in ['daily', 'cleanup']:
        report.append(f"\n## Docker Images (unused 12+ months)")
        unused = audit_docker_unused()
        if unused:
            for img in unused[:10]:
                report.append(f"\n- `{img['name']}:{img['tag']}` (created {img['created']})")
                report.append(f"  → {img['recommendation']}")
        else:
            report.append("\n(No unused Docker images found)")

    return '\n'.join(report)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    if mode not in ['daily', 'check', 'cleanup']:
        mode = 'daily'

    print(generate_report(mode))
