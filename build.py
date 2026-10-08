"""Generate the VS Code, Ghostty, herdr, tuicr, Neovim and Claude Code themes
from the palettes in palettes.py.

Run: python3 build.py
"""
import colorsys
import json
import plistlib
from pathlib import Path

from palettes import (
    CLEAR_DARK, CLEAR_DARK_GRAYS, CLEAR_LIGHT, CLEAR_LIGHT_GRAYS,
    DARK, DARK_GRAYS, LIGHT, LIGHT_GRAYS, mix,
)

ANSI_NAMES = [
    "Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White",
    "BrightBlack", "BrightRed", "BrightGreen", "BrightYellow",
    "BrightBlue", "BrightMagenta", "BrightCyan", "BrightWhite",
]


def alpha(color, a):
    return f"{color}{a:02x}"


def luminance(color):
    c = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable(color, bg, target=4.5, saturate=1.0):
    """Darken (on light bg) or lighten (on dark bg) color until it reaches
    the WCAG contrast target against bg. Hue and saturation are kept (and
    saturation optionally boosted) so the color doesn't turn muddy."""
    h, l, s = colorsys.rgb_to_hls(*(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)))
    s = min(1, s * saturate)
    step = -0.005 if luminance(bg) > 0.5 else 0.005

    def hex_(l):
        return "#" + "".join(f"{round(x * 255):02x}" for x in colorsys.hls_to_rgb(h, l, s))

    while contrast(hex_(l), bg) < target and 0 < l < 1:
        l = min(1, max(0, l + step))
    return hex_(l)


def over(color, under):
    """The opaque color that translucent color (#rrggbbaa) shows over under."""
    a = int(color[7:9], 16) / 255
    return "#" + "".join(
        f"{round(int(color[i:i + 2], 16) * a + int(under[i:i + 2], 16) * (1 - a)):02x}"
        for i in (1, 3, 5))


def vivid(color):
    """color's hue at full saturation, so even a faint tint of it shows."""
    h, _, _ = colorsys.rgb_to_hls(*(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)))
    return "#" + "".join(f"{round(x * 255):02x}" for x in colorsys.hls_to_rgb(h, 0.5, 1))


def tint(color, under, texts, most, layers=1):
    """color, translucent, at the strongest alpha up to most that keeps every
    text color readable (4.5:1) on it, even stacked layers times over under."""
    for a in range(most, 0, -1):
        shown = under
        for _ in range(layers):
            shown = over(alpha(color, a), shown)
        if all(contrast(t, shown) >= 4.5 for t in texts):
            return alpha(color, a)
    return alpha(color, 0)


def diff_fills(hue, bg, code):
    """The changed-line and changed-text fills for hue. Each is as strong as
    it can be, up to its designed alpha, while every code color on it stays
    readable; it uses the hue at full saturation so it still shows. Changed
    text is tinted on top of its changed line (and added or removed lines get
    both), so the line leaves room for it."""
    line = tint(vivid(hue), bg, code, 0x18, layers=2)
    return line, tint(vivid(hue), over(line, bg), code, 0x30)


def terminal_ansi(p):
    """The ANSI colors as the terminal gets them. For palettes marked
    readable_terminal, every color under 4.5:1 on the background is adjusted
    just enough to be readable, keeping its hue. Black and white are left
    alone, as programs use them for backgrounds; bright black is included, as
    it's the usual gray for dimmed text. In a light palette the six normal
    colors take the editor's hues, and the rest get the same saturation
    boost."""
    a = list(p["ansi"])
    if not p.get("readable_terminal"):
        return a
    bg = p["background"]
    dark = luminance(bg) < 0.5
    editor = [] if dark else hues(p, dark)
    for i in range(16):
        if i in (0, 7, 15) or contrast(a[i], bg) >= 4.5:
            continue
        if not dark and 1 <= i <= 6:
            a[i] = editor[i - 1]
        else:
            a[i] = readable(a[i], bg, saturate=1.0 if dark else 1.2)
    return a


def selection_gray(p, dark):
    """Selected list rows and selected code get a neutral gray, so colored
    text (git status, syntax) keeps its contrast on them."""
    return mix(p["background"], p["foreground"], 0.12 if dark else 0.08)


def hues(p, dark):
    """Red, green, yellow, blue, magenta and cyan for colored text. Dark mode
    uses the bright (Apple dark-appearance) hues, light mode the normal ones,
    which read better on white. Each is adjusted just enough to stay
    readable, even on a selected row. This mostly darkens the light palette,
    which is too pale on white; it gets a saturation boost so the darker
    colors stay vivid."""
    a = p["ansi"]
    selected = selection_gray(p, dark)
    if dark:
        return [readable(c, selected) for c in a[9:15]]
    return [readable(c, selected, saturate=1.2) for c in a[1:7]]


def accent_color(p, dark):
    """Filled accent (buttons, badges, menu selection). White on the bright
    dark-mode blue is too faint, so dark mode puts dark text on it; light
    mode darkens the blue under white text instead."""
    return p["ansi"][12] if dark else readable(p["ansi"][12], "#ffffff")


