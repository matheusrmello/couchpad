---
name: couchpad-frontend
description: Implement and validate CouchPad desktop interfaces in Qt Quick/QML, connecting to the existing Python service and preserving session controls and preferences.
---

# CouchPad frontend

Use the approved mockup as visual direction and actual project behavior as the source of truth. Keep navigation, status, controls and device settings usable at smaller window sizes; expose accessible labels and keyboard focus. Preserve configuration, tray, autosave, launcher options and recovery semantics when replacing an interface. Keep long-running IPC and discovery off the UI thread and update Qt objects on the GUI thread. Do not simulate successful device operations or report fabricated device state.

Before replacing an entry point, exercise startup, disconnected service, actions, persistence, shutdown and device discovery. Test QML loading and representative interactions with a mocked daemon and isolated XDG paths, then run the project's regression suite. Verify packaging separately and disclose any untested or incomplete migration. Follow AGENTS.md and the current user request.
