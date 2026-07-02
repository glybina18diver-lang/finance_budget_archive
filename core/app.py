# core/app.py
import tkinter as tk
from tkinter import ttk, messagebox

from core.database import DatabaseManager
from core.window_manager import SmartWindowManager  # ← ДОБАВЬТЕ ЭТО
from ui.main_window import MainWindow
from ui.widgets.window_utils import center_window

class BudgetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
                
        self.title("Простой Бюджет (Tkinter) - SQLite")
        self.geometry("1300x680")
        
        # Менеджер окон
        self.window_manager = SmartWindowManager(self)
        
        # ДЕБАГ: покажем что нашлось
        print("=== АВТООБНАРУЖЕННЫЕ ОКНА ===")
        for window_id, cls in self.window_manager.window_classes.items():
            print(f"  {window_id} -> {cls.__name__}")
        
        # Создаем главное окно с логикой
        self.main_window = MainWindow(self, self.db)
        self.main_window.pack(fill="both", expand=True)
        
        print("Центрируем окно...")
        self.update_idletasks()
        center_window(self)
        
        self.protocol("WM_DELETE_WINDOW", self._on_main_window_close)
        
        # Привязываем Alt+Tab для поднятия всех окон
        self.bind("<Alt-Tab>", self._bring_all_to_front)

    def _bring_all_to_front(self, event=None):
        """Поднимает все открытые окна."""
        self.lift()
        if hasattr(self, 'main_window'):
            self.main_window._bring_all_to_front(event)
        for window_type, window in self.open_windows.items():
            if window and window.winfo_exists():
                window.lift()
    
    
        
    def show_window(self, window_id: str, *args, **kwargs):
        """Универсальный метод показа окна"""
        return self.window_manager.show_window(window_id, *args, **kwargs)
    
    def _on_main_window_close(self):
        """Закрывает все дочерние окна"""
        self.window_manager.close_all()
        self.destroy()


# --- ЗАПУСК ПРИЛОЖЕНИЯ ---
if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()