from textual.app import App, ComposeResult
from textual.widgets import Input, SelectionList
from thoughtcli.ui import (
    RadioListDialog,
    CheckboxListDialog,
    InputDialog,
    ConfirmDialog,
    MessageDialog,
)


class DialogTestApp(App):
    """Helper app that opens a dialog and stores the result."""

    def __init__(self, dialog):
        super().__init__()
        self._dialog = dialog
        self.result = None

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self):
        def capture(result):
            self.result = result
            self.exit()

        self.push_screen(self._dialog, callback=capture)


async def test_radio_list_ok():
    app = DialogTestApp(RadioListDialog("Title", "Choose", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        await pilot.click("RadioButton")
        await pilot.click("#ok")
    assert app.result == "a"


async def test_radio_list_selects_second_option():
    app = DialogTestApp(RadioListDialog("Title", "Choose", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        second_button = pilot.app.screen.query("RadioButton").nodes[1]
        await pilot.click(second_button)
        await pilot.click("#ok")
    assert app.result == "b"


async def test_radio_list_ok_without_selection():
    app = DialogTestApp(RadioListDialog("Title", "Choose", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        await pilot.click("#ok")
    assert app.result is None


async def test_radio_list_cancel():
    app = DialogTestApp(RadioListDialog("Title", "Choose", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        await pilot.click("#cancel")
    assert app.result is None


async def test_radio_list_escape_returns_none():
    app = DialogTestApp(RadioListDialog("Title", "Choose", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        await pilot.press("escape")
    assert app.result is None


async def test_checkbox_list_ok_with_selection():
    app = DialogTestApp(CheckboxListDialog("Title", "Pick", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        pilot.app.screen.query_one(SelectionList).select("a")
        await pilot.click("#ok")
    assert app.result == ["a"]


async def test_checkbox_list_ok_with_multiple_selections():
    app = DialogTestApp(CheckboxListDialog("Title", "Pick", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        sl = pilot.app.screen.query_one(SelectionList)
        sl.select("a")
        sl.select("b")
        await pilot.click("#ok")
    assert app.result == ["a", "b"]


async def test_checkbox_list_ok_with_no_selection():
    app = DialogTestApp(CheckboxListDialog("Title", "Pick", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        await pilot.click("#ok")
    assert app.result == []


async def test_checkbox_list_cancel_returns_empty():
    app = DialogTestApp(CheckboxListDialog("Title", "Pick", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        await pilot.click("#cancel")
    assert app.result == []


async def test_checkbox_list_escape_returns_empty():
    app = DialogTestApp(CheckboxListDialog("Title", "Pick", [("a", "A"), ("b", "B")]))
    async with app.run_test() as pilot:
        await pilot.press("escape")
    assert app.result == []


async def test_input_dialog_submit():
    app = DialogTestApp(InputDialog("Commit", "Enter message:"))
    async with app.run_test() as pilot:
        pilot.app.screen.query_one("#text-input", Input).value = "my commit message"
        await pilot.click("#ok")
    assert app.result == "my commit message"


async def test_input_dialog_enter_submits():
    app = DialogTestApp(InputDialog("Commit", "Enter message:"))
    async with app.run_test() as pilot:
        pilot.app.screen.query_one("#text-input", Input).value = "my commit message"
        await pilot.press("enter")
    assert app.result == "my commit message"


async def test_input_dialog_empty_returns_none():
    app = DialogTestApp(InputDialog("Commit", "Enter message:"))
    async with app.run_test() as pilot:
        await pilot.click("#ok")
    assert app.result is None


async def test_input_dialog_cancel():
    app = DialogTestApp(InputDialog("Commit", "Enter message:"))
    async with app.run_test() as pilot:
        await pilot.click("#cancel")
    assert app.result is None


async def test_input_dialog_escape_returns_none():
    app = DialogTestApp(InputDialog("Commit", "Enter message:"))
    async with app.run_test() as pilot:
        await pilot.press("escape")
    assert app.result is None


async def test_confirm_dialog_confirm():
    app = DialogTestApp(ConfirmDialog("Delete", "Are you sure?"))
    async with app.run_test() as pilot:
        await pilot.click("#ok")
    assert app.result is True


async def test_confirm_dialog_cancel():
    app = DialogTestApp(ConfirmDialog("Delete", "Are you sure?"))
    async with app.run_test() as pilot:
        await pilot.click("#cancel")
    assert app.result is False


async def test_confirm_dialog_escape_returns_false():
    app = DialogTestApp(ConfirmDialog("Delete", "Are you sure?"))
    async with app.run_test() as pilot:
        await pilot.press("escape")
    assert app.result is False


async def test_message_dialog_closes_on_ok():
    app = DialogTestApp(MessageDialog("Done!"))
    async with app.run_test() as pilot:
        await pilot.click("#ok")
    assert app.result is None


async def test_message_dialog_enter():
    app = DialogTestApp(MessageDialog("Done!"))
    async with app.run_test() as pilot:
        await pilot.press("enter")
    assert app.result is None


async def test_message_dialog_escape():
    app = DialogTestApp(MessageDialog("Done!"))
    async with app.run_test() as pilot:
        await pilot.press("escape")
    assert app.result is None
