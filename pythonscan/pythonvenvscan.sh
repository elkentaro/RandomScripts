#!/bin/bash
# find_venvs.sh - Find all Python virtual environments and identify what uses them
# Usage: ./find_venvs.sh [search_root]
#        Default search root: /

set +e  # Don't exit on errors - many commands in the loop may return non-zero legitimately

SEARCH_ROOT="${1:-/}"
BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
DIM='\033[2m'
RESET='\033[0m'

echo -e "${BOLD}🐍 Python Virtual Environment Scanner${RESET}"
echo -e "${DIM}Searching from: ${SEARCH_ROOT}${RESET}"
echo -e "${DIM}Scanning all subdirectories recursively (including hidden dirs like .venv)${RESET}"
echo -e "${DIM}Skipping: /proc, /sys, /dev, /run, /snap${RESET}"
echo ""

# Find venvs by looking for the pyvenv.cfg marker file (definitive venv indicator)
# Also check for conda environments via conda-meta
found=0

while IFS= read -r cfg_file; do
    venv_dir="$(dirname "$cfg_file")"
    found=$((found + 1))

    # --- Basic Info ---
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}📁 ${venv_dir}${RESET}"

    # Python version from pyvenv.cfg
    py_version=$(grep -i '^version' "$cfg_file" 2>/dev/null | head -1 | cut -d'=' -f2 | xargs)
    base_prefix=$(grep -i '^home' "$cfg_file" 2>/dev/null | head -1 | cut -d'=' -f2 | xargs)
    if [[ -n "$py_version" ]]; then
        echo -e "   ${GREEN}Python:${RESET} ${py_version} (base: ${base_prefix:-unknown})"
    fi

    # Size
    venv_size=$(du -sh "$venv_dir" 2>/dev/null | cut -f1)
    echo -e "   ${GREEN}Size:${RESET} ${venv_size}"

    # Creation / last modified time
    created=$(stat -c '%w' "$venv_dir" 2>/dev/null || stat -c '%y' "$venv_dir" 2>/dev/null | cut -d'.' -f1)
    modified=$(stat -c '%y' "$venv_dir" 2>/dev/null | cut -d'.' -f1)
    echo -e "   ${GREEN}Modified:${RESET} ${modified}"

    # --- Installed Packages ---
    pip_exe=""
    for candidate in "$venv_dir/bin/pip" "$venv_dir/Scripts/pip.exe" "$venv_dir/bin/pip3"; do
        if [[ -x "$candidate" ]]; then
            pip_exe="$candidate"
            break
        fi
    done

    if [[ -n "$pip_exe" ]]; then
        pkg_count=$("$pip_exe" list --format=columns 2>/dev/null | tail -n +3 | wc -l)
        echo -e "   ${GREEN}Packages:${RESET} ${pkg_count} installed"

        # Show top-level (non-dependency) packages if pipdeptree isn't available, just list all
        echo -e "   ${GREEN}Key packages:${RESET}"
        "$pip_exe" list --format=columns 2>/dev/null | tail -n +3 | \
            grep -ivE '^(pip |setuptools |wheel |pkg.resources)' | \
            head -15 | while read -r line; do
                echo -e "      ${DIM}${line}${RESET}"
            done
        remaining=$("$pip_exe" list --format=columns 2>/dev/null | tail -n +3 | grep -ivEc '^(pip |setuptools |wheel |pkg.resources)' || true)
        if [[ "${remaining:-0}" -gt 15 ]]; then
            echo -e "      ${DIM}... and $((remaining - 15)) more${RESET}"
        fi
    fi

    # --- What Uses This Venv ---
    echo -e "   ${GREEN}Used by:${RESET}"
    parent_dir="$(dirname "$venv_dir")"
    venv_name="$(basename "$venv_dir")"
    found_usage=false

    # 1. Check parent directory for project indicators
    for indicator in "setup.py" "setup.cfg" "pyproject.toml" "requirements.txt" "Pipfile" "poetry.lock" "Makefile" "README.md" "README.rst"; do
        if [[ -f "$parent_dir/$indicator" ]]; then
            if [[ "$found_usage" == false ]]; then
                project_name=$(basename "$parent_dir")
                echo -e "      ${YELLOW}📦 Project:${RESET} ${project_name} (${parent_dir})"
                found_usage=true
            fi
            echo -e "         ${DIM}↳ detected via: ${indicator}${RESET}"
        fi
    done

    # 2. Check if any systemd services reference this venv
    if command -v systemctl &>/dev/null; then
        while IFS= read -r service_file; do
            if [[ -f "$service_file" ]] && grep -ql "$venv_dir" "$service_file" 2>/dev/null; then
                svc_name=$(basename "$service_file")
                svc_status=$(systemctl is-active "$svc_name" 2>/dev/null || echo "unknown")
                echo -e "      ${YELLOW}⚙️  Systemd service:${RESET} ${svc_name} (${svc_status})"
                found_usage=true
            fi
        done < <(find /etc/systemd/system /usr/lib/systemd/system -name '*.service' 2>/dev/null)
    fi

    # 3. Check if any crontab entries reference this venv
    cron_hits=$(crontab -l 2>/dev/null | grep -c "$venv_dir" || true)
    if [[ "$cron_hits" -gt 0 ]]; then
        echo -e "      ${YELLOW}⏰ Crontab:${RESET} ${cron_hits} cron job(s) reference this venv"
        crontab -l 2>/dev/null | grep "$venv_dir" | while read -r cron_line; do
            echo -e "         ${DIM}↳ ${cron_line}${RESET}"
        done
        found_usage=true
    fi

    # Also check system-wide crontabs
    for cronfile in /etc/crontab /etc/cron.d/*; do
        if [[ -f "$cronfile" ]] && grep -ql "$venv_dir" "$cronfile" 2>/dev/null; then
            echo -e "      ${YELLOW}⏰ System cron:${RESET} $(basename "$cronfile")"
            found_usage=true
        fi
    done

    # 4. Check if any running processes use this venv
    proc_hits=$(ps aux 2>/dev/null | grep "$venv_dir" | grep -vc grep || true)
    if [[ "$proc_hits" -gt 0 ]]; then
        echo -e "      ${YELLOW}🔄 Active processes:${RESET}"
        ps aux 2>/dev/null | grep "$venv_dir" | grep -v grep | while read -r proc_line; do
            pid=$(echo "$proc_line" | awk '{print $2}')
            cmd=$(echo "$proc_line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
            echo -e "         ${DIM}PID ${pid}: ${cmd}${RESET}"
        done
        found_usage=true
    fi

    # 5. Check supervisor configs
    for sup_conf in /etc/supervisor/conf.d/*.conf /etc/supervisord.d/*.ini; do
        if [[ -f "$sup_conf" ]] && grep -ql "$venv_dir" "$sup_conf" 2>/dev/null; then
            echo -e "      ${YELLOW}📋 Supervisor:${RESET} $(basename "$sup_conf")"
            found_usage=true
        fi
    done

    # 6. Check Docker-related files in parent
    for dfile in "$parent_dir/Dockerfile" "$parent_dir/docker-compose.yml" "$parent_dir/docker-compose.yaml"; do
        if [[ -f "$dfile" ]]; then
            echo -e "      ${YELLOW}🐳 Docker:${RESET} $(basename "$dfile") found in project"
            found_usage=true
        fi
    done

    # 7. Check for shell scripts in parent that activate the venv
    while IFS= read -r sh_file; do
        if grep -ql "$venv_name/bin/activate\|$venv_dir" "$sh_file" 2>/dev/null; then
            echo -e "      ${YELLOW}📜 Script:${RESET} $(basename "$sh_file")"
            found_usage=true
        fi
    done < <(find "$parent_dir" -maxdepth 2 \( -name '*.sh' -o -name '*.bash' \) 2>/dev/null)

    if [[ "$found_usage" == false ]]; then
        echo -e "      ${DIM}⚠️  No active usage detected (possibly orphaned)${RESET}"
    fi

    echo ""

done < <(find "$SEARCH_ROOT" \
    \( -path /proc -o -path /sys -o -path /dev -o -path /run -o -path /snap \) -prune \
    -o -name 'pyvenv.cfg' -print \
    2>/dev/null)

# Also scan for conda environments
if command -v conda &>/dev/null; then
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}🐍 Conda Environments${RESET}"
    conda env list 2>/dev/null | grep -v '^#' | grep -v '^$' | while read -r env_name env_path rest; do
        if [[ -n "$env_path" ]]; then
            echo -e "   ${CYAN}${env_name}${RESET} → ${env_path}"
            found=$((found + 1))
        fi
    done
    echo ""
fi

echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}Total virtual environments found: ${found}${RESET}"
