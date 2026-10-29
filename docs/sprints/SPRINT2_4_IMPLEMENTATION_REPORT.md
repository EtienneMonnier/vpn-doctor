# Sprint 2.4 Implementation Report

## Summary

Sprint 2.4 introduces the first GTK4/libadwaita UI skeleton for VPN Doctor.

The UI is intentionally safe and conservative. It displays the current backend
status, offers Connect/Disconnect buttons, and provides a log area, but the
buttons are not yet wired to start real VPN processes from the GUI.

## Added

- `vpn-doctor gui`
- `vpn-doctor-gui` console script
- GTK4/libadwaita main window skeleton
- UI view model layer independent from GTK
- Initial UI tests without requiring GTK
- README, ROADMAP and CHANGELOG progress updates

## Design decision

The UI module imports GTK lazily. This keeps CLI usage and automated tests
working on environments where GTK/libadwaita are not installed.

## Next Sprint

Sprint 2.5 should wire the UI buttons to the backend manager, stream logs in
real time and add the connection timer.
