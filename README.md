# physlint

Static analysis for physical unit consistency in Python. Reads unit annotations, propagates them through arithmetic via AST traversal, and flags dimensional or scale mismatches — all without executing your code.

## Install

### pip (from GitHub)

```bash
python -m pip install git+https://github.com/Darsh-A/physlint.git
```

### pip (local clone)

```bash
git clone https://github.com/Darsh-A/physlint.git
cd physlint
python -m pip install .
```

### pre-commit (no install needed)

Add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Darsh-A/physlint
    rev: v0.1.0
    hooks:
      - id: physlint
```

When you run `pre-commit install`, this registers physlint as a git hook. On every commit, pre-commit clones the repo, installs physlint into an isolated virtualenv automatically (using `pyproject.toml`), and runs `physlint` against your staged `.py` files. If any unit error is found the commit is blocked. You don't need to install physlint yourself — pre-commit manages the entire lifecycle.

You can also run it manually without committing:

```bash
pre-commit run physlint --all-files
```

## Adding to your project

1. Install physlint (any method above).
2. Annotate your Python files with units (see below).
3. Run `physlint your_file.py` or `physlint src/ -r` for a whole directory.
4. Optionally copy `physlint.example.toml` from the repo into your project root as `physlint.toml` to configure behavior. Every option is documented in that file.

## Annotating units

Three styles — pick whichever fits:

```python
from typing import Annotated

# Annotated style (recommended — works with Pylance/mypy)
velocity: Annotated[float, "m/s"] = 20.0
mass: Annotated[float, "kg"] = 5.0

# bare string style (shorter, but type checkers will complain)
acceleration: "m/s^2" = 9.81

# trailing comment style
gravity = 9.81  # m/s^2
```

`Annotated` is the recommended style — type checkers see `float` and stay happy, physlint reads the unit from the metadata.

Units propagate through arithmetic automatically:

```python
force = mass * acceleration  # inferred: kg*m/s^2 (N)
distance = velocity * time   # inferred: m
```

Functions work too:

```python
def kinetic_energy(m: Annotated[float, "kg"], v: Annotated[float, "m/s"]) -> Annotated[float, "J"]:
    return 0.5 * m * v ** 2
```

## CLI

```bash
physlint file.py                    # default text output
physlint file.py --json             # JSON output
physlint src/ -r                    # recursive directory scan
physlint file.py --no-strict-scale  # allow km + m without warning
physlint file.py --ignore-prefix _  # skip variables starting with _
physlint file.py --config path/to/physlint.toml
```

### Diagnostics

| Code | Level | Meaning |
|---|---|---|
| `UNIT_MISMATCH` | error | adding/subtracting incompatible dimensions |
| `UNIT_CONFLICT` | error | annotation contradicts inferred unit |
| `SCALE_MISMATCH` | warning | same dimensions, different prefix scale |
| `SCALE_CONFLICT` | warning | annotation scale contradicts expression |
| `UNIT_INFERRED` | info | unit successfully inferred from context |

Exit code `1` when any error or warning is present, `0` otherwise.

## Editor integration

Install physlint with LSP support first:

```bash
python -m pip install "physlint[lsp]"
```

### VS Code

Build and install the extension:

```bash
cd physlint/src/plugins/vscode
npm install
npm run compile
npm run package
```

In VS Code: **Extensions** > **...** > **Install from VSIX...** > select `physlint-0.1.0.vsix`.

The extension auto-detects your Python interpreter — it checks the ms-python extension's selected interpreter first, then looks for a `.venv` in your workspace. If neither works, set `physlint.pythonPath` in VS Code settings to the Python that has `physlint[lsp]` installed.

If the server fails to start, you'll get an error notification with options to view the log or open settings. You can also use the command palette (`Ctrl+Shift+P`):

- **physlint: Restart Server** — restart after changing settings or reinstalling
- **physlint: Show Output** — view the server log

| Setting | Default | Description |
|---|---|---|
| `physlint.pythonPath` | `"python"` | Python interpreter (auto-detects if left as default) |
| `physlint.enable` | `true` | Enable/disable the extension |

### Neovim

#### lazy.nvim (from cloned repo)

```lua
{
  dir = "/absolute/path/to/physlint/src/plugins/nvim",
  ft = "python",
  opts = {
    python_path = "python",
  },
}
```

#### Manual (no plugin manager)

```lua
vim.opt.runtimepath:append("/absolute/path/to/physlint/src/plugins/nvim")
require("physlint").setup()
```

#### Options

```lua
require("physlint").setup({
  python_path = "python",   -- path to python with physlint[lsp] installed
  enabled = true,           -- set false to disable entirely
  autostart = true,         -- attach automatically on FileType python
  filetypes = { "python" }, -- file types to attach to
})
```

## Supported units

**Base SI**: m, kg, s, A, K, mol, cd

**Derived**: Hz, N, Pa, J, W, V, Ω, C, F, T, Wb, lm, lx, Gy, kat

**Prefixes**: Y Z E P T G M k h da d c m μ n p f a z y

**Aliases**: g, L, min, hr, day, eV, bar, atm, cal, Å, au, ly, mph, rpm, dB, ppm, rad, °, sr

Expressions support `*`, `/`, `^`/`**`, and parentheses: `kg*m/s^2`, `kg/(A*s^2)`, `m^2`.

### ASCII alternatives

Every Greek letter and special character has a plain ASCII name you can type instead:

| Symbol | ASCII | Example |
|---|---|---|
| `Ω` | `Ohm` or `ohm` | `V/ohm` instead of `V/Ω` |
| `μ` (prefix) | `u` or `mu` | `us`, `mus` instead of `μs` |
| `Å` | `angstrom` | `angstrom` instead of `Å` |
| `°` | `deg` | `deg` instead of `°` |

## Development

```bash
git clone https://github.com/Darsh-A/physlint.git
cd physlint
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev,lsp]"
pytest
```
