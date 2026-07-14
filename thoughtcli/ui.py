from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, SelectionList, Static
from textual.widgets._toggle_button import ToggleButton
from rich.markup import escape

ToggleButton.BUTTON_INNER = "✓"

_DIALOG_CSS = """
    align: center middle;

    Vertical {
        width: 50%;
        height: auto;
        max-height: 100vh;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    RadioSet {
        max-height: 50vh;
        overflow-x: auto;
        overflow-y: auto;
    }

    SelectionList {
        max-height: 50vh;
        overflow-y: auto;
        overflow-x: auto;
    }

    #dialog-title {
        text-style: bold;
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }

    Horizontal {
        height: auto;
        align: right middle;
        margin-top: 1;
    }

    Button {
        margin-left: 1;
    }
"""


class RadioListDialog(ModalScreen[str | None]):
    """Modal dialog for selecting a single option from a list."""

    DEFAULT_CSS = f"RadioListDialog {{{_DIALOG_CSS}}}"

    def __init__(self, title: str, text: str, values: list[tuple[str, str]]):
        super().__init__()
        self._dialog_title = title
        self._text = text
        self._values = values
        self._user_selected = False

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._dialog_title, id="dialog-title")
            yield Label(self._text)
            with RadioSet():
                for _value, label in self._values:
                    yield RadioButton(escape(label))
            with Horizontal():
                yield Button("OK", id="ok")
                yield Button("Cancel", id="cancel")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        self._user_selected = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            if not self._user_selected:
                self.notify("Please select an option.", severity="error")
                return
            radio_set = self.query_one(RadioSet)
            if self._values:
                self.dismiss(self._values[radio_set.pressed_index][0])
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class CheckboxListDialog(ModalScreen[list[str]]):
    """Modal dialog for selecting multiple options from a list."""

    DEFAULT_CSS = f"CheckboxListDialog {{{_DIALOG_CSS}}}"

    def __init__(self, title: str, text: str, values: list[tuple[str, str]]):
        super().__init__()
        self._dialog_title = title
        self._text = text
        self._values = values

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._dialog_title, id="dialog-title")
            yield Label(self._text)
            yield SelectionList(*[(escape(label), value) for value, label in self._values])
            with Horizontal():
                yield Button("OK", id="ok")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(list(self.query_one(SelectionList).selected))
        else:
            self.dismiss([])

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss([])


class InputDialog(ModalScreen[str | None]):
    """Modal dialog for text input."""

    DEFAULT_CSS = f"InputDialog {{{_DIALOG_CSS}}}"

    def __init__(self, title: str, text: str):
        super().__init__()
        self._dialog_title = title
        self._text = text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._dialog_title, id="dialog-title")
            yield Label(self._text)
            yield Input(id="text-input")
            with Horizontal():
                yield Button("OK", id="ok")
                yield Button("Cancel", id="cancel")

    def _submit(self) -> None:
        value = self.query_one(Input).value.strip()
        self.dismiss(value if value else None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class MessageDialog(ModalScreen[None]):
    """Modal dialog for displaying a result message."""

    DEFAULT_CSS = f"MessageDialog {{{_DIALOG_CSS}}} MessageDialog Horizontal {{ align: center middle; }}"

    def __init__(self, text: str):
        super().__init__()
        self._text = text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._text, id="message")
            with Horizontal():
                yield Button("OK", id="ok")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def on_key(self, event) -> None:
        if event.key in ("escape", "enter"):
            self.dismiss()