def build(name, p, grays, dark):
    a = p["ansi"]
    bg, fg = p["background"], p["foreground"]
    gray, gray2, gray3, gray4, gray5, gray6 = grays

    selection = selection_gray(p, dark)
    red, green, yellow, blue, magenta, cyan = hues(p, dark)
    comment = readable(p.get("comment", a[7]), selection)
    # Cyan is too faint on white for something as common as types; in light
    # mode types take blue and functions, which are rarer, take cyan.
    type_color, func_color = (cyan, blue) if dark else (blue, cyan)
    muted = gray if dark else a[8]

    accent = accent_color(p, dark)
    on_accent = bg if dark else "#ffffff"
    accent_hover = a[4] if dark else mix(accent, "#000000", 0.15)

    border = gray4
    chrome = bg
    hover = alpha(fg, 0x10)

    # Code shows through the diff, find and bracket-match fills, so each is
    # only as strong as keeps every code color readable on it.
    code = [fg, comment, red, green, yellow, blue, magenta, cyan]
    inserted_line, inserted_text = diff_fills(green, bg, code)
    removed_line, removed_text = diff_fills(red, bg, code)

    colors = {
        "foreground": fg,
        "focusBorder": blue,
        "selection.background": p["selection_bg"],
        "descriptionForeground": muted,
        "errorForeground": red,
        "icon.foreground": muted,
        "widget.border": border,
        "widget.shadow": "#00000040" if dark else "#00000020",
        "textLink.foreground": blue,
        "textLink.activeForeground": blue,
        "textPreformat.foreground": cyan,
        "textBlockQuote.background": gray6 if not dark else gray5,
        "textCodeBlock.background": gray6 if not dark else gray5,
        "scrollbarSlider.background": "#00000000",
        "scrollbarSlider.hoverBackground": alpha(gray, 0x70),
        "scrollbarSlider.activeBackground": alpha(gray, 0x90),

        # Window chrome
        "titleBar.activeBackground": chrome,
        "titleBar.activeForeground": fg,
        "titleBar.inactiveBackground": chrome,
        "titleBar.inactiveForeground": muted,
        "titleBar.border": border,
        "activityBar.background": chrome,
        "activityBar.foreground": fg,
        "activityBar.inactiveForeground": muted,
        "activityBar.border": border,
        "activityBar.activeBorder": blue,
        "activityBarBadge.background": accent,
        "activityBarBadge.foreground": on_accent,
        "sideBar.background": chrome,
        "sideBar.foreground": fg,
        "sideBar.border": border,
        "sideBarTitle.foreground": muted,
        "sideBarSectionHeader.background": chrome,
        "sideBarSectionHeader.foreground": fg,
        "sideBarSectionHeader.border": border,
        "statusBar.background": chrome,
        "statusBar.foreground": muted,
        "statusBar.border": border,
        "statusBar.noFolderBackground": chrome,
        "statusBar.debuggingBackground": alpha(yellow, 0x40),
        "statusBar.debuggingForeground": fg,
        "statusBarItem.hoverBackground": hover,
        "statusBarItem.remoteBackground": accent,
        "statusBarItem.remoteForeground": on_accent,
        "panel.background": bg,
        "panel.border": border,
        "panelTitle.activeForeground": fg,
        "panelTitle.inactiveForeground": muted,
        "panelTitle.activeBorder": blue,

        # Tabs
        "editorGroupHeader.tabsBackground": chrome,
        "editorGroupHeader.tabsBorder": border,
        "editorGroup.border": border,
        "tab.activeBackground": bg,
        "tab.activeForeground": fg,
        "tab.activeBorderTop": blue,
        "tab.inactiveBackground": chrome,
        "tab.inactiveForeground": muted,
        "tab.border": border,
        "tab.hoverBackground": hover,
        "breadcrumb.foreground": muted,
        "breadcrumb.focusForeground": fg,

        # Lists
        "list.activeSelectionBackground": selection,
        "list.activeSelectionForeground": fg,
        "list.inactiveSelectionBackground": alpha(selection, 0x80),
        "list.hoverBackground": hover,
        "list.focusOutline": blue,
        "list.highlightForeground": blue,
        "list.errorForeground": red,
        "list.warningForeground": yellow,
        "tree.indentGuidesStroke": gray3,

        # Inputs, buttons, dropdowns
        "input.background": gray5 if dark else "#ffffff",
        "input.foreground": fg,
        "input.border": border,
        "input.placeholderForeground": muted,
        "inputOption.activeBorder": blue,
        "inputOption.activeBackground": alpha(blue, 0x30),
        "dropdown.background": gray5 if dark else "#ffffff",
        "dropdown.border": border,
        "button.background": accent,
        "button.foreground": on_accent,
        "button.hoverBackground": accent_hover,
        "button.secondaryBackground": gray4 if dark else gray5,
        "button.secondaryForeground": fg,
        "badge.background": accent,
        "badge.foreground": on_accent,
        "progressBar.background": blue,
        "checkbox.background": gray5 if dark else "#ffffff",
        "checkbox.border": border,

        # Widgets
        "editorWidget.background": gray6 if dark else "#ffffff",
        "editorWidget.border": border,
        "editorHoverWidget.background": gray6 if dark else "#ffffff",
        "editorHoverWidget.border": border,
        "editorSuggestWidget.background": gray6 if dark else "#ffffff",
        "editorSuggestWidget.border": border,
        "editorSuggestWidget.selectedBackground": selection,
        "editorSuggestWidget.highlightForeground": blue,
        "quickInput.background": gray6 if dark else "#ffffff",
        "pickerGroup.foreground": blue,
        "pickerGroup.border": border,
        "menu.background": gray6 if dark else "#ffffff",
        "menu.selectionBackground": accent,
        "menu.selectionForeground": on_accent,
        "notifications.background": gray6 if dark else "#ffffff",
        "notifications.border": border,

        # Editor
        "editor.background": bg,
        "editor.foreground": fg,
        "editorCursor.foreground": p["cursor"],
        "editorCursor.background": p["cursor_text"],
        "editor.selectionBackground": selection,
        "editor.inactiveSelectionBackground": alpha(selection, 0x80),
        "editor.selectionHighlightBackground": alpha(selection, 0x80),
        "editor.wordHighlightBackground": alpha(selection, 0x60),
        "editor.wordHighlightStrongBackground": alpha(selection, 0x90),
        # Faint fill plus outline: the match stands out, the code stays readable.
        "editor.findMatchBackground": tint(vivid(yellow), bg, code, 0x28),
        "editor.findMatchBorder": yellow,
        "editor.findMatchHighlightBackground": tint(vivid(yellow), bg, code, 0x18),
        "editor.findMatchHighlightBorder": alpha(yellow, 0x80),
        "editor.lineHighlightBackground": alpha(fg, 0x0a),
        "editor.lineHighlightBorder": "#00000000",
        "editorLineNumber.foreground": gray2,
        "editorLineNumber.activeForeground": fg,
        "editorIndentGuide.background1": gray4 if dark else gray5,
        "editorIndentGuide.activeBackground1": gray2 if dark else gray3,
        "editorWhitespace.foreground": gray3 if dark else gray4,
        "editorRuler.foreground": gray4 if dark else gray5,
        "editorBracketMatch.background": tint(vivid(blue), bg, code, 0x30),
        "editorBracketMatch.border": "#00000000",
        "editorBracketHighlight.foreground1": blue,
        "editorBracketHighlight.foreground2": magenta,
        "editorBracketHighlight.foreground3": cyan,
        "editorBracketHighlight.foreground4": green,
        "editorBracketHighlight.foreground5": yellow,
        "editorBracketHighlight.foreground6": red,
        "editorError.foreground": red,
        "editorWarning.foreground": yellow,
        "editorInfo.foreground": blue,
        "editorHint.foreground": green,
        "editorLink.activeForeground": blue,
        "editorGutter.addedBackground": green,
        "editorGutter.modifiedBackground": blue,
        "editorGutter.deletedBackground": red,
        "editorOverviewRuler.border": "#00000000",
        "editorOverviewRuler.errorForeground": red,
        "editorOverviewRuler.warningForeground": yellow,
        "editorOverviewRuler.findMatchForeground": yellow,

        # Diff
        "diffEditor.insertedTextBackground": inserted_text,
        "diffEditor.removedTextBackground": removed_text,
        "diffEditor.insertedLineBackground": inserted_line,
        "diffEditor.removedLineBackground": removed_line,

        # Git
        "gitDecoration.addedResourceForeground": green,
        "gitDecoration.untrackedResourceForeground": green,
        "gitDecoration.modifiedResourceForeground": blue,
        "gitDecoration.deletedResourceForeground": red,
        "gitDecoration.conflictingResourceForeground": magenta,
        "gitDecoration.ignoredResourceForeground": muted,

        # Terminal: the same colors as the Ghostty theme
        "terminal.background": bg,
        "terminal.foreground": fg,
        "terminalCursor.foreground": p["cursor"],
        "terminalCursor.background": p["cursor_text"],
        "terminal.selectionBackground": p["selection_bg"],
        "terminal.selectionForeground": p["selection_fg"],
    }
    for n, c in zip(ANSI_NAMES, terminal_ansi(p)):
        colors[f"terminal.ansi{n}"] = c

    def rule(scope, color=None, style=None):
        s = {}
        if color:
            s["foreground"] = color
        if style is not None:
            s["fontStyle"] = style
        return {"scope": scope, "settings": s}

    token_colors = [
        rule(["comment", "punctuation.definition.comment"], comment),
        rule(["keyword", "storage.type", "storage.modifier", "keyword.control"], magenta),
        rule(["keyword.operator"], fg),
        rule(["string", "punctuation.definition.string"], fg),
        rule(["constant.character.escape", "string.regexp"], cyan),
        rule(["constant.numeric", "constant.language", "constant.language.boolean"], red),
        rule(["constant.other", "variable.other.constant", "support.constant"], yellow),
        rule(["entity.name.function", "support.function", "meta.function-call"], func_color),
        rule(["entity.name.type", "entity.name.class", "support.type", "support.class",
              "entity.other.inherited-class"], type_color),
        rule(["variable", "variable.parameter"], fg),
        rule(["variable.language"], magenta),
        rule(["variable.other.property", "variable.other.object.property", "support.variable.property",
              "meta.object-literal.key", "support.type.property-name"], green),
        rule(["entity.name.tag"], blue),
        rule(["entity.other.attribute-name"], green),
        rule(["entity.name.section", "markup.heading"], blue, "bold"),
        rule(["markup.bold"], None, "bold"),
        rule(["markup.italic"], None, "italic"),
        rule(["markup.underline.link", "string.other.link"], cyan),
        rule(["markup.inline.raw", "markup.fenced_code"], cyan),
        rule(["markup.inserted"], green),
        rule(["markup.deleted"], red),
        rule(["markup.changed"], blue),
        rule(["invalid"], red),
    ]

    semantic = {
        "keyword": magenta,
        "string": fg,
        "number": red,
        "function": func_color,
        "method": func_color,
        "type": type_color,
        "class": type_color,
        "interface": type_color,
        "enum": type_color,
        "enumMember": yellow,
        "property": green,
        "parameter": fg,
        "variable": fg,
        "variable.readonly": yellow,
        "*.defaultLibrary": type_color,
        "comment": comment,
    }

    colors = {k: v for k, v in colors.items() if v is not None}

    return {
        "$schema": "vscode://schemas/color-theme",
        "name": name,
        "type": "dark" if dark else "light",
        "semanticHighlighting": True,
        "colors": colors,
        "tokenColors": token_colors,
        "semanticTokenColors": semantic,
    }


