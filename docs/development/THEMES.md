# Skins

VPN Doctor can be reskinned with a plain GTK 4 CSS file. No code, no restart:
pick a skin in ☰ > Preferences, edit your file, then press **Reload**.

## Where skins live

| Location | Purpose |
| --- | --- |
| `src/vpn_doctor/ui/themes/` | built-in skins (`default`, `wasteland`) |
| `~/.config/vpn-doctor/themes/` | your skins; a file with the same name overrides a built-in |

The selected skin is saved in `~/.config/vpn-doctor/settings.json`.

## Metadata

The first comment of the file may describe the skin:

```css
/*
 * @name: Neon Night
 * @color-scheme: dark
 * @title: VPN DOCTOR ✦ NEON
 * @tagline: Diagnose. Connect. Protect.
 * @logo: neon-logo.svg
 */
```

| Key | Values | Effect |
| --- | --- | --- |
| `@name` | text | name shown in the menu |
| `@color-scheme` | `default`, `light`, `dark` | forces the libadwaita color scheme |
| `@title` | text | replaces the window heading |
| `@tagline` | text | replaces the line under the heading |
| `@logo` | file name | logo of the heading and startup animation, next to the skin file (or a built-in asset); paths leaving that folder are ignored |

## CSS classes

| Selector | Widget |
| --- | --- |
| `window.vd-window` | main window |
| `.vd-header-logo` | logo next to the heading |
| `.vd-boot`, `.vd-boot-log`, `.vd-boot-hint` | startup animation |
| `.vd-title`, `.vd-tagline` | heading and tagline |
| `.vd-card` | the three panels (also `.vd-status-card`, `.vd-connection-card`, `.vd-log-card`) |
| `.vd-section-title` | panel titles (`■ STATUS`, ...) |
| `.vd-state` | big status text |
| `.vd-pill` | status pill (`● ONLINE`, `○ OFFLINE`, ...) |
| `.vd-timer` | connection timer |
| `.vd-subtitle` | status explanation or suggestion |
| `.vd-meta-key`, `.vd-meta-value` | connection details |
| `.vd-connection-name` | connection name in its tab |
| `tabbar`, `tabbar tab`, `tabbar tab:selected` | connection tabs |
| `.vd-open-button` | `+` button opening a connection tab |
| `.vd-conflict-banner` | banner shown when VPNs conflict |
| `button.vd-primary`, `button.vd-danger`, `button.vd-secondary` | Connect, Disconnect, Diagnose |
| `.vd-menu-button` | main menu button (☰) |
| `.vd-log`, `.vd-log text` | log console |

The status panel, the status text and the pill also carry one state class:
`.vd-success` (connected), `.vd-warning` (connecting, waiting for input),
`.vd-error` (failed) or `.vd-neutral` (disconnected).

To recolor libadwaita widgets (dialogs, popovers, entries), override its
palette with both `@define-color window_bg_color ...;` (libadwaita < 1.6) and
`:root { --window-bg-color: ...; }` (libadwaita >= 1.6). See
`wasteland.css` for a complete example.

## Limits

GTK CSS has no `text-transform` and no `content`: write uppercase text in
`@title` and `@tagline` when a skin needs it. Parsing errors are reported in
the log console with their line number.

## Trademarks

Built-in skins must not use third-party trademarks or artwork. The Wasteland
Terminal skin is inspired by retro terminals, without game names or logos.
