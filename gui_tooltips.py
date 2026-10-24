"""Small hover tips for the Tkinter interface."""
import tkinter as tk
from tkinter import ttk


class ToolTip:
    """Show help after a short hover without taking keyboard focus."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.timer = None
        self.window = None
        widget.bind('<Enter>', self.schedule, add='+')
        for event in ('<Leave>', '<ButtonPress>', '<KeyPress>', '<FocusOut>',
                      '<Unmap>', '<Destroy>'):
            widget.bind(event, self.hide, add='+')

    def schedule(self, event=None):
        self.hide()
        self.timer = self.widget.after(500, self.show)

    def show(self):
        self.timer = None
        if not self.widget.winfo_viewable():
            return
        window = self.window = tk.Toplevel(self.widget, takefocus=False)
        window.withdraw()
        window.overrideredirect(True)
        ttk.Label(window, text=self.text, wraplength=300, justify='left',
                  padding=8, relief='solid', borderwidth=1).pack()
        window.update_idletasks()
        x = min(self.widget.winfo_rootx() + 12,
                window.winfo_screenwidth() - window.winfo_reqwidth() - 8)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        if y + window.winfo_reqheight() > window.winfo_screenheight() - 8:
            y = self.widget.winfo_rooty() - window.winfo_reqheight() - 6
        window.geometry(f'+{max(0, x)}+{max(0, y)}')
        window.deiconify()

    def hide(self, event=None):
        if self.timer is not None:
            self.widget.after_cancel(self.timer)
            self.timer = None
        if self.window is not None:
            self.window.destroy()
            self.window = None


def add_tooltip(widget, text):
    widget.tooltip = ToolTip(widget, text)
    return widget