def ghostty(p):
    lines = [f"palette = {i}={c}" for i, c in enumerate(terminal_ansi(p))]
    lines += [
        f"background = {p['background']}",
        f"foreground = {p['foreground']}",
        f"cursor-color = {p['cursor']}",
        f"cursor-text = {p['cursor_text']}",
        f"selection-background = {p['selection_bg']}",
    ]
    if p["selection_fg"]:
        lines.append(f"selection-foreground = {p['selection_fg']}")
    return "\n".join(lines) + "\n"


def herdr(p, grays, dark):
    """herdr's colors for one appearance: every token of its palette, with
    the VS Code theme's grays, accent and hues."""
    fg = p["foreground"]
    gray, gray2, gray3, gray4, gray5, gray6 = grays
    red, green, yellow, blue, magenta, cyan = hues(p, dark)
    # The current row takes the terminal's selection color; the neutral
    # selection gray is too faint to mark it on a translucent window.
    row = p["selection_bg"]
    # Secondary text: the VS Code theme's muted gray, lightened where it
    # isn't readable on the current row.
    muted = gray if dark else p["ansi"][8]
    if contrast(muted, row) < 4.5:
        muted = readable(muted, row)
    # The active tab's label is surface_dim on the accent (panel_bg is reset),
    # so the accent is adjusted until that label is readable.
    accent = readable(accent_color(p, dark), gray4)
    return {
        "text": fg,
        "subtext0": muted,
        "overlay0": muted,
        "overlay1": muted,
        "mauve": muted,
        "sidebar_bg": "reset",
        "panel_bg": "reset",
        "active_row_bg": row,
        "selection_bg": row,
        "surface0": gray5,
        "surface1": gray3,
        "surface_dim": gray4,
        "accent": accent,
        "blue": blue,
        "green": green,
        "yellow": yellow,
        "red": red,
        "teal": cyan,
        "peach": yellow,
    }


