#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile
import argparse
from textwrap import dedent
from typing import List, Optional, Dict, Any

# requests is required for real API calls
try:
    import requests
except ImportError:
    requests = None

VERSION = "1.0.0"
DEBUG = False


# ----------------------
# Utilities / Git layer
# ----------------------
def debug(msg: str) -> None:
    """Print debug messages if DEBUG flag is set."""
    if DEBUG:
        print(f"DEBUG: {msg}", file=sys.stderr)


def run_cmd(cmd: List[str]) -> str:
    """Run a shell command and return stdout."""
    debug(f"run_cmd: {' '.join(cmd)}")
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return completed.stdout
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Error running command {' '.join(cmd)}: {e.stderr or e}")


def get_staged_diff() -> str:
    """Return the current staged git diff."""
    try:
        return run_cmd(["git", "diff", "--cached"])
    except SystemExit as e:
        sys.exit(f"Error getting git diff: {e}")


def get_new_staged_files() -> List[str]:
    """Return list of newly added staged files."""
    try:
        out = run_cmd(["git", "diff", "--cached", "--name-only", "--diff-filter=A"])
        return out.split()
    except SystemExit as e:
        sys.exit(f"Error getting new staged files: {e}")


def get_recent_commits(n: int = 3) -> str:
    """Return recent commit messages for context."""
    try:
        return run_cmd(["git", "log", f"-{n}", "--pretty=format:%B"])
    except SystemExit:
        return ""


def append_new_files_to_diff(diff: str, new_files: List[str]) -> str:
    """Append full content of new files to diff for better context."""
    for file in new_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            diff += f"\n--- /dev/null\n+++ b/{file}\n{content}\n"
        except Exception as e:
            sys.exit(f"Error reading file {file}: {e}")
    return diff


# ----------------------
# Prompt builder
# ----------------------
def build_prompt(diff: str, recent_commits: str) -> str:
    """Build the prompt to send to Claude API."""
    return dedent(
        f"""
    Generate a git commit message following this structure:
    1. First line: conventional commit format (type: concise description)
       (use types like feat, fix, docs, style, refactor, perf, test, chore, etc.)
    2. Optional bullet points for context:
       - Keep second line blank
       - Be concise and clear
       - Avoid long explanations
       - No fluff or quotes

    Recent commits from this repo (for style reference):
    {recent_commits}

    Here's the current diff:
    {diff}
    """
    )


# ----------------------
# Anthropic helpers
# ----------------------
def get_models_from_api(api_key: str) -> List[Dict[str, Any]]:
    """Fetch available models for this key. Returns list of model dicts or []"""
    if requests is None:
        debug("requests not installed; cannot query model list")
        return []
    try:
        resp = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            timeout=10,
        )
        if resp.status_code != 200:
            debug(f"/v1/models returned {resp.status_code}: {resp.text}")
            return []
        payload = resp.json()
        return payload.get("models") or payload.get("data") or []
    except Exception as e:
        debug(f"Error fetching models: {e}")
        return []


def pick_preferred_model(models: List[Dict[str, Any]]) -> Optional[str]:
    """Pick a preferred model string from models list (sonnet->opus->haiku)."""
    names = [m.get("id") or m.get("name") or m.get("model") or str(m) for m in models]
    for pref in ("sonnet", "opus", "haiku"):
        for n in names:
            if pref in n.lower() and "claude" in n.lower():
                return n
    for n in names:
        if "claude" in n.lower():
            return n
    return None


def call_claude_api(prompt: str, api_key: str, model: str, timeout: int = 30) -> str:
    """Send prompt to Anthropic Claude API using chosen model."""
    if requests is None:
        sys.exit(
            "The 'requests' library is required. Install it with: pip install requests"
        )

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    body = {
        "model": model,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }

    debug(f"Sending request to Claude API with model={model}...")
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()
    except requests.exceptions.RequestException as e:
        sys.exit(f"❌ Network/API error: {e}")
    except Exception as e:
        sys.exit(f"❌ Error parsing API response: {e}")


