# Clear Theme

The macOS Terminal **Clear Dark** and **Clear Light** profiles for VS Code,
Ghostty, herdr, tuicr, Neovim and Claude Code, so your editor and terminal look
just like Terminal.app.

![Clear Dark in front of Clear Light in VS Code](images/clear.png)

The colors are decoded straight from Terminal's own profiles. Terminal draws
them slightly translucent; in VS Code the background is opaque. One
departure: terminal colors that are hard to read on the background are
darkened or lightened just enough to be readable, keeping their hue. In Clear
Light that's most colors, and the normal ones take the hues the editor uses;
in Clear Dark it's red and bright black.

Also included, as a secondary pair: **Apple System Colors** and **Apple System
Colors Light**, matching Ghostty's bundled themes of the same name.

## VS Code

### Installation

The theme isn't on the VS Code Marketplace. Install it by cloning the repo into
your VS Code extensions folder:

```sh
git clone https://github.com/hyprsh/clear-theme.git \
  ~/.vscode/extensions/hyprsh.clear-theme-0.1.0
```

Then restart VS Code (or run **Developer: Reload Window**) and pick a theme with
**Preferences: Color Theme** (<kbd>Cmd</kbd>+<kbd>K</kbd> <kbd>Cmd</kbd>+<kbd>T</kbd>).

On Windows the extensions folder is `%USERPROFILE%\.vscode\extensions`. For
VS Code Insiders use `~/.vscode-insiders/extensions`, for VSCodium
`~/.vscode-oss/extensions`, and for Cursor `~/.cursor/extensions`.

To update:

```sh
git -C ~/.vscode/extensions/hyprsh.clear-theme-0.1.0 pull
```

To uninstall, delete that folder and reload VS Code.

### Usage

To switch between light and dark automatically with the system appearance,
add this to your `settings.json`:

```jsonc
"window.autoDetectColorScheme": true,
"workbench.preferredDarkColorTheme": "Clear Dark",
"workbench.preferredLightColorTheme": "Clear Light"
```

For the secondary themes, use `"Apple System Colors"` and
`"Apple System Colors Light"` instead.

If the theme doesn't switch, remove `"window.systemColorTheme"` from your
settings; any value other than the default stops VS Code from seeing the
system appearance.

### Recommended settings

The theme is designed for a minimal editor. These settings hide most of the
chrome around the code:

```jsonc
// Editor
"breadcrumbs.enabled": false,
"editor.glyphMargin": false,
"editor.guides.bracketPairs": false,
"editor.guides.indentation": false,
"editor.lightbulb.enabled": "off",
"editor.lineNumbers": "off",
"editor.minimap.enabled": false,
"editor.renderLineHighlight": "none",
"editor.scrollbar.horizontalScrollbarSize": 5,
"editor.scrollbar.useShadows": false,
"editor.scrollbar.verticalScrollbarSize": 10,
"editor.showFoldingControls": "mouseover",
"editor.stickyScroll.enabled": false,
"scm.diffDecorations": "gutter",

// Window
"window.commandCenter": false,
"workbench.activityBar.location": "hidden",
"workbench.browser.showInTitleBar": false,
"workbench.iconTheme": "vscode-modern-icons",
"workbench.layoutControl.enabled": false,
"workbench.navigationControl.enabled": false
```

With the activity bar hidden, open views from the command palette or with their
shortcuts (<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>E</kbd> for the Explorer,
<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>F</kbd> for Search). The scrollbar stays
hidden until you hover over it.

## Ghostty

Copy the theme files from the `ghostty` folder into Ghostty's themes folder:

```sh
mkdir -p ~/.config/ghostty/themes
cp ghostty/* ~/.config/ghostty/themes/
```

Then set the theme in your Ghostty config:

```
theme = light:Clear Light,dark:Clear Dark
```

For a Terminal-like translucent background, add:

```
background-opacity = 0.95
background-blur-radius = 20
```

Recommended settings to go with it:

```
cursor-style = block
shell-integration-features = no-cursor
macos-titlebar-proxy-icon = hidden
window-padding-balance = true
window-padding-x = 4
window-padding-y = 4
```

`no-cursor` stops Ghostty's shell integration from switching to a bar cursor at
the prompt, so `cursor-style` applies there too.

Ghostty already ships **Apple System Colors** and **Apple System Colors Light**,
so there are no files for those here.

## herdr

`herdr/clear.toml` gives [herdr](https://herdr.dev) Clear Light and Clear
Dark, switching with the terminal's light/dark appearance. It sets every color
herdr has, with the same grays and hues as the VS Code theme and its accent,
adjusted so the active tab's label stays readable; herdr's own `terminal`
theme assumes a dark background and is hard to read in Clear Light.

herdr can't include other files, so copy the file's contents into
`~/.config/herdr/config.toml`, replacing any `[theme]` section there, then
reload:

```sh
herdr server reload-config
```

Picking a theme in herdr's Settings turns off the automatic switching.

## tuicr

`tuicr/` has Clear Light and Clear Dark for [tuicr](https://tuicr.dev), with
the VS Code theme's colors: its grays, accent and hues, its syntax colors (in
the `.tmTheme` files) and its changed-line fills, made opaque. Copy the folder's
files into tuicr's themes folder:

```sh
mkdir -p ~/.config/tuicr/themes
cp tuicr/* ~/.config/tuicr/themes/
```

Then pick them in `~/.config/tuicr/config.toml`; tuicr takes the one that
matches the macOS appearance when it starts:

```toml
theme_light = "clear-light"
theme_dark = "clear-dark"
```

tuicr keeps the terminal's background (`transparent_background`, on by
default), so a translucent window stays translucent.

