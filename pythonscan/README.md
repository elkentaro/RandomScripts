# find_venvs.sh

A bash script that recursively scans a directory tree to find all Python virtual environments, reports what's installed in each, and identifies what projects or services are using them.

## How It Works

The script locates virtual environments by searching for `pyvenv.cfg` files, which are the definitive marker that Python writes when creating a venv. This catches all naming conventions including `venv/`, `.venv/`, `env/`, `.env/`, or any custom name.

Hidden directories are included in the scan. Only pseudo-filesystems (`/proc`, `/sys`, `/dev`, `/run`, `/snap`) are skipped.

## Usage

```bash
# Make executable
chmod +x find_venvs.sh

# Scan entire system (use sudo for full access)
sudo ./find_venvs.sh /

# Scan home directory
./find_venvs.sh /home

# Scan a specific project area
./find_venvs.sh /opt/projects

# Default (no argument) scans from /
./find_venvs.sh
```

## What It Reports

For each virtual environment found:

### Environment Info
- **Path** — full path to the venv directory
- **Python version** — parsed from `pyvenv.cfg`
- **Disk size** — total size of the venv
- **Last modified** — timestamp of the venv directory
- **Installed packages** — count and list (up to 15, excluding pip/setuptools/wheel)

### Usage Detection

The script checks 7 sources to determine what's actively using each venv:

| Check | What It Looks For |
|-------|-------------------|
| **Project files** | `pyproject.toml`, `requirements.txt`, `setup.py`, `setup.cfg`, `Pipfile`, `poetry.lock`, `Makefile`, `README.md/rst` in the parent directory |
| **Systemd services** | Unit files in `/etc/systemd/system` and `/usr/lib/systemd/system` that reference the venv path, plus current service status |
| **Crontab** | User crontab and system-wide cron (`/etc/crontab`, `/etc/cron.d/`) entries referencing the venv |
| **Running processes** | Any active process with the venv path in its command line |
| **Supervisor** | Config files in `/etc/supervisor/conf.d/` and `/etc/supervisord.d/` |
| **Docker** | `Dockerfile` or `docker-compose.yml/yaml` in the parent directory |
| **Shell scripts** | `.sh` and `.bash` files (up to 2 levels deep in parent) that source the venv's `activate` script |

Venvs with no detected usage are flagged as **possibly orphaned**.

### Conda

If `conda` is available on the system, conda environments are listed separately at the end.

## Example Output

```
🐍 Python Virtual Environment Scanner
Searching from: /home
Scanning all subdirectories recursively (including hidden dirs like .venv)
Skipping: /proc, /sys, /dev, /run, /snap

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 /home/user/myproject/.venv
   Python: 3.11.6 (base: /usr/bin)
   Size: 142M
   Modified: 2025-01-20 14:32:01
   Packages: 47 installed
   Key packages:
      flask          3.0.0
      gunicorn       21.2.0
      requests       2.31.0
   Used by:
      📦 Project: myproject (/home/user/myproject)
         ↳ detected via: pyproject.toml
         ↳ detected via: requirements.txt
      ⚙️  Systemd service: myproject.service (active)
      ⏰ Crontab: 1 cron job(s) reference this venv
         ↳ 0 * * * * /home/user/myproject/.venv/bin/python cleanup.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 /home/user/old-experiment/venv
   Python: 3.9.7 (base: /usr/bin)
   Size: 89M
   Modified: 2024-03-15 09:11:44
   Packages: 12 installed
   Key packages:
      numpy          1.24.0
      pandas         2.0.3
   Used by:
      ⚠️  No active usage detected (possibly orphaned)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total virtual environments found: 2
```

## Requirements

- Bash 4+
- Standard coreutils (`find`, `grep`, `du`, `stat`, `ps`, `awk`)
- `pip` inside each venv (for package listing — gracefully skipped if missing)
- `systemctl` (optional — systemd checks skipped if unavailable)
- `conda` (optional — conda section skipped if unavailable)

## Notes

- Run with `sudo` for a full system scan; without it, permission-denied directories will be silently skipped.
- The script is read-only — it does not modify or delete anything.
- Large directory trees (like `/`) may take a minute or two depending on disk speed.
- Package listing invokes each venv's `pip`, which can be slow if there are many environments. The scan itself (finding `pyvenv.cfg`) is fast.
