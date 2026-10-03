# Server Resource Auditor Skill

A daily audit skill for shared server machines. Monitors active users, resource usage, stale files, and Docker cleanup opportunities while respecting team courtesy rules.

## Setup

### 1. Install Dependencies

```bash
pip install psutil
```

### 2. Make the Script Executable

```bash
chmod +x server-audit
chmod +x scripts/audit.py
```

### 3. Add to Your PATH (Optional)

```bash
export PATH="$PATH:$(pwd)"
```

Or link it to a bin directory:
```bash
ln -s $(pwd)/server-audit ~/bin/server-audit
```

## Usage

### Daily Full Audit
```bash
./server-audit daily
# or
python3 scripts/audit.py daily
```

Shows: active users, resource usage, courtesy status, stale files, Docker unused images.

### Hourly Quick Check
```bash
./server-audit check
```

Shows: active users and resource usage only. Fast, suitable for cron.

### Cleanup Report Only
```bash
./server-audit cleanup
```

Shows: stale files and Docker images only.

## Setting Up Hourly Cron Job

Add to your crontab:

```bash
crontab -e
```

Then add:
```
0 * * * * /path/to/server-audit check >> ~/.audit-logs/hourly.log 2>&1
```

Create the log directory first:
```bash
mkdir -p ~/.audit-logs
```

## Configuration

Edit `scripts/audit.py` to adjust:

- **COURTESY_USERS**: List of users to trigger courtesy mode
- **MAX_RESOURCE_PERCENT**: Hard cap on resource usage (default: 60%)
- **COURTESY_RESOURCE_PERCENT**: Max when courtesy users active (default: 40%)
- **STALE_FILE_DAYS**: Threshold for stale file detection (default: 30 days)
- **DOCKER_UNUSED_MONTHS**: Threshold for unused Docker images (default: 12 months)
- **TOTAL_THREADS**: Total available threads on server (default: 64)

## Output Format

All reports are Markdown. Copy-paste ready for team distribution via Slack, email, or shared docs.

## Notes

- Requires Python 3.6+
- May need sudo for some Docker operations
- File scanning respects permission errors (won't crash if a file is inaccessible)
- Handles both `docker inspect` and simple image metadata
