# UI Guidelines

## Design direction

VPN Doctor should feel like a modern GNOME application.

Use:

- GTK4
- Libadwaita
- GNOME Human Interface Guidelines

## Main window concept

Main areas:

- Sidebar with profiles
- Connection status card
- Connect / disconnect action
- Diagnostics summary
- Live logs
- Timer
- Optional traffic statistics later

## Status language

Use clear labels:

- Disconnected
- Connecting
- Authenticating
- Connected
- Disconnecting
- Error

## Status colors

Use semantic colors sparingly:

- Green: healthy / connected
- Orange: warning
- Red: error
- Blue: action / neutral trust

## Avoid jargon

Bad:

```text
ppp0 route metric mismatch
```

Better:

```text
The VPN route is active, but replies are not coming back through the tunnel.
```

Advanced details can be available in an expandable technical section.

## Notifications

Use notifications for:

- Connected
- Disconnected
- Connection failed
- Certificate changed
- Diagnostic completed

## Accessibility

- Keyboard navigation must work.
- Icons must not be the only indicator.
- Logs must be copyable.
- Colors must not be the only indicator.

## Dialogs

Avoid blocking dialogs unless needed.

Prefer:

- Toasts
- Inline messages
- Details expanders