# What herdr uses each token for, noted once, on the light block.
HERDR_NOTES = {
    "subtext0": "secondary text: headers, hints, branch names",
    "sidebar_bg": "keep the window's translucent background",
    "panel_bg": "tab bar, status line, popups: translucent too",
    "active_row_bg": "current space/agent: the terminal's selection",
    "selection_bg": "cursor row while navigating",
    "surface1": "dragged row, search matches, popup dividers",
    "surface_dim": "divider lines; text on accent, as panel_bg is reset",
    "accent": "active tab, key hints",
    "green": "idle",
    "yellow": "working",
    "red": "blocked",
    "teal": "done",
    "peach": "interrupted",
}


def herdr_toml(light, dark):
    lines = [
        "# Clear Light and Clear Dark for herdr (https://herdr.dev), generated by",
        "# clear-theme's build.py. herdr switches between them with the terminal's",
        "# appearance. Every color is set, so nothing falls back to the \"terminal\"",
        "# base theme, which assumes a dark background.",
        "[theme]",
        'name = "terminal"',
        "auto_switch = true",
    ]
    for mode, colors in (("light", light), ("dark", dark)):
        lines += ["", f"[theme.custom.{mode}]"]
        for key, color in colors.items():
            line = f'{key} = "{color}"'
            note = HERDR_NOTES.get(key) if mode == "light" else None
            lines.append(f"{line:<25}  # {note}" if note else line)
    return "\n".join(lines) + "\n"


def slug(name):
    return name.lower().replace(" ", "-")


def tuicr(vs, p, grays, dark):
    """tuicr's colors for one theme, with the VS Code theme vs's grays,
    accent and hues."""
    c = vs["colors"]
    bg, fg = p["background"], p["foreground"]
    red, green, yellow, blue, magenta, cyan = hues(p, dark)
    comment = vs["semanticTokenColors"]["comment"]
    accent, on_accent = c["button.background"], c["button.foreground"]
    # The selected row takes the terminal's selection color, as in herdr,
    # with secondary text adjusted to stay readable on it. The cursor line
    # holds code, so it takes the editor's selection gray, which every code
    # color is readable on.
    row = p["selection_bg"]
    muted = c["descriptionForeground"]
    if contrast(muted, row) < 4.5:
        muted = readable(muted, row)
    # Changed lines: the editor's changed-line fill, as strong as it gets
    # with every code color readable on it. tuicr has no changed-text fill to
    # stack on top, and takes no alpha, so it's flattened onto the background.
    code = [fg, comment, red, green, yellow, blue, magenta, cyan]

    def fill(hue):
        return over(tint(vivid(hue), bg, code, 0x18), bg)

    added, removed = fill(green), fill(red)

    def on(color):
        return max((bg, fg), key=lambda t: contrast(t, color))

    return {
        "panel_bg": bg,  # only with transparent_background = false
        "bg_highlight": row,
        "fg_primary": fg,
        "fg_secondary": muted,
        "fg_dim": comment,
        "diff_add": green,
        "diff_add_bg": added,
        "diff_del": red,
        "diff_del_bg": removed,
        "diff_context": fg,
        "diff_hunk_header": blue,
        "expanded_context_fg": comment,
        "syntax_add_bg": added,
        "syntax_del_bg": removed,
        "syntax_theme": f"{slug(vs['name'])}.tmTheme",
        "file_added": green,
        "file_modified": blue,
        "file_deleted": red,
        "file_renamed": magenta,
        "reviewed": green,
        "pending": yellow,
        "comment_note": blue,
        "comment_suggestion": cyan,
        "comment_issue": red,
        "comment_praise": green,
        "border_focused": c["focusBorder"],
        "border_unfocused": c["widget.border"],
        "status_bar_bg": grays[4],
        "cursor_color": yellow,  # commit hashes
        "cursor_line_bg": selection_gray(p, dark),
        "branch_name": blue,
        "help_indicator": muted,
        "message_info_fg": on_accent,
        "message_info_bg": accent,
        "message_warning_fg": on(yellow),
        "message_warning_bg": yellow,
        "message_error_fg": on(red),
        "message_error_bg": red,
        "update_badge_fg": on(yellow),
        "update_badge_bg": yellow,
        "mode_fg": on_accent,
        "mode_bg": accent,
    }


def tuicr_toml(name, colors):
    lines = [
        f"# {name} for tuicr (https://tuicr.dev), generated by clear-theme's",
        "# build.py from the VS Code theme. Syntax colors are in the .tmTheme",
        "# file next to it.",
    ]
    for key, value in colors.items():
        lines.append(f'{key} = "{value}"')
    return "\n".join(lines) + "\n"


def tmtheme(vs):
    """The VS Code theme's syntax colors as a TextMate theme, for tuicr's
    highlighter (syntect)."""
    c = vs["colors"]
    rules = [{"settings": {"background": c["editor.background"],
                           "foreground": c["editor.foreground"]}}]
    rules += [{"scope": ", ".join(r["scope"]), "settings": r["settings"]}
              for r in vs["tokenColors"]]
    # syntect's (Sublime) grammars mark function calls as variable.function,
    # which the variable rule would otherwise make plain text.
    rules.append({"scope": "variable.function",
                  "settings": {"foreground": vs["semanticTokenColors"]["function"]}})
    return plistlib.dumps({"name": vs["name"], "settings": rules}).decode()


