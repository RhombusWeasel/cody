"""Utility button widgets with built-in callbacks."""
from typing import Callable, Any

from textual.widgets import Button
from textual import on

from utils import icons


class ActionButton(Button):
    """A button that executes a callback when pressed."""

    def __init__(
        self,
        label: str,
        action: Callable[[], None] | None = None,
        tooltip: str | None = None,
        **kwargs: Any
    ):
        super().__init__(label, **kwargs)
        self._action_callback = action
        if tooltip:
            self.tooltip = tooltip

    @on(Button.Pressed)
    def _on_pressed(self, event: Button.Pressed) -> None:
        if self._action_callback:
            event.stop()
            self._action_callback()


class EditButton(ActionButton):
    """Button for edit actions."""
    def __init__(self, action: Callable[[], None] | None = None, tooltip: str = "Edit", label: str = icons.EDIT, **kwargs):
        kwargs.setdefault("classes", "action-btn edit-btn")
        super().__init__(label, action=action, tooltip=tooltip, **kwargs)


class DeleteButton(ActionButton):
    """Button for delete actions."""
    def __init__(self, action: Callable[[], None] | None = None, tooltip: str = "Delete", label: str = icons.DELETE, **kwargs):
        kwargs.setdefault("classes", "action-btn delete-btn")
        super().__init__(label, action=action, tooltip=tooltip, **kwargs)


class AddButton(ActionButton):
    """Button for add actions."""
    def __init__(self, action: Callable[[], None] | None = None, tooltip: str = "Add", label: str = "+", **kwargs):
        kwargs.setdefault("classes", "action-btn add-btn")
        super().__init__(label, action=action, tooltip=tooltip, **kwargs)


class RemoveButton(ActionButton):
    """Button for remove actions."""
    def __init__(self, action: Callable[[], None] | None = None, tooltip: str = "Remove", label: str = icons.DELETE, **kwargs):
        kwargs.setdefault("classes", "action-btn remove-btn")
        super().__init__(label, action=action, tooltip=tooltip, **kwargs)


class RefreshButton(ActionButton):
    """Button for refresh actions."""
    def __init__(self, action: Callable[[], None] | None = None, tooltip: str = "Refresh", label: str = icons.REFRESH, **kwargs):
        kwargs.setdefault("classes", "action-btn refresh-btn")
        super().__init__(label, action=action, tooltip=tooltip, **kwargs)


class RunButton(ActionButton):
    """Button for run actions."""
    def __init__(self, action: Callable[[], None] | None = None, tooltip: str = "Run", label: str = icons.RUN, **kwargs):
        kwargs.setdefault("classes", "action-btn run-btn")
        super().__init__(label, action=action, tooltip=tooltip, **kwargs)

