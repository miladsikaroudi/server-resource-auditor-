---
name: server-resource-auditor
description: |
  Daily server audit for shared machine courtesy and cleanup. Generates reports on active users and resource usage, flags stale files and unused Docker images for deletion, and monitors resource consumption to stay within 60% max (even weekends). Run daily or hourly as a side-check for active sessions. Use this whenever you need to: audit who's using the server and how much, check if you can safely use resources (respecting Bryan Sundhal, Peter Chen, Kirk Gossage if active), find stale driver downloads and build artifacts, identify Docker images unused 12+ months, or get a cleanup report for the team.
---

# Server Resource Auditor

A daily audit skill for shared server machines. Monitors active users, resource usage, stale files, and Docker cleanup opportunities while respecting team courtesy rules and maintaining a hard 60% resource cap.

## How It Works

Run this skill daily (or hourly as a side-check). It will:

1. **Identify active users** — detect who's logged in and using the server
2. **Show resource usage** — CPU, memory, disk for each active user
3. **Apply courtesy rules:**
   - If Bryan Sundhal, Peter Chen, or Kirk Gossage are active → stay below 40% resources
   - If server is idle (weekends) → you can use up to 60% max
   - **Hard cap: never exceed 60% resource usage**
4. **Find stale files** — scan for old driver downloads, redundant cache, build artifacts
5. **Audit Docker images** — flag images unused 12+ months, list owner for cleanup request
6. **Generate a report** — structured, ready to share with the team

## Running the Audit

### Full Daily Audit

```bash
server-audit daily
```

Produces: active users, resource snapshot, stale files found, Docker cleanup list, courtesy status.

### Hourly Side-Check

```bash
server-audit check
```

Runs quickly: just shows active users + resource usage. Use this in a cron job or loop to monitor every hour.

### Cleanup Report Only

```bash
server-audit cleanup
```

Returns stale files and Docker images only—useful for standalone cleanup runs.

## What the Audit Checks

### Active Users & Resources
- User names (who's logged in)
- CPU threads in use (out of 64 available)
- Memory usage (percentage of total)
- Disk usage (top directories)
- Whether courtesy rules apply (is Bryan, Peter, or Kirk active?)

### Stale Files
Scans these locations for files older than 30 days:
- `/tmp/` — temporary builds, driver downloads
- `~/.cache/` — old build caches, package downloads
- `~/Downloads/` — redundant driver versions, old tools
- Project root `./build/`, `./dist/`, `./node_modules/` — stale artifacts

Returns: full path, size, age (days), recommended action (delete/archive).

### Docker Images
Checks image metadata for last-use date:
- Compares image creation date to 12-month threshold
- Lists owner (user who created or last pulled the image)
- Returns: image name, owner, created date, recommended action (ask owner to delete).

## Report Format

All outputs are Markdown, ready to paste into Slack, email, or a shared doc:

```
# Server Audit — [date]

## Active Users & Resource Usage
- Bryan Sundhal: 45 threads (70%), 28GB mem (55%)
  → **Courtesy applies** — you should stay ≤ 40% resources
- Kirk Gossage: 8 threads (12%), 5GB mem (10%)
- **Available for you**: 43 threads max (67%), but capped at 60% = ~38 threads

## Stale Files Detected
- `/tmp/old-driver-v1.2.exe` (347MB, 120 days old) → DELETE
- `~/.cache/npm-cache/` (1.2GB, 95 days old) → CLEAN
- `~/Downloads/tensorflow-old.tar.gz` (890MB, 200 days old) → DELETE

## Docker Images (12+ months unused)
- `ubuntu:20.04` (owner: sikaroudi, created 2023-03-15) → ask owner to delete
- `python:3.8-slim` (owner: unknown, created 2024-01-10) → orphaned, safe to delete
```

## Integration: Hourly Cron Check

To run hourly checks, add to your cron:

```bash
0 * * * * /path/to/server-audit check >> ~/.audit-logs/hourly.log 2>&1
```

This logs resource status every hour, no output unless issues arise.

## Notes

- **60% cap is hard** — even on weekends, never exceed 60% total resource usage
- **Courtesy threshold**: When Bryan, Peter, or Kirk are active, you stay below 40%
- **Stale file ages**: 30 days for general cache, 12 months for Docker images (tunable)
- **Reporting**: All output is plaintext Markdown; copy it and share with the team as-is

---

## What You Do with the Report

1. **Review the courtesy status** — if others are active, respect the limits
2. **Share stale file recommendations** with the team (ask owners to clean up)
3. **Request Docker image deletion** from owners listed in the Docker section
4. **Monitor your own usage** — run `server-audit check` hourly to stay under 60%