def nvim(vs, p, grays, dark):
    """Neovim's highlight groups for one theme, with the VS Code theme vs's
    colors. Neovim can't draw translucent colors, so the VS Code theme's
    translucent fills are flattened onto the background. Groups that are the
    same in both themes are links, in NVIM_LINKS."""
    c, sem = vs["colors"], vs["semanticTokenColors"]
    bg, fg = p["background"], p["foreground"]
    gray, gray2, gray3, gray4, gray5, gray6 = grays
    red, green, yellow, blue, magenta, cyan = hues(p, dark)
    comment, func, type_ = sem["comment"], sem["function"], sem["type"]
    muted = c["descriptionForeground"]
    accent, on_accent = c["button.background"], c["button.foreground"]
    selection = c["editor.selectionBackground"]
    line = over(c["editor.lineHighlightBackground"], bg)
    # Floats (completion, hover, pickers) often have no border, so they get
    # a faint fill, the VS Code theme's widget gray. Their current row takes
    # the terminal's selection color, as in herdr: the neutral selection gray
    # is too faint on a translucent window.
    float_bg = gray6
    row = p["selection_bg"]
    # Box-drawing borders are thin, so they're a step darker than VS Code's.
    border = gray3

    code = [fg, comment, red, green, yellow, blue, magenta, cyan]
    add_line, _ = diff_fills(green, bg, code)
    delete_line, _ = diff_fills(red, bg, code)
    change_line, change_text = diff_fills(blue, bg, code)
    change_line = over(change_line, bg)

    def on(color):
        return max((bg, fg), key=lambda t: contrast(t, color))

    def kinds(color, *names):
        return {f"BlinkCmpKind{n}": {"fg": color} for n in names}

    return {
        # Editor
        "Normal": {"fg": fg, "bg": bg},
        "NormalFloat": {"fg": fg, "bg": float_bg},
        "FloatBorder": {"fg": border, "bg": float_bg},
        "FloatTitle": {"fg": fg, "bg": float_bg, "bold": True},
        "FloatFooter": {"fg": muted, "bg": float_bg},
        "Cursor": {"fg": p["cursor_text"], "bg": p["cursor"]},
        "CursorLine": {"bg": line},
        "ColorColumn": {"bg": line},
        "Folded": {"fg": muted, "bg": line},
        "LineNr": {"fg": c["editorLineNumber.foreground"]},
        "CursorLineNr": {"fg": c["editorLineNumber.activeForeground"]},
        "SignColumn": {"fg": c["editorLineNumber.foreground"]},
        "FoldColumn": {"fg": c["editorLineNumber.foreground"]},
        # Plugins use NonText for dimmed text (paths, counts, hidden files),
        # so it's as readable as line numbers; only whitespace is fainter.
        "NonText": {"fg": c["editorLineNumber.foreground"]},
        "Whitespace": {"fg": c["editorWhitespace.foreground"]},
        "Conceal": {"fg": muted},
        "Directory": {"fg": blue},
        "Title": {"fg": blue, "bold": True},
        "Visual": {"bg": selection},
        "Search": {"bg": over(c["editor.findMatchBackground"], bg)},
        # The current match gets the solid color VS Code gives its outline.
        "CurSearch": {"fg": on(yellow), "bg": yellow},
        "Substitute": {"fg": on(red), "bg": red},
        "MatchParen": {"fg": blue, "bg": over(c["editorBracketMatch.background"], bg),
                       "bold": True},
        "Pmenu": {"fg": fg, "bg": float_bg},
        "PmenuSel": {"bg": row},
        "PmenuMatch": {"fg": blue, "bold": True},
        "PmenuMatchSel": {"fg": blue, "bold": True},
        "PmenuKind": {"fg": muted},
        "PmenuExtra": {"fg": muted},
        "PmenuSbar": {"bg": float_bg},
        "PmenuThumb": {"bg": border},
        "StatusLine": {"fg": muted, "bg": bg},
        "StatusLineNC": {"fg": gray2, "bg": bg},
        "WinBar": {"fg": fg, "bold": True},
        "WinBarNC": {"fg": muted},
        "TabLine": {"fg": muted, "bg": bg},
        "TabLineFill": {"bg": bg},
        "TabLineSel": {"fg": fg, "bg": bg, "bold": True},
        "WinSeparator": {"fg": border},
        "QuickFixLine": {"bg": row},
        "WildMenu": {"bg": row},
        "ModeMsg": {"fg": fg, "bold": True},
        "MoreMsg": {"fg": blue},
        "Question": {"fg": blue},
        "ErrorMsg": {"fg": red},
        "WarningMsg": {"fg": yellow},
        "SpellBad": {"sp": red, "undercurl": True},
        "SpellCap": {"sp": yellow, "undercurl": True},
        "SpellLocal": {"sp": blue, "undercurl": True},
        "SpellRare": {"sp": magenta, "undercurl": True},

        # Diff: added and removed lines take the VS Code line fills, changed
        # lines the same fill in blue, with their changed text on top.
        "DiffAdd": {"bg": over(add_line, bg)},
        "DiffDelete": {"fg": border, "bg": over(delete_line, bg)},
        "DiffChange": {"bg": change_line},
        "DiffText": {"bg": over(change_text, change_line)},
        "Added": {"fg": green},
        "Changed": {"fg": blue},
        "Removed": {"fg": red},

        # Syntax, as in the VS Code theme's token colors
        "Comment": {"fg": comment},
        "Constant": {"fg": yellow},
        "String": {"fg": fg},
        "Character": {"fg": fg},
        "Number": {"fg": red},
        "Boolean": {"fg": red},
        "Identifier": {"fg": fg},
        "Function": {"fg": func},
        "Statement": {"fg": magenta},
        "Operator": {"fg": fg},
        "PreProc": {"fg": magenta},
        "Type": {"fg": type_},
        "StorageClass": {"fg": magenta},
        "Special": {"fg": cyan},
        "Delimiter": {"fg": fg},
        "SpecialComment": {"fg": comment},
        "Tag": {"fg": blue},
        "Error": {"fg": red},
        "Todo": {"fg": yellow, "bold": True},

        # Treesitter
        "@variable": {"fg": fg},
        "@variable.builtin": {"fg": magenta},
        "@variable.member": {"fg": green},
        "@property": {"fg": green},
        "@constant.builtin": {"fg": red},
        "@constant.macro": {"fg": yellow},
        "@module": {"fg": fg},
        "@string.special.symbol": {"fg": yellow},
        "@string.special.url": {"fg": cyan, "underline": True},
        "@type.builtin": {"fg": type_},
        "@function.builtin": {"fg": func},
        "@constructor": {"fg": type_},
        # Lua's table braces, which its grammar calls constructors
        "@constructor.lua": {"fg": fg},
        "@keyword.operator": {"fg": fg},
        "@punctuation.special": {"fg": fg},
        "@tag.builtin": {"fg": blue},
        "@markup": {"fg": fg},
        "@markup.link": {"fg": cyan},
        "@markup.link.url": {"fg": cyan, "underline": True},
        "@markup.raw": {"fg": cyan},
        "@markup.math": {"fg": cyan},
        "@markup.list.checked": {"fg": green},
        "@markup.list.unchecked": {"fg": muted},

        # LSP semantic tokens, as in the VS Code theme's semantic colors
        "@lsp.type.variable": {},  # keep treesitter's builtins (self, this)
        "@lsp.typemod.variable.readonly": {"fg": yellow},
        "@lsp.mod.defaultLibrary": {"fg": type_},

        # Diagnostics and LSP
        "DiagnosticError": {"fg": red},
        "DiagnosticWarn": {"fg": yellow},
        "DiagnosticInfo": {"fg": blue},
        "DiagnosticHint": {"fg": green},
        "DiagnosticOk": {"fg": green},
        "DiagnosticUnderlineError": {"sp": red, "undercurl": True},
        "DiagnosticUnderlineWarn": {"sp": yellow, "undercurl": True},
        "DiagnosticUnderlineInfo": {"sp": blue, "undercurl": True},
        "DiagnosticUnderlineHint": {"sp": green, "undercurl": True},
        "DiagnosticUnderlineOk": {"sp": green, "undercurl": True},
        "LspReferenceText": {"bg": over(c["editor.wordHighlightBackground"], bg)},
        "LspReferenceRead": {"bg": over(c["editor.wordHighlightBackground"], bg)},
        "LspReferenceWrite": {"bg": over(c["editor.wordHighlightStrongBackground"], bg)},
        "LspInlayHint": {"fg": comment},
        "LspCodeLens": {"fg": comment},
        "LspSignatureActiveParameter": {"fg": blue, "bold": True},

        # Plugins in LazyVim's defaults. The rest take their colors from the
        # groups above.
        # Pickers, the file explorer among them, sit on the background like
        # VS Code's sidebar; floating ones have a border.
        "SnacksPicker": {"fg": fg, "bg": bg},
        "SnacksPickerBorder": {"fg": border, "bg": bg},
        "SnacksPickerTitle": {"fg": fg, "bg": bg, "bold": True},
        "SnacksPickerFooter": {"fg": muted, "bg": bg},
        "SnacksPickerListCursorLine": {"bg": row},
        "SnacksPickerMatch": {"fg": blue, "bold": True},
        "SnacksPickerDir": {"fg": muted},
        "SnacksPickerGitStatusUntracked": {"fg": c["gitDecoration.untrackedResourceForeground"]},
        "SnacksIndent": {"fg": c["editorIndentGuide.background1"]},
        "SnacksIndentScope": {"fg": c["editorIndentGuide.activeBackground1"]},
        "SnacksDashboardHeader": {"fg": blue},
        "SnacksDashboardIcon": {"fg": blue},
        "SnacksDashboardKey": {"fg": magenta},
        "SnacksDashboardDesc": {"fg": fg},
        "SnacksDashboardFile": {"fg": fg},
        "SnacksDashboardDir": {"fg": muted},
        "SnacksDashboardFooter": {"fg": muted},
        "SnacksDashboardSpecial": {"fg": magenta},
        "BlinkCmpLabelMatch": {"fg": blue, "bold": True},
        "BlinkCmpLabelDeprecated": {"fg": muted, "strikethrough": True},
        "BlinkCmpLabelDetail": {"fg": muted},
        "BlinkCmpLabelDescription": {"fg": muted},
        "BlinkCmpSource": {"fg": muted},
        "BlinkCmpGhostText": {"fg": comment},
        "BlinkCmpKind": {"fg": muted},
        **kinds(func, "Function", "Method", "Constructor"),
        **kinds(type_, "Class", "Interface", "Struct", "Enum", "TypeParameter"),
        **kinds(green, "Field", "Property"),
        **kinds(yellow, "Constant", "EnumMember"),
        **kinds(magenta, "Keyword"),
        "FlashLabel": {"fg": on_accent, "bg": accent, "bold": True},
        "BufferLineIndicatorSelected": {"fg": blue, "bg": bg},
        "MiniIconsAzure": {"fg": blue},
        "MiniIconsBlue": {"fg": blue},
        "MiniIconsCyan": {"fg": cyan},
        "MiniIconsGreen": {"fg": green},
        "MiniIconsGrey": {"fg": muted},
        "MiniIconsOrange": {"fg": yellow},
        "MiniIconsPurple": {"fg": magenta},
        "MiniIconsRed": {"fg": red},
        "MiniIconsYellow": {"fg": yellow},
    }


