# Neovim Cheatsheet

This is a personalized cheatsheet for your Neovim configuration. It's designed to be a quick reference for the keybindings and concepts that are most important to your workflow.

## Core Concepts

- **Buffers**: In-memory representations of your files. Think of them as an open stack of papers on your desk. You can have many open without cluttering your view.
- **Windows**: Viewports into your buffers. Splits (`<C-w>s`, `<C-w>v`) create new windows.
- **Tabs**: A collection of windows. Use them to manage different layouts or workspaces, not individual files.

---

## 🌎 Global & Navigation

| Keybinding         | Action                                                                          |
| ------------------ | ------------------------------------------------------------------------------- |
| `<leader>`         | Your leader key is `Space`.                                                     |
| `kj`               | `(Insert Mode)` Exit insert mode.                                               |
| `-`                | Open file explorer (`oil.nvim`).                                                |
| `<leader>hc`       | Clear search highlights.                                                        |
| `<C-d>` / `<C-u>`  | Scroll down/up and center the view.                                             |
| `zz`               | Center the current line.                                                        |
| `<leader>u`        | Toggle Undotree (visual undo history).                                          |
| `<leader><leader>` | **(Most Important)** Fuzzy find open buffers. Your primary way to switch files. |

---

## ✂️ Clipboard & Text Manipulation (Yanking/Pasting)

Your configuration is set up to use the system clipboard by default. `y` is copy, `d` is cut.

| Keybinding    | Action                                                                  |
| ------------- | ----------------------------------------------------------------------- |
| `y`           | Yank (copy) to system clipboard.                                        |
| `d`           | Delete (cut) to system clipboard.                                       |
| `p` / `P`     | Paste after/before cursor.                                              |
| `x`           | Delete (cut) character under cursor.                                    |
| `c`           | Change (cut and enter insert mode).                                     |
| `> / <`       | Indent / un-indent selected text.                                       |
| `"+y` / `"+p` | Explicitly yank/paste to system clipboard (redundant but good to know). |

---

## 📂 Buffer & File Management

The main idea is to use Telescope (`<leader><leader>`) to jump between files, not cycle through them one-by-one.

| Keybinding            | Action                               |
| --------------------- | ------------------------------------ |
| `-`                   | Open file explorer (`oil.nvim`).     |
| From `oil.nvim`:      |                                      |
| `<CR>`                | Open file in the current window.     |
| `<C-v>`               | Open file in a new vertical split.   |
| `<C-s>`               | Open file in a new horizontal split. |
| `<S-L>` / `<S-H>`     | Go to next/previous buffer (linear). |
| `<leader>bd`          | Delete the current buffer.           |
| `<leader>fs`          | Save file.                           |
| `(Insert Mode) <C-s>` | Save file.                           |

---

## 🔭 Telescope (Fuzzy Finding)

| Keybinding         | Action                                 |
| ------------------ | -------------------------------------- |
| `<leader><leader>` | Find in open buffers.                  |
| `<leader>ff`       | Find any file in your project.         |
| `<leader>fg`       | Find text within any file (live grep). |
| `<leader>fb`       | Find recent files.                     |
| `<leader>fh`       | Find help tags.                        |

---

## 🖼️ Window & Tab Management

| Keybinding        | Action                                 |
| ----------------- | -------------------------------------- |
| `<C-w>s`          | Create horizontal split.               |
| `<C-w>v`          | Create vertical split.                 |
| `<C-w>w`          | Cycle through open windows.            |
| `<C-h/j/k/l>`     | Navigate to window left/down/up/right. |
| `<C-w>c`          | Close current window.                  |
| `<leader>sm`      | Maximize/minimize current split.       |
| `<leader>tn`      | Create a new tab.                      |
| `<leader>to`      | Close all other tabs.                  |
| `<leader>tl / th` | Go to next/previous tab.               |

---

## ✨ Key Plugin Functionality

| Keybinding      | Plugin                        | Action                          |
| --------------- | ----------------------------- | ------------------------------- |
| `<leader>gg`    | LazyGit                       | Open LazyGit interface.         |
| `<leader>gs`    | Gitsigns                      | Stage the current hunk.         |
| `<leader>gr`    | Gitsigns                      | Reset/revert the current hunk.  |
| `]h` / `[h`     | Gitsigns                      | Jump to next/previous git hunk. |
| `gitsigns.nvim` | See vertical bar for changes. |
| `<leader>ca`    | LSP                           | Code Actions.                   |
| `K`             | LSP                           | Show documentation for symbol.  |
| `gd`            | LSP                           | Go to definition.               |
| `<leader>cd`    | DAP                           | Continue debugger.              |
| `<leader>cb`    | DAP                           | Toggle breakpoint.              |
| `<leader>cr`    | DAP                           | Restart debugger.               |
