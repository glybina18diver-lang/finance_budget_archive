import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative
from ui.widgets.calendar_widgets import TtkDateEntry  # если используете0

class DateRangeDialog(tk.Toplevel):
    """Диалог для выбора диапазона дат с помощью TtkDateEntry."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.date_from_str = None
        self.date_to_str = None
        self.result = None
        
        self.last_selected_date = getattr(parent, 'last_selected_date', date.today().strftime('%Y-%m-%d'))
        
        self.title("Выбрать диапазон дат")
        self.geometry("250x150")
        
        center_window_relative(self, self.parent)
        
        # self.transient(parent)
        # self.grab_set()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self._create_ui()
        
        self.wait_window()
    
    def _create_ui(self):
        """Создание интерфейса диалога."""
        ttk.Label(self, text="Дата от:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.date_from_entry = TtkDateEntry(self)
        self.date_from_entry.var.set("")
        self.date_from_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self, text="Дата до:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.date_to_entry = TtkDateEntry(self)
        self.date_to_entry.var.set("")
        self.date_to_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        button_frame = ttk.Frame(self)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self._apply).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.on_close).pack(side="right", padx=5)
        
        self.grid_columnconfigure(1, weight=1)
        
        return self.date_from_entry
    
    def _apply(self):
        """Применяет выбранные даты."""
        self.date_from_str = self.date_from_entry.get_date() if self.date_from_entry.get_date() else None
        self.date_to_str = self.date_to_entry.get_date() if self.date_to_entry.get_date() else None

        if self.date_from_str and self.date_to_str:
            if self.date_from_str > self.date_to_str:
                tk.messagebox.showerror("Ошибка ввода", "'Дата от' не может быть позже 'Дата до'.", parent=self)
                return
        
        self.result = (self.date_from_str, self.date_to_str)
        self.on_close()
    
    def on_close(self):
        """Закрывает диалоговое окно."""
        self.grab_release()
        self.destroy()