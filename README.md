# 🧠 GenCommit

> **AI-powered Git commit assistant** that generates smart, clean commit messages using **Anthropic Claude API** — directly from your terminal.

---

## 🚀 Features

• Reads your **staged Git diff** (including new files)  
• Uses **Claude AI** to generate **conventional commit messages**  
• Lets you **accept, edit, or reject** interactively  
• Works offline in **mock mode** (`--mock`) — produces **simulated (fictive)** commit messages for testing  
• Simple, fast, and works in any Git repository

---

## ⚙️ Installation

```bash
# Clone the repository
git clone https://github.com/oussamaachahboune/gencommit.git
cd gencommit

# Install locally
pip install -e .
```

> 💡 Once installed, you can run `gencommit` from anywhere in your terminal.

---

## 💡 Usage

Run it inside any Git project **after staging changes**:

```bash
git add .
gencommit
```

Example output:

```
Suggested commit message:
----------------------------------------
feat: improve user input validation
----------------------------------------
Do you want to (a)ccept, (e)dit, or (r)eject?
```

---

## 🧰 Flags

| Flag        | Description                                                        |
| ----------- | ------------------------------------------------------------------ |
| `--mock`    | Offline mode — generates **fake/simulated messages** (no API call) |
| `--dry-run` | Show what would happen but don’t commit                            |
| `--model`   | Specify a Claude model manually                                    |
| `--debug`   | Show debug logs                                                    |
| `--version` | Show version info                                                  |

---

## 🔑 Environment

| Variable            | Description                                  |
| ------------------- | -------------------------------------------- |
| `ANTHROPIC_API_KEY` | Required — your Claude API key               |
| `EDITOR`            | Optional — your text editor (default: `vim`) |

> ⚠️ Keep your API key private. Never commit it to GitHub or share it publicly.

---

## 🧠 Requirements

- Python 3.8+
- Git
- Anthropic API key
