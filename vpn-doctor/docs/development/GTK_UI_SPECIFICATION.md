# GTK UI Specification

## Goal

Provide a modern GNOME-friendly UI.

## First window

The first GTK UI should show:

- profile selector;
- status;
- connect/disconnect button;
- elapsed connection timer;
- progress/status area;
- live log viewer;
- diagnostic summary.

## Suggested layout

```text
HeaderBar: VPN Doctor

Profile: [ Demo Fortinet v ]

Status: Disconnected

[ Connect ] [ Diagnose ]

Logs:
...
```

## Design principles

- avoid scary technical output by default;
- keep advanced details expandable;
- provide clear suggestions;
- support light and dark themes.
