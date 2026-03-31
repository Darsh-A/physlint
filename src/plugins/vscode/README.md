# physlint — VS Code extension

Real-time physical unit diagnostics and hover info for Python files.

## Install

Install from the VS Code Marketplace — search **physlint** in the Extensions tab, or use the command line:

```bash
code --install-extension Darsh-A.physlint
```

That's it. The extension automatically installs everything it needs on first activation — no manual `pip install` required. Just open a Python file.

## Requirements

Python 3.11+ must be available on your system. The extension creates a private environment and installs `physlint` into it automatically.

## Commands

Open the command palette (`Ctrl+Shift+P`):

- **physlint: Restart Server** — restart the LSP server
- **physlint: Reinstall Server** — wipe the private environment and reinstall from scratch
- **physlint: Show Output** — view the server log

## Settings

| Setting | Default | Description |
|---|---|---|
| `physlint.pythonPath` | `"python"` | Override which Python is used to create the environment |
| `physlint.enable` | `true` | Enable/disable the extension |
