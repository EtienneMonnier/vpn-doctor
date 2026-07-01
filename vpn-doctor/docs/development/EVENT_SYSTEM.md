# Event System

## Purpose

The event system lets backends, diagnostics and services communicate without coupling
directly to the GUI.

## Event examples

- `LogEvent`
- `StatusChangedEvent`
- `DiagnosticStartedEvent`
- `DiagnosticCompletedEvent`
- `BackendProcessStartedEvent`
- `BackendProcessStoppedEvent`

## Why events matter

The future GTK UI needs live updates:

- progress bar;
- log viewer;
- connection timer;
- status pill;
- notifications.

Backends should emit events. The UI should subscribe through the controller or service
layer.

## Initial implementation

The current `core/events.py` contains simple dataclasses. A full event bus can be
added later when the GTK UI requires it.
