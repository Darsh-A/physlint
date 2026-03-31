# physlint — VS Code extension

Provides real-time physical unit diagnostics and hover info for Python files.

## Prerequisites

physlint must be installed in the Python environment you're using:

```bash
pip install physlint          # core only
pip install "physlint[lsp]"   # with LSP server dependencies
```

## Install from source

```bash
cd src/plugins/vscode
npm install
npm run compile
npm run package          # produces physlint-0.1.0.vsix
```

Then in VS Code: `Extensions` → `...` → `Install from VSIX...` → select the `.vsix` file.

## Settings

| Setting | Default | Description |
|---|---|---|
| `physlint.pythonPath` | `"python"` | Python interpreter with physlint installed |
| `physlint.enable` | `true` | Enable/disable the extension |
