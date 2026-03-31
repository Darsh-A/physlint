# physlint — Neovim plugin

Provides real-time physical unit diagnostics and hover info for Python files via Neovim's built-in LSP client.

## Prerequisites

physlint must be installed in your Python environment:

```bash
pip install physlint          # core only
pip install "physlint[lsp]"   # with LSP server dependencies
```

## Install

### lazy.nvim

```lua
{
  dir = "path/to/phylint/src/plugins/nvim",
  ft = "python",
  opts = {
    python_path = "python",  -- python interpreter with physlint installed
  },
}
```

Or point at the repo directly:

```lua
{
  "Darsh-A/physlint",
  ft = "python",
  opts = {},
}
```

### Manual (no plugin manager)

Add this to your `init.lua`:

```lua
vim.opt.runtimepath:append("path/to/phylint/src/plugins/nvim")
require("physlint").setup()
```

## Configuration

```lua
require("physlint").setup({
  python_path = "python",   -- path to python with physlint[lsp] installed
  enabled = true,           -- set false to disable entirely
  autostart = true,         -- attach automatically on FileType python
  filetypes = { "python" }, -- file types to attach to
})
```

## How it works

On opening a Python file, the plugin starts `python -m physlint.lsp` as an LSP server using Neovim's built-in `vim.lsp.start()`. Diagnostics appear inline, and you can hover over variables to see their inferred units.

The server looks for `physlint.toml` in the project root for configuration.
