"""
Custom button implementation using Static widgets.
"""
from textual.widgets import Static
from textual.reactive import reactive
from textual.message import Message
from textual import events


class CustomButton(Static):
    """A custom button widget that ensures text is always visible."""
    
    class Pressed(Message):
        """Button was pressed."""
        def __init__(self, button: "CustomButton") -> None:
            super().__init__()
            self.button = button
    
    text = reactive("")
    disabled = reactive(False)
    
    def __init__(
        self, 
        text: str, 
        *,
        id: str = None,
        classes: str = None,
        disabled: bool = False
    ):
        super().__init__(f" {text} ", id=id, classes=classes)
        self.text = text
        self.disabled = disabled
        self.can_focus = not disabled
        
    def on_click(self, event: events.Click) -> None:
        """Handle click events."""
        if not self.disabled:
            self.post_message(self.Pressed(self))
    
    def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        if event.key in ("enter", " ") and not self.disabled:
            self.post_message(self.Pressed(self))
    
    def watch_disabled(self, disabled: bool) -> None:
        """React to disabled state changes."""
        self.can_focus = not disabled
        if disabled:
            self.add_class("disabled")
        else:
            self.remove_class("disabled")
    
    def render(self) -> str:
        """Render the button text."""
        return f" {self.text} "