## Neovim

The repo is also a Neovim plugin with one colorscheme, `clear`: Clear Light
when `'background'` is `light`, Clear Dark when it's `dark`. Neovim sets
`'background'` from the terminal's background color, so with the Ghostty
theme above it follows the macOS appearance, and from Neovim 0.11 it switches
while running too. It has the VS Code theme's syntax colors and grays, sets
the terminal colors for `:terminal`, and covers the plugins
[LazyVim](https://www.lazyvim.org) comes with. It needs Neovim 0.10 or
later.

With [lazy.nvim](https://github.com/folke/lazy.nvim):

```lua
{
  "hyprsh/clear-theme",
  lazy = false,
  priority = 1000,
  config = function()
    vim.cmd.colorscheme("clear")
  end,
}
```

In LazyVim, add a file such as `lua/plugins/colorscheme.lua`:

```lua
return {
  { "hyprsh/clear-theme", lazy = true, priority = 1000 },
  { "LazyVim/LazyVim", opts = { colorscheme = "clear" } },
}
```

Don't set `'background'` in your config, or Neovim stops following the
terminal.

[lualine](https://github.com/nvim-lualine/lualine.nvim)'s `auto` theme
(LazyVim's default) picks up the matching statusline theme. For tabs on the
background like VS Code's, without a darker tab bar, use bufferline's minimal
preset:

```lua
{
  "akinsho/bufferline.nvim",
  opts = function(_, opts)
    opts.options.style_preset = require("bufferline").style_preset.minimal
  end,
}
```

## Claude Code

<!-- Screenshot placeholder: images/claude-code.png, Clear Dark in front of
Clear Light in Claude Code. -->

`claude-code/` has Clear Light and Clear Dark, and Apple System Colors and
Apple System Colors Light, as [custom
themes](https://code.claude.com/docs/en/terminal-config#create-a-custom-theme)
for [Claude Code](https://code.claude.com)'s interface. Each one starts from
Claude Code's own dark or light preset and replaces every color: the VS Code
theme's grays and hues for text, borders, modes and subagents, its
changed-line and changed-word fills (made opaque) for diffs, and faint grays
for your messages. Claude's orange becomes the palette's red, which is close
to it. They need Claude Code 2.1.246 or later; older versions ignore the diff
colors.

Copy the files into Claude Code's themes folder:

```sh
mkdir -p ~/.claude/themes
cp claude-code/*.json ~/.claude/themes/
```

Then run `/theme` in Claude Code and pick **Clear Dark** or **Clear Light**
(listed as `custom`). That saves `"theme": "custom:clear-dark"` (or
`custom:clear-light`) in Claude Code's config. If `~/.claude/themes` didn't
exist before, restart Claude Code once so it finds the folder; after that it
picks up changes while running.

Unlike the presets' **Auto (match terminal)**, a custom theme doesn't follow
the macOS appearance, so switch with `/theme` when you switch appearance.
Claude Code's syntax colors in diffs and code blocks aren't part of a theme;
they come from the preset (Monokai Extended in dark mode).

To have Claude Code follow the appearance, pick **Auto (match terminal)**
instead; you get Claude Code's own colors rather than Clear's. The **ANSI
colors only** presets are a middle way: they draw with the terminal's 16
colors, so with the Ghostty theme above they take Clear's hues, but their
grays and diff fills are coarser and they don't switch either.

## Font (optional)

To match macOS Terminal's font too, use **SF Mono Terminal**, the SF Mono
variant Terminal ships inside its app bundle. It isn't installed for other apps,
and copying the files into `~/Library/Fonts` isn't enough; install them with
Font Book:

```sh
cp /System/Applications/Utilities/Terminal.app/Contents/Resources/Fonts/SFMono*-Terminal.ttf /tmp/
open -a "Font Book" /tmp/SFMono-Terminal.ttf /tmp/SFMonoItalic-Terminal.ttf
```

Click **Install** in Font Book, then check that "SF Mono Terminal" appears in
its font list.

VS Code `settings.json` (the integrated terminal inherits the editor font):

```jsonc
"editor.fontFamily": "'SF Mono Terminal', ui-monospace, Menlo, monospace",
"editor.fontSize": 16,
"editor.lineHeight": 29,
"terminal.integrated.fontSize": 16,
"terminal.integrated.lineHeight": 1.5
```

Ghostty config:

```
font-family = SF Mono Terminal
font-size = 16
adjust-cell-height = 50%
```

This gives the editor and both terminals the same roomier line spacing. The
editor's `lineHeight` is in pixels because it multiplies the font size, while
the terminals multiply the font's taller natural line height. For the tighter
spacing Terminal.app uses, drop `adjust-cell-height` and the terminal
`lineHeight`, and set `editor.lineHeight` to 1.2.

Quit and reopen VS Code afterwards; a window reload doesn't pick up new fonts.
The installed copies don't update with macOS, so repeat the install after a
major update if you want Terminal's latest version.

## Development

The VS Code, Ghostty, herdr, tuicr, Neovim and Claude Code themes are
generated from `palettes.py`; edit it or `build.py`, then:

```sh
python3 build.py
```

To work on it, symlink your clone into the extensions folder and reload VS Code:

```sh
ln -s "$PWD" ~/.vscode/extensions/hyprsh.clear-theme-0.1.0
```

## License

[MIT](LICENSE)