# Groups that are the same in both themes.
NVIM_LINKS = {
    "CursorColumn": "CursorLine",
    "SpecialKey": "NonText",
    "VisualNOS": "Visual",
    "IncSearch": "CurSearch",
    "@variable.parameter": "@variable",
    "@variable.parameter.builtin": "@variable.builtin",
    "@module.builtin": "@variable.builtin",
    "@attribute": "PreProc",
    "@attribute.builtin": "@attribute",
}


def lualine(vs, p, dark):
    """lualine's colors for one theme: the mode in the VS Code theme's
    accent (or a hue per mode) and the rest on the background, like VS
    Code's status bar."""
    c = vs["colors"]
    bg, fg = p["background"], p["foreground"]
    red, green, yellow, blue, magenta, cyan = hues(p, dark)
    muted = c["descriptionForeground"]

    def mode(color, text=None):
        text = text or max((bg, fg), key=lambda t: contrast(t, color))
        return {"a": {"fg": text, "bg": color, "gui": "bold"}}

    plain = {"fg": muted, "bg": bg}
    return {
        "normal": {
            **mode(c["button.background"], c["button.foreground"]),
            "b": {"fg": fg, "bg": c["button.secondaryBackground"]},
            "c": plain,
        },
        "insert": mode(green),
        "visual": mode(magenta),
        "replace": mode(red),
        "command": mode(yellow),
        "terminal": mode(cyan),
        "inactive": {"a": plain, "b": plain, "c": plain},
    }


