# Tim's Neovim for GEEST DevShell

A practical, declarative Nix setup with:

- LSP + completion for **Python (PyQt5/6, Django), Nix (nixd), Bash**.
- On-save formatting: **Black**, **nixfmt**, **shfmt**.
- **UK English** spell-check.
- **GitHub Copilot** + **Copilot Chat** (presets: review / feature / refactor).
- **Kartoza** colourscheme.
- Powerline statusline with Nerd Font glyphs (use a Nerd Font in Kitty).
- **DAP** debugging for Python (debugpy).
- **Persistent clipboard** history across sessions (Telescope → `<leader>fy`).
- Toggleable file manager: **Neo-tree** (`<leader>e`).
- **Inline images** in Kitty via `image.nvim`.
- **Great Git**: Fugitive, Gitsigns, Diffview, **Octo** (PRs/issues).
- **Fun**: Minesweeper (`<leader>ms`), Cellular Automata rain (`<leader>zz`).

## Key shortcuts

- Leader is **Space**.
- File tree: `<leader>e`
- Files/Grep/Buffers: `<leader>ff`, `<leader>fg`, `<leader>fb`
- Clipboard history: `<leader>fy`
- Git: Fugitive `<leader>gg`, Diffview `<leader>gd` / close `<leader>gD`
- PRs/Issues (Octo): `<leader>gpr` (list), `<leader>gpc` (create)
- Copilot Chat (visual select code first):
  - Review: `<leader>cr`
  - Implement feature: `<leader>cf`
  - Refactor: `<leader>cx`
  - Toggle chat: `<leader>cc`
- Debug (Python): `F5/F10/F11/F12`, toggle UI: `<leader>du`, set BP: `<leader>db`
- Minesweeper: `<leader>ms`, Rain: `<leader>zz`

## Usage

When you enter the devShell with `nix develop`, the following will be available:

- `vim` / `vi` / `nvim` - all aliased to the configured Neovim
- `$EDITOR` and `$VISUAL` environment variables set to the configured Neovim

## Notes

- Ensure your terminal uses a **Nerd Font** for glyphs.
- Kitty ≥ 0.28 recommended for inline images.
- `gh auth login` once to enable Octo/Telescope-gh.
- For PyQGIS projects, point **Pyright** to your env/site-packages if needed via
  `python.analysis.extraPaths` in a local `pyrightconfig.json`.