# ----------------------
# Mock for local testing
# ----------------------
def call_claude_api_mock(prompt: str, api_key: Optional[str] = None) -> str:
    """Offline mock for local testing without API key or Internet."""
    debug("Using MOCK API (no network call).")
    lines = prompt.splitlines()
    summary = "chore: update files"
    for l in lines:
        l_strip = l.strip()
        if l_strip.startswith("+++ b/"):
            fname = l_strip[len("+++ b/") :]
            summary = f"feat: update {fname}"
            break
        if "def " in l_strip and "(" in l_strip:
            summary = "feat: add/modify function"
            break
        if "fix" in l_strip.lower():
            summary = "fix: address bug found in diff"
            break
    bullets = []
    if "TODO" in prompt.upper():
        bullets.append("- Add TODO items")
    if "print(" in prompt:
        bullets.append("- Adjust debugging prints")
    if not bullets:
        bullets.append("- See diff for details")
    return summary + "\n\n" + "\n".join(bullets)


# ----------------------
# Message cleaner
# ----------------------
def clean_commit_message(msg: str) -> str:
    """Clean up model output (remove markdown formatting and extra quotes)."""
    msg = msg.strip()
    msg = msg.replace("```", "")
    msg = msg.strip('"').strip("'").strip()
    return msg


# ----------------------
# Editor & commit
# ----------------------
def open_editor(initial_message: str) -> str:
    """Open a text editor for the user to edit commit message."""
    editor = os.getenv("EDITOR", "vim")
    with tempfile.NamedTemporaryFile(
        suffix=".txt", delete=False, mode="w+", encoding="utf-8"
    ) as tmp:
        tmp.write(initial_message)
        tmp.flush()
        try:
            subprocess.run([editor, tmp.name])
        except FileNotFoundError:
            print(f"Editor '{editor}' not found — using original message.")
        tmp.seek(0)
        edited = tmp.read()
    try:
        os.unlink(tmp.name)
    except Exception:
        pass
    return edited


def commit_changes(message: str, dry_run: bool = False) -> None:
    """Run git commit with the given message."""
    debug("Running git commit...")
    if dry_run:
        print(f'[DRY-RUN] git commit -m "{message}"')
        return
    try:
        subprocess.run(["git", "commit", "-m", message], check=True)
        print("✅ Changes committed successfully!")
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error committing changes: {e}")


# ----------------------
# Main
# ----------------------
def main() -> None:
    global DEBUG
    parser = argparse.ArgumentParser(
        description="Generate Git commit messages using Claude (Anthropic)."
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logs")
    parser.add_argument(
        "--mock", action="store_true", help="Use mock API (no network call)"
    )
    parser.add_argument(
        "--model", type=str, default=None, help="Anthropic model id to use"
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't actually commit")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    args = parser.parse_args()

    DEBUG = args.debug
    use_mock = args.mock or os.getenv("GENCOMMIT_MOCK") == "1"

    if args.version:
        print(f"gencommit {VERSION}")
        sys.exit(0)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not use_mock and not api_key:
        sys.exit("❌ Error: ANTHROPIC_API_KEY not set. Use --mock for offline testing.")

    diff = get_staged_diff()
    new_files = get_new_staged_files()

    if not diff.strip() and not new_files:
        sys.exit("❌ No staged changes found. Use 'git add' first.")

    if new_files:
        diff = append_new_files_to_diff(diff, new_files)

    recent_commits = get_recent_commits(3)
    prompt = build_prompt(diff, recent_commits)

    chosen_model = args.model
    if not use_mock and not chosen_model:
        models = get_models_from_api(api_key)
        chosen_model = pick_preferred_model(models) or "claude-sonnet-4-5-20250929"
        debug(f"Using model: {chosen_model}")

    raw_message = (
        call_claude_api_mock(prompt, api_key)
        if use_mock
        else call_claude_api(prompt, api_key, chosen_model)
    )

    commit_message = clean_commit_message(raw_message)

    print("\nSuggested commit message:\n" + "-" * 40)
    print(commit_message)
    print("-" * 40)

    while True:
        choice = (
            input("\nDo you want to (a)ccept, (e)dit, or (r)eject? ").strip().lower()
        )
        if choice in ("a", "accept"):
            commit_changes(commit_message, dry_run=args.dry_run)
            break
        elif choice in ("e", "edit"):
            edited = open_editor(commit_message)
            commit_changes(edited, dry_run=args.dry_run)
            break
        elif choice in ("r", "reject"):
            print("❎ Commit message rejected. No changes committed. Exiting cleanly.")
            sys.exit(0)
        else:
            print("Invalid choice. Please enter a, e, or r.")


if __name__ == "__main__":
    main()
