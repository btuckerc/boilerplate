# Neovim Cheatsheet

Quick reference for the shared Neovim configuration in `boilerplate`.

## Core

| Keybinding | Action |
| --- | --- |
| `<leader>` | Leader key is `Space`. |
| `jk` / `kj` | `(Insert mode)` Exit insert mode. |
| `<leader>w` | Save the current file. |
| `<leader>L` | Open `lazy.nvim`. |
| `<leader>tt` | Toggle theme transparency. |

## Navigation

| Keybinding | Action |
| --- | --- |
| `-` | Open Oil in the current window. |
| `<leader>e` | Open Oil in the current window. |
| `<leader>ef` | Open Oil in a floating window. |
| `<leader>ev` | Open Oil in a vertical split. |
| `<leader>ff` | Find files with Telescope. |
| `<leader>fg` | Live grep with Telescope. |
| `<leader>fb` | Find open buffers. |
| `<leader>fh` | Find help tags. |
| `<leader>fr` | Find recent files. |
| `<leader>fs` | Find document symbols. |
| `<leader>fS` | Find workspace symbols. |
| `<leader>fm` | Find functions and methods. |
| `<leader>fc` | Find classes and structs. |

## Buffers, Windows, Tabs

| Keybinding | Action |
| --- | --- |
| `<S-h>` / `<S-l>` | Previous / next buffer. |
| `<leader>bd` | Delete the current buffer. |
| `<C-h/j/k/l>` | Navigate splits and tmux panes. |
| `<leader>wv` | Split vertically. |
| `<leader>wh` | Split horizontally. |
| `<leader>w=` | Equalize split sizes. |
| `<leader>wq` | Close the current split. |
| `<Up/Down/Left/Right>` | Resize the current split. |
| `<leader>tc` | New tab. |
| `<leader>tx` | Close tab. |
| `<leader>tn` / `<leader>tp` | Next / previous tab. |
| `<leader>ts` | Open current buffer in a new tab. |
| `<leader>tq` | Close other tabs. |

## Editing

| Keybinding | Action |
| --- | --- |
| `<leader>hc` | Clear search highlighting. |
| `<CR>` | Clear search highlights if active. |
| `<C-d>` / `<C-u>` | Scroll and recenter. |
| `n` / `N` | Next / previous match and recenter. |
| `J` / `K` | `(Visual mode)` Move selected lines down / up. |
| `<` / `>` | `(Visual mode)` Reselect after indenting. |
| `<leader>p` | Paste without overwriting the default register. |
| `<leader>y` / `<leader>Y` | Copy to the system clipboard. |
| `<leader>d` | Delete into the void register. |
| `<leader>+` / `<leader>-` | Increment / decrement numbers. |
| `<leader>u` | Toggle Undotree. |

## LSP and Diagnostics

| Keybinding | Action |
| --- | --- |
| `gd` | Go to definition. |
| `gr` | Find references. |
| `gI` | Go to implementation. |
| `gD` | Go to declaration. |
| `grt` | Go to type definition. |
| `K` | Hover documentation. |
| `<leader>rn` | Rename symbol. |
| `<leader>ca` | Code action. |
| `[d` / `]d` | Previous / next diagnostic. |
| `<leader>dp` / `<leader>dn` | Previous / next diagnostic. |
| `gl` | Open diagnostics for the current line. |
| `<leader>de` | Open the floating diagnostics window. |
| `<leader>dl` | Send diagnostics to the location list. |

## Git and Tools

| Keybinding | Action |
| --- | --- |
| `]c` / `[c` | Next / previous git hunk. |
| `<leader>hp` | Preview hunk. |
| `<leader>hr` | Reset hunk. |
| `<leader>hb` | Blame line. |
| `<leader>gg` | Open LazyGit. |
| `<leader>db` | Toggle Dadbod UI. |
| `<leader>xl` | Execute the current Lua file. |
