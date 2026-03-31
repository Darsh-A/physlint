local M = {}

M.defaults = {
  python_path = "python",
  enabled = true,
  autostart = true,
  filetypes = { "python" },
}

function M.setup(opts)
  opts = vim.tbl_deep_extend("force", M.defaults, opts or {})

  if not opts.enabled then
    return
  end

  vim.api.nvim_create_autocmd("FileType", {
    pattern = opts.filetypes,
    callback = function(ev)
      if not opts.autostart then
        return
      end

      local root = vim.fs.root(ev.buf, { "physlint.toml", "pyproject.toml", ".git" })

      vim.lsp.start({
        name = "physlint",
        cmd = { opts.python_path, "-m", "physlint.lsp" },
        root_dir = root,
        capabilities = vim.lsp.protocol.make_client_capabilities(),
      })
    end,
  })
end

return M
