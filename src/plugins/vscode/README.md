# physlint — VS Code extension

Real-time physical unit diagnostics and hover info for Python files.

## Install

**1. Install physlint with LSP support:**

```bash
python -m pip install "physlint[lsp]"
```

**2. Build and install the extension:**

```bash
cd src/plugins/vscode
npm install
npm run compile
npm run package          # produces physlint-0.1.0.vsix
```

In VS Code: **Extensions** > **...** > **Install from VSIX...** > select `physlint-0.1.0.vsix`.

**3. Open a Python file** — the extension activates automatically.

## Python detection

The extension finds your Python interpreter in this order:

1. `physlint.pythonPath` setting (if you set it explicitly)
2. The ms-python extension's selected interpreter (`python.defaultInterpreterPath`)
3. A local `.venv/bin/python` or `venv/bin/python` in the workspace
4. Falls back to `python`

If the LSP server can't start, you'll get an error with options to view the output log or open settings.

## Commands

Open the command palette (`Ctrl+Shift+P`) and type `physlint`:

- **physlint: Restart Server** — restart the LSP server after changing settings or reinstalling
- **physlint: Show Output** — open the output log for debugging

## Settings

| Setting | Default | Description |
|---|---|---|
| `physlint.pythonPath` | `"python"` | Python interpreter with `physlint[lsp]` installed |
| `physlint.enable` | `true` | Enable/disable the extension |
