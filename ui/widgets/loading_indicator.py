# ui/widgets/loading_indicator.py - Индикатор загрузки
import tkinter as tk
from tkinter import ttk


class LoadingIndicator:
    """Индикатор загрузки с анимированными точками."""
    
    def __init__(self, parent, text="Загрузка..."):
        self.parent = parent
        self.text = text
        self.is_loading = False
        self.bg_color = '#f5f5f5'
        self.frame = None
        self._animation_id = None
        
    def start(self, text=None):
        """Начинает анимацию загрузки."""
        if text:
            self.text = text
        
        # Уничтожаем старый фрейм если есть
        if self.frame and self.frame.winfo_exists():
            self.stop()
        
        self.is_loading = True
        
        # Создаем новый фрейм поверх всего
        self.frame = tk.Frame(self.parent, bg=self.bg_color, relief="solid", borderwidth=1)
        self.frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)
        self.frame.lift()  # Поднимаем на передний план
        
        # Настраиваем интерфейс
        self._setup_ui()
        
        # Запускаем анимацию
        self._animate(0)
        
        # Принудительное обновление
        self.frame.update()
    
    def _setup_ui(self):
        """Настраивает интерфейс индикатора."""
        # Центральный фрейм
        center_frame = tk.Frame(self.frame, bg=self.bg_color)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Текст
        self.label = tk.Label(center_frame, text=self.text,
                             font=("TkDefaultFont", 10),
                             bg=self.bg_color)
        self.label.pack(pady=(0, 15))
        
        # Фрейм для анимации
        self.animation_frame = tk.Frame(center_frame, bg=self.bg_color)
        self.animation_frame.pack()
        
        # Создаем 3 точки
        self.dots = []
        dot_colors = ['#4CAF50', '#2196F3', '#FF9800']
        for i in range(3):
            dot = tk.Canvas(self.animation_frame, width=20, height=20,
                           highlightthickness=0, bg=self.bg_color)
            dot.create_oval(5, 5, 15, 15, fill='#cccccc', outline='')
            dot.pack(side="left", padx=5)
            self.dots.append((dot, dot_colors[i]))
    
    def _animate(self, dot_index=0):
        """Анимирует точки (рекурсивно)."""
        if not self.is_loading:
            return
        
        # Обновляем цвета точек
        for i, (dot, color) in enumerate(self.dots):
            if i == dot_index:
                dot.itemconfig(1, fill=color)  # Подсвечиваем текущую точку
            else:
                dot.itemconfig(1, fill='#cccccc')  # Остальные серые
        
        # Переключаемся на следующую точку
        next_dot = (dot_index + 1) % 3
        
        # Отменяем предыдущую анимацию если есть
        if self._animation_id:
            try:
                self.frame.after_cancel(self._animation_id)
            except:
                pass
        
        # Планируем следующий кадр анимации
        self._animation_id = self.frame.after(300, lambda: self._animate(next_dot))
    
    def stop(self):
        """Останавливает анимацию загрузки."""
        self.is_loading = False
        
        # Отменяем анимацию
        if self._animation_id:
            try:
                self.frame.after_cancel(self._animation_id)
                self._animation_id = None
            except:
                pass
        
        # Уничтожаем фрейм
        if self.frame and self.frame.winfo_exists():
            self.frame.destroy()
            self.frame = None
    
    def __del__(self):
        """Деструктор для очистки ресурсов."""
        self.stop()