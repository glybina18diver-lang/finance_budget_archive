import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta, date
import calendar
from tkinter import simpledialog
import tkinter.font as tkfont
 


class TtkCalendar(ttk.Frame):
    """Кастомный календарь для TtkDateEntry."""
    def __init__(self, parent, command=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.command = command
        
        self.russian_months = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }
        
        self.year_var = tk.IntVar(self, value=date.today().year)
        self.month_var = tk.IntVar(self, value=date.today().month)
        
        self._build_header()
        self._build_calendar_grid()
        
        self._update_calendar()

    def _build_header(self):
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x")

        ttk.Button(header_frame, text="◀", command=self._prev_month, width=3).pack(side="left", padx=2)
        
        self.month_label = ttk.Label(header_frame, text="", font="TkDefaultFont 10 bold")
        self.month_label.pack(side="left", expand=True, fill="x")
        
        self.year_label = ttk.Label(header_frame, text="", font="TkDefaultFont 10 bold")
        self.year_label.pack(side="right", expand=True, fill="x")
        
        ttk.Button(header_frame, text="▶", command=self._next_month, width=3).pack(side="right", padx=2)

    def _build_calendar_grid(self):
        self.calendar_frame = ttk.Frame(self)
        self.calendar_frame.pack()
        
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for i, day in enumerate(days):
            ttk.Label(self.calendar_frame, text=day, width=4, anchor="center", 
                     font="TkDefaultFont 8 bold").grid(row=0, column=i, pady=2)
        
        self.day_buttons = []
        for row in range(6): 
            row_buttons = []
            for col in range(7): 
                btn = ttk.Button(self.calendar_frame, text="", width=4,
                               command=lambda r=row, c=col: self._select_date(r, c))
                btn.grid(row=row+1, column=col, padx=1, pady=1)
                row_buttons.append(btn)
            self.day_buttons.append(row_buttons)

    def _update_calendar(self):
        year = self.year_var.get()
        month = self.month_var.get()

        self.month_label.config(text=f"{self.russian_months[month]}")
        self.year_label.config(text=str(year))

        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdatescalendar(year, month)
        
        for row_idx, week in enumerate(month_days):
            for col_idx, day_date in enumerate(week):
                btn = self.day_buttons[row_idx][col_idx]
                btn.config(text=str(day_date.day))
                btn.day_date = day_date

                if day_date.month == month:
                    btn.config(state="normal", style="")
                else:
                    btn.config(state="disabled")
                    btn.config(text=f"{day_date.day}", style="Secondary.TButton")

    def _prev_month(self):
        current_month = self.month_var.get()
        current_year = self.year_var.get()
        
        if current_month == 1:
            self.month_var.set(12)
            self.year_var.set(current_year - 1)
        else:
            self.month_var.set(current_month - 1)
            
        self._update_calendar()

    def _next_month(self):
        current_month = self.month_var.get()
        current_year = self.year_var.get()
        
        if current_month == 12:
            self.month_var.set(1)
            self.year_var.set(current_year + 1)
        else:
            self.month_var.set(current_month + 1)
            
        self._update_calendar()

    def _select_date(self, row, col):
        btn = self.day_buttons[row][col]
        if btn['state'] == 'normal':
            selected_date = btn.day_date
            if self.command:
                self.command(selected_date, close=True)

class TtkDateEntry(ttk.Frame):
    """Виджет для ввода даты с календарным попапом."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.var = tk.StringVar(self)
        
        self.entry = ttk.Entry(self, textvariable=self.var, width=12)
        self.entry.pack(side="left", fill="x", expand=True)
        
        self.calendar_button = ttk.Button(self, text="📅", command=self._show_calendar, width=3)
        self.calendar_button.pack(side="right", padx=(2, 0))

        self.var.set(date.today().strftime('%Y-%m-%d'))
        self._calendar_toplevel = None

    def get_date(self):
        return self.var.get()

    def _show_calendar(self, event=None):
        top = tk.Toplevel(self)
        top.title("Выбрать дату")
        
        self.entry.update_idletasks()
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        top.geometry(f"+{x}+{y}")
        
        cal = TtkCalendar(top, command=self._set_selected_date)
        cal.pack(padx=10, pady=10)
        
        ttk.Button(top, text="Сегодня", 
                  command=lambda: self._set_selected_date(date.today(), close=True)).pack(pady=5)

        self._calendar_toplevel = top 
        top.transient(self.winfo_toplevel())
        top.grab_set()
        top.focus_set()

    def _set_selected_date(self, selected_date, close=False):
        if selected_date:
            self.var.set(selected_date.strftime('%Y-%m-%d'))
        if close and self._calendar_toplevel and self._calendar_toplevel.winfo_exists():
            self._calendar_toplevel.destroy()