def lua(value, indent=0):
    """value as a Lua literal. Tables of up to four plain values, such as a
    highlight group, stay on one line."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "{ " + ", ".join(lua(v) for v in value) + " }"
    if not value:
        return "{}"

    def key(k):
        return k if k.isidentifier() else f"[{json.dumps(k)}]"

    if len(value) <= 4 and not any(isinstance(v, (dict, list)) for v in value.values()):
        return "{ " + ", ".join(f"{key(k)} = {lua(v)}" for k, v in value.items()) + " }"
    pad = "  " * (indent + 1)
    lines = [f"{pad}{key(k)} = {lua(v, indent + 1)}," for k, v in value.items()]
    return "{\n" + "\n".join(lines) + "\n" + "  " * indent + "}"


def nvim_lua(light, dark):
    """The colorscheme file. light and dark are (groups, terminal colors)."""
    return f"""\
-- Clear Light and Clear Dark for Neovim, generated by clear-theme's build.py
-- from the VS Code theme. One colorscheme, "clear", that takes the theme for
-- 'background'. Neovim sets 'background' from the terminal's background
-- color and reloads the colorscheme when it changes, so it follows the
-- terminal's light/dark appearance.
local themes = {{
  light = {lua(light[0], 1)},
  dark = {lua(dark[0], 1)},
}}

local links = {lua(NVIM_LINKS)}

-- The terminal colors, as in the Ghostty theme, for :terminal and lazygit.
local terminal = {{
  light = {lua(light[1])},
  dark = {lua(dark[1])},
}}

vim.cmd("highlight clear")
if vim.fn.exists("syntax_on") == 1 then
  vim.cmd("syntax reset")
end
vim.g.colors_name = "clear"

local mode = vim.o.background == "light" and "light" or "dark"
for name, spec in pairs(themes[mode]) do
  vim.api.nvim_set_hl(0, name, spec)
end
for name, target in pairs(links) do
  vim.api.nvim_set_hl(0, name, {{ link = target }})
end
for i, color in ipairs(terminal[mode]) do
  vim.g["terminal_color_" .. (i - 1)] = color
end
"""


def lualine_lua(light, dark):
    return f"""\
-- Clear Light and Clear Dark for lualine, generated by clear-theme's build.py.
-- lualine picks this up for the "clear" colorscheme with its "auto" theme,
-- and reloads it when 'background' changes.
local themes = {{
  light = {lua(light, 1)},
  dark = {lua(dark, 1)},
}}

return themes[vim.o.background == "light" and "light" or "dark"]
"""


def claude_code(vs, p, grays, dark):
    """A Claude Code custom theme (~/.claude/themes/<slug>.json) with the VS
    Code theme vs's grays and hues. It starts from the built-in dark or light
    preset and overrides every color token, so nothing of the preset shows.
    Claude Code draws on the terminal's background and takes no alpha, so
    fills are flattened onto it."""
    c = vs["colors"]
    bg, fg = p["background"], p["foreground"]
    gray, gray2, gray3, gray4, gray5, gray6 = grays
    red, green, yellow, blue, magenta, cyan = hues(p, dark)
    muted = c["descriptionForeground"]
    # Claude's orange is close to the palette's red (bright red in dark
    # mode); orange and pink, which Claude Code has and the palette hasn't,
    # sit half-way between its neighbors.
    orange = readable(mix(red, yellow, 0.5), bg)
    pink = readable(mix(red, magenta, 0.5), bg)

    def shimmer(color):
        """The lighter color a spinner's gradient sweeps to, as in the
        presets."""
        return mix(color, "#ffffff", 0.3)

    # Changed lines and changed words: the editor's fills, flattened.
    # Dimmed diffs (a rejected edit) fade them toward the selection gray.
    code = [fg, vs["semanticTokenColors"]["comment"], red, green, yellow, blue, magenta, cyan]
    selected = selection_gray(p, dark)

    def diff(hue):
        line, text = diff_fills(hue, bg, code)
        line = over(line, bg)
        return line, over(text, line), mix(line, selected, 0.5)

    added, added_word, added_dimmed = diff(green)
    removed, removed_word, removed_dimmed = diff(red)

    colors = {
        # Text and accents
        "claude": red,
        "text": fg,
        "inverseText": bg,
        "inactive": muted,
        "subtle": gray2,
        "suggestion": blue,
        "permission": blue,
        "remember": blue,
        "skill": magenta,
        "background": cyan,
        "professionalBlue": blue,
        "chromeYellow": yellow,
        "clawd_body": red,
        "claudeBlue_FOR_SYSTEM_SPINNER": blue,
        # Status
        "success": green,
        "error": red,
        "warning": yellow,
        "merged": magenta,
        # Input box and modes
        "promptBorder": gray2,
        "planMode": cyan,
        "autoAccept": magenta,
        "bashBorder": magenta,
        "ide": blue,
        "fastMode": orange,
        "effortUltra": magenta,
        # Diffs
        "diffAdded": added,
        "diffRemoved": removed,
        "diffAddedDimmed": added_dimmed,
        "diffRemovedDimmed": removed_dimmed,
        "diffAddedWord": added_word,
        "diffRemovedWord": removed_word,
        # Message backgrounds, faintly tinted like the presets'
        "userMessageBackground": gray5,
        "userMessageBackgroundHover": gray4,
        "composerSidebarBackground": gray6,
        "bashMessageBackgroundColor": mix(gray5, magenta, 0.06),
        "memoryBackgroundColor": mix(gray5, blue, 0.06),
        "selectionBg": p["selection_bg"],
        # Usage meter and speaker labels
        "rate_limit_fill": blue,
        "rate_limit_empty": gray4,
        "briefLabelYou": blue,
        "briefLabelClaude": red,
        # Subagents
        "red_FOR_SUBAGENTS_ONLY": red,
        "blue_FOR_SUBAGENTS_ONLY": blue,
        "green_FOR_SUBAGENTS_ONLY": green,
        "yellow_FOR_SUBAGENTS_ONLY": yellow,
        "purple_FOR_SUBAGENTS_ONLY": magenta,
        "orange_FOR_SUBAGENTS_ONLY": orange,
        "pink_FOR_SUBAGENTS_ONLY": pink,
        "cyan_FOR_SUBAGENTS_ONLY": cyan,
        # The ultrathink rainbow
        "rainbow_red": red,
        "rainbow_orange": orange,
        "rainbow_yellow": yellow,
        "rainbow_green": green,
        "rainbow_blue": cyan,
        "rainbow_indigo": blue,
        "rainbow_violet": magenta,
    }
    for token in ("claude", "permission", "promptBorder", "inactive", "warning", "fastMode"):
        colors[f"{token}Shimmer"] = shimmer(colors[token])
    colors["claudeBlueShimmer_FOR_SYSTEM_SPINNER"] = shimmer(blue)
    colors["autoAcceptShimmer"] = shimmer(magenta)
    for hue in ("red", "orange", "yellow", "green", "blue", "indigo", "violet"):
        colors[f"rainbow_{hue}_shimmer"] = shimmer(colors[f"rainbow_{hue}"])
    return {"name": vs["name"], "base": "dark" if dark else "light", "overrides": colors}


def main():
    out = Path(__file__).parent / "themes"
    out.mkdir(exist_ok=True)
    vscode = {}
    for name, pal, grays, dark, fname in [
        ("Apple System Colors", DARK, DARK_GRAYS, True, "apple-system-colors-dark.json"),
        ("Apple System Colors Light", LIGHT, LIGHT_GRAYS, False, "apple-system-colors-light.json"),
        ("Clear Dark", CLEAR_DARK, CLEAR_DARK_GRAYS, True, "clear-dark.json"),
        ("Clear Light", CLEAR_LIGHT, CLEAR_LIGHT_GRAYS, False, "clear-light.json"),
    ]:
        vscode[name] = build(name, pal, grays, dark)
        (out / fname).write_text(json.dumps(vscode[name], indent=2) + "\n")
        print(f"wrote themes/{fname}")

    # Ghostty already ships Apple System Colors; only the Clear themes are generated.
    gh = Path(__file__).parent / "ghostty"
    gh.mkdir(exist_ok=True)
    for name, pal in [("Clear Dark", CLEAR_DARK), ("Clear Light", CLEAR_LIGHT)]:
        (gh / name).write_text(ghostty(pal))
        print(f"wrote ghostty/{name}")

    hd = Path(__file__).parent / "herdr"
    hd.mkdir(exist_ok=True)
    (hd / "clear.toml").write_text(herdr_toml(
        herdr(CLEAR_LIGHT, CLEAR_LIGHT_GRAYS, False),
        herdr(CLEAR_DARK, CLEAR_DARK_GRAYS, True),
    ))
    print("wrote herdr/clear.toml")

    tc = Path(__file__).parent / "tuicr"
    tc.mkdir(exist_ok=True)
    for name, pal, grays, dark in [
        ("Clear Dark", CLEAR_DARK, CLEAR_DARK_GRAYS, True),
        ("Clear Light", CLEAR_LIGHT, CLEAR_LIGHT_GRAYS, False),
    ]:
        vs = vscode[name]
        colors = tuicr(vs, pal, grays, dark)
        (tc / f"{slug(name)}.toml").write_text(tuicr_toml(name, colors))
        (tc / colors["syntax_theme"]).write_text(tmtheme(vs))
        print(f"wrote tuicr/{slug(name)}.toml, tuicr/{colors['syntax_theme']}")

    # Neovim looks for colors/ and lua/ at the repo root, so the repo installs
    # as a plugin.
    root = Path(__file__).parent
    (root / "colors").mkdir(exist_ok=True)
    (root / "colors" / "clear.lua").write_text(nvim_lua(
        (nvim(vscode["Clear Light"], CLEAR_LIGHT, CLEAR_LIGHT_GRAYS, False), terminal_ansi(CLEAR_LIGHT)),
        (nvim(vscode["Clear Dark"], CLEAR_DARK, CLEAR_DARK_GRAYS, True), terminal_ansi(CLEAR_DARK)),
    ))
    print("wrote colors/clear.lua")
    themes = root / "lua" / "lualine" / "themes"
    themes.mkdir(parents=True, exist_ok=True)
    (themes / "clear.lua").write_text(lualine_lua(
        lualine(vscode["Clear Light"], CLEAR_LIGHT, False),
        lualine(vscode["Clear Dark"], CLEAR_DARK, True),
    ))
    print("wrote lua/lualine/themes/clear.lua")

    cc = Path(__file__).parent / "claude-code"
    cc.mkdir(exist_ok=True)
    for name, pal, grays, dark, fname in [
        ("Apple System Colors", DARK, DARK_GRAYS, True, "apple-system-colors-dark.json"),
        ("Apple System Colors Light", LIGHT, LIGHT_GRAYS, False, "apple-system-colors-light.json"),
        ("Clear Dark", CLEAR_DARK, CLEAR_DARK_GRAYS, True, "clear-dark.json"),
        ("Clear Light", CLEAR_LIGHT, CLEAR_LIGHT_GRAYS, False, "clear-light.json"),
    ]:
        theme = claude_code(vscode[name], pal, grays, dark)
        (cc / fname).write_text(json.dumps(theme, indent=2) + "\n")
        print(f"wrote claude-code/{fname}")


if __name__ == "__main__":
    main()
