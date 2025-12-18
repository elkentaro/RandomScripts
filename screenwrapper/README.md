# Interactive `screen` Wrapper Script

This setup replaces the normal `screen` command with an **interactive helper** that makes managing GNU Screen sessions easier and more memorable.

## What it does

When you run:

```bash
screen
```

You get an interactive menu that:

- Lists existing screen sessions
- Lets you **reconnect by number**
- Lets you **create a new named session**
- Falls back to normal `screen` behavior when flags are used

No more remembering `screen -ls`, `screen -r`, or `screen -S`.

---

## Requirements

- Linux
- GNU Screen installed
- Bash or Zsh
- Write access to your home directory

---

## Installation

### 1. Create a local `bin` directory

```bash
mkdir -p ~/bin
```

This directory will hold the wrapper script.

---

### 2. Create the wrapper script

Create a file named `screen`:

```bash
nano ~/bin/screen
```

Paste the following:

```bash
#!/usr/bin/env bash

REAL_SCREEN="/usr/bin/screen"

# If arguments are provided, behave exactly like normal screen
if [ "$#" -gt 0 ]; then
    exec "$REAL_SCREEN" "$@"
fi

# Collect existing sessions
mapfile -t SESSIONS < <(
    "$REAL_SCREEN" -ls 2>/dev/null | awk '/\t[0-9]+/{print $1}'
)

echo
echo "Screen sessions:"
if [ ${#SESSIONS[@]} -eq 0 ]; then
    echo "  (none)"
else
    for i in "${!SESSIONS[@]}"; do
        printf "  [%d] %s\n" "$i" "${SESSIONS[$i]}"
    done
fi
echo

read -rp "Enter session number to attach, or name for new session: " INPUT

# Numeric input → attach
if [[ "$INPUT" =~ ^[0-9]+$ ]] && [ "$INPUT" -lt "${#SESSIONS[@]}" ]; then
    exec "$REAL_SCREEN" -r "${SESSIONS[$INPUT]}"
fi

# Empty input → default screen behavior
if [ -z "$INPUT" ]; then
    exec "$REAL_SCREEN"
fi

# Otherwise → create named session
exec "$REAL_SCREEN" -S "$INPUT"
```

Make it executable:

```bash
chmod +x ~/bin/screen
```

---

### 3. Ensure `~/bin` is first in your PATH

Add the following to your shell configuration file.

**Bash**
```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Zsh**
```bash
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify:

```bash
which screen
```

Expected output:
```
/home/youruser/bin/screen
```

---

## Usage

Simply run:

```bash
screen
```

Example output:

```
Screen sessions:
  [0] 12345.screaming
  [1] 23456.scraper
  [2] 34567.hackingstuff

Enter session number to attach, or name for new session:
```

### Examples

| Input | Result |
|------|--------|
| `0` | Attach to session `12345.screaming` |
| `newjob` | Create a new session named `newjob` |
| *(Enter)* | Start a normal unnamed screen |
| `screen -ls` | Normal screen behavior |
| `screen -r name` | Normal screen behavior |

---

## Closing Screen Sessions

### From inside a screen session

- `exit` or `Ctrl+D` — closes the session cleanly
- `Ctrl+A k` — immediately kills the session

### From outside a screen session

```bash
screen -S sessionname -X quit
```

---

## Why this approach

- No fragile shell aliases
- Works over SSH and TTY
- Fully compatible with existing scripts
- Zero change to muscle memory

---

## Optional enhancements

Ideas for future improvements:

- Auto-attach when only one session exists
- Fuzzy matching by session name
- `fzf` integration
- Colorized output
- Session usage logging

---

## License

MIT — do whatever you want, just don’t blame me if you kill the wrong session 😉
