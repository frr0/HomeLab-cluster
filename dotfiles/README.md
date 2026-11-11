# Workstation Environment & Dotfiles

The primary workstation is engineered for high-productivity development and system administration, running **CachyOS Linux** (Arch-based with optimized BORE kernel scheduler and x86-64-v3 optimization).

## Architecture Highlights

- **Wayland Window Compositor**: **`niri`** (`~/.config/niri/config.kdl`) - an infinite horizontal scrollable tiling window manager providing a fluid, multi-window workflow without window overlapping or manual sizing friction.
- **Shell & UI System**: **`noctalia`** (`~/.config/noctalia/`) - integrated dark-themed system bar, application launcher, dock, lockscreen, and polkit agent.
- **Terminal Multiplexer**: **`alacritty`** (GPU-accelerated terminal) paired with **`tmux`** (custom leader `Ctrl+Space`, unified directional pane navigation shared with Neovim).
- **Interactive Shell**: **`zsh`** powered by **`starship`** prompt, `zsh-autosuggestions`, `zsh-syntax-highlighting`, and `zoxide` for fast directory jumping (`z`).
- **Editor Suite (LazyVim Style)**:
  - **Neovim**: Native LazyVim configuration (`~/.config/nvim/`).
  - **VS Code / Cursor**: Vim keybindings with custom WhichKey `Space` leader mapping mirroring Neovim muscle memory.
  - **IntelliJ IDEA**: Configured with `.ideavimrc` for unified code navigation.

## Idempotent Dotfiles Deployment

All dotfiles are tracked in a versioned repository with an idempotent installer script (`install.sh`) creating symlinks across both the development workstation and headless servers, ensuring consistent shell ergonomics across the entire infrastructure.
