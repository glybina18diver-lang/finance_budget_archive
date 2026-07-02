import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter
import matplotlib.pyplot as plt
from datetime import datetime
import threading
import time

# import tkinter as tk
# from tkinter import ttk
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.database import DatabaseManager


'''def center_window_relative(window, parent=None):
    """
    Центрирует окно относительно родителя или экрана.
    """
    window.update_idletasks()
    
    width = window.winfo_width()
    height = window.winfo_height()
    
    # Если размеры не определены
    if width <= 1 or height <= 1:
        try:
            geometry = window.geometry()
            if 'x' in geometry:
                geom_parts = geometry.split('+')[0]
                width, height = map(int, geom_parts.split('x'))
            else:
                width, height = 1000, 650
        except:
            width, height = 1000, 650
    
    if parent:
        # Центрируем относительно родителя
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
    else:
        # Центрируем на экране
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
    
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.lift()
    window.focus_force()
'''

def get_simple_taskbar_height():
    """
    Упрощенный метод определения высоты панели задач.
    """
    # Инициализируем переменные значениями по умолчанию
    screen_height = 1080
    
    try:
        # Пробуем получить высоту экрана
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
    except:
        # Если не получилось, оставляем значение по умолчанию
        pass
    
    try:
        # Получаем рабочую область
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)
            ]
        
        rect = RECT()
        # SPI_GETWORKAREA = 48
        success = ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
        
        if success:
            work_height = rect.bottom - rect.top
            taskbar_height = screen_height - work_height
            
            if 0 <= taskbar_height <= 100:
                return taskbar_height
    
    except:
        pass
    
    # Эмпирические значения на основе разрешения
    if screen_height <= 768:
        return 30
    elif screen_height <= 1080:
        return 40
    elif screen_height <= 1440:
        return 45
    else:
        return 50

def center_window(window):
    """
    Центрирует окно с автоматическим учетом панели задач.
    """
    try:
        window.update_idletasks()
        
        # Получаем размеры экрана
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # Автоматически определяем высоту панели задач
        try:
            taskbar_height = get_simple_taskbar_height()
            print(f"DEBUG: Высота панели задач определена как {taskbar_height}px")
        except Exception as e:
            print(f"DEBUG: Ошибка определения панели: {e}, используем 40px")
            taskbar_height = 40
        
        # Рассчитываем рабочую область
        work_height = screen_height - taskbar_height
        
        # Получаем размеры окна
        width = window.winfo_width()
        height = window.winfo_height()
        
        # Если размеры не определены
        if width <= 1 or height <= 1:
            width = min(800, screen_width * 0.8)
            height = min(600, work_height * 0.8)
            window.geometry(f"{int(width)}x{int(height)}")
            window.update_idletasks()
            width = window.winfo_width()
            height = window.winfo_height()
        
        # Ограничиваем максимальную высоту
        if height > work_height - 20:
            height = work_height - 40
            window.geometry(f"{width}x{height}")
        
        # Вычисляем позицию
        x = (screen_width - width) // 2-10
        y = (work_height - height) // 2-10
        
        # Устанавливаем позицию
        window.geometry(f"{width}x{height}+{x}+{y}")
        
        print(f"DEBUG: Окно размещено на позиции x={x}, y={y}, размер {width}x{height}")
        
        window.lift()
        window.focus_force()
        
    except Exception as e:
        print(f"ERROR: Ошибка при центрировании окна: {e}")
        # Просто размещаем по центру без учета панели задач
        window.update_idletasks()
        width = window.winfo_width() if window.winfo_width() > 1 else 800
        height = window.winfo_height() if window.winfo_height() > 1 else 600
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

class SimpleDashboard(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db = db_manager
        self.parent = parent
        self.title("Дашборд (Тестовый)")
        self.geometry("1350x700")  # Используем заданный размер
        # center_window_relative(self, self.parent)
        center_window(self)

        
        # Запрещаем изменение размера
        self.resizable(True, True)
        
        # Бинд для прокрутки
        self._bind_mousewheel()
        
        # Обработчик закрытия окна
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._init_ui()
        self._load_data_async()
        


    def _init_ui(self):
        # Основной контейнер с прокруткой
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True)
        
        # Создаем Canvas для прокрутки
        self.canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview)
        
        # Фрейм для содержимого внутри Canvas
        self.content_frame = ttk.Frame(self.canvas)
        
        # Конфигурация Canvas - фиксируем ширину
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Упаковка
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Обновление области прокрутки и ширины контента
        def update_scrollregion(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # Устанавливаем ширину контента равной ширине canvas
            self.canvas.itemconfig(self.canvas_frame, width=self.canvas.winfo_width())
        
        self.content_frame.bind("<Configure>", update_scrollregion)
        self.canvas.bind("<Configure>", lambda e: update_scrollregion())
        
        # Основной интерфейс
        self._create_widgets()
        
        # self.after(100, lambda: center_window_relative(self, self.parent))

    def _bind_mousewheel(self):
        """Привязка прокрутки мыши"""
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", self._on_mousewheel)  # Для Linux
        self.bind("<Button-5>", self._on_mousewheel)  # Для Linux

    def _unbind_mousewheel(self):
        """Отвязка прокрутки мыши"""
        self.unbind("<MouseWheel>")
        self.unbind("<Button-4>")
        self.unbind("<Button-5>")

    def _on_mousewheel(self, event):
        """Обработчик прокрутки колеса мыши"""
        # Проверяем, существует ли canvas
        if hasattr(self, 'canvas') and self.canvas.winfo_exists():
            try:
                # Определяем направление прокрутки
                if event.num == 4:  # Linux - вверх
                    self.canvas.yview_scroll(-1, "units")
                elif event.num == 5:  # Linux - вниз
                    self.canvas.yview_scroll(1, "units")
                else:  # Windows/Mac
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                pass  # Игнорируем ошибки если виджет уже уничтожен

    def _on_close(self):
        """Обработчик закрытия окна"""
        self._unbind_mousewheel()
        self.destroy()

    def _create_widgets(self):
        # Кнопка возврата
        return_btn = ttk.Button(self.content_frame, text="← К транзакциям", command=self._on_close)
        return_btn.pack(anchor="w", padx=20, pady=10)
        
        # Заголовок
        title_label = ttk.Label(self.content_frame, text="📊 Тестовый Дашборд (Ноябрь-Декабрь)", 
                               font=("TkDefaultFont", 16, "bold"))
        title_label.pack(pady=15)
        
        # Прогресс-бар
        self.progress_frame = ttk.Frame(self.content_frame)
        self.progress_frame.pack(fill="x", padx=30, pady=15)
        
        self.progress_label = ttk.Label(self.progress_frame, text="Загрузка данных...", 
                                       font=("TkDefaultFont", 11))
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate', length=500)
        self.progress_bar.pack(fill="x", pady=5)
        
        # Контейнер для графика
        self.chart_container = ttk.Frame(self.content_frame)
        self.chart_container.pack(fill="both", expand=True, padx=20, pady=15)
        self.chart_container.pack_propagate(False)
        self.chart_container.config(height=500)
        
        # Контейнер для статистики
        self.stats_frame = ttk.Frame(self.content_frame)
        self.stats_frame.pack(fill="x", padx=20, pady=15)

    def _load_data_async(self):
        self.progress_bar.start(10)
        
        def load_data():
            try:
                time.sleep(0.5)
                current_year = datetime.now().year
                
                self.after(0, lambda: self._update_progress("Загрузка ноября..."))
                nov_data = self.db.get_monthly_summary(current_year, 11)
                
                self.after(0, lambda: self._update_progress("Загрузка декабря..."))
                time.sleep(0.3)
                dec_data = self.db.get_monthly_summary(current_year, 12)
                
                self.after(0, lambda: self._update_progress("Загрузка данных по дням..."))
                daily_data = self._get_daily_data(current_year)
                
                self.after(0, lambda: self._update_progress("Построение графика..."))
                time.sleep(0.2)
                
                self.after(0, lambda: self._finish_loading(nov_data, dec_data, daily_data))
                
            except Exception as e:
                self.after(0, lambda: self._show_error(str(e)))
        
        threading.Thread(target=load_data, daemon=True).start()

    def _update_progress(self, text):
        if self.progress_label:
            self.progress_label.config(text=text)

    def _get_daily_data(self, year):
        try:
            transactions = self.db.get_transactions(
                date_from=f"{year}-11-01", 
                date_to=f"{year}-12-31"
            )
            
            print(f"DEBUG: Количество транзакций: {len(transactions)}")
            if transactions:
                print(f"DEBUG: Первая транзакция: {transactions[0]}")
                print(f"DEBUG: Количество значений в транзакции: {len(transactions[0])}")
            
            daily_income = {}
            daily_expense = {}
            
            for i, transaction in enumerate(transactions):
                try:
                    # Пробуем распаковать 9 значений
                    t_id, date, amount, t_type, category, description, account_name, account_id, extra = transaction
                    # print(f"DEBUG Транзакция {i}: date={date}, type={t_type}, amount={amount}")
                except ValueError:
                    # Если значений меньше 9, используем первые 8
                    t_id, date, amount, t_type, category, description, account_name, account_id = transaction[:8]
                
                if date and (date.startswith(f"{year}-11") or date.startswith(f"{year}-12")):
                    day_key = date
                    
                    if t_type == 'доход':
                        daily_income[day_key] = daily_income.get(day_key, 0) + float(amount)
                    elif t_type == 'расход':
                        daily_expense[day_key] = daily_expense.get(day_key, 0) + abs(float(amount))
            
            print(f"DEBUG: дней с доходами: {len(daily_income)}, дней с расходами: {len(daily_expense)}")
            
            return {
                'daily_income': daily_income,
                'daily_expense': daily_expense
            }
            
        except Exception as e:
            print(f"Error getting daily data: {e}")
            import traceback
            traceback.print_exc()
            return {'daily_income': {}, 'daily_expense': {}}

    def _finish_loading(self, nov_data, dec_data, daily_data):
        self.progress_bar.stop()
        self.progress_frame.pack_forget()
        
        self._create_chart(nov_data, dec_data, daily_data)
        self._create_stats(nov_data, dec_data)

    def _show_error(self, error_msg):
        self.progress_bar.stop()
        self.progress_label.config(text=f"Ошибка: {error_msg}", foreground="red")

    def _create_chart(self, nov_data, dec_data, daily_data):
        for widget in self.chart_container.winfo_children():
            widget.destroy()
        
        # Создание графика большого размера
        fig = Figure(figsize=(13, 4.5), dpi=100)
        ax = fig.add_subplot(111)
        
        # Подготовка данных
        dates = []
        income_values = []
        expense_values = []
        
        all_dates = sorted(set(list(daily_data['daily_income'].keys()) + 
                              list(daily_data['daily_expense'].keys())))
        
        for date_str in all_dates:
            dates.append(datetime.strptime(date_str, '%Y-%m-%d'))
            income_values.append(daily_data['daily_income'].get(date_str, 0))
            expense_values.append(daily_data['daily_expense'].get(date_str, 0))
        
        if not dates:
            dates = [datetime(2025, 11, i) for i in range(1, 31)] + \
                    [datetime(2025, 12, i) for i in range(1, 32)]
            
            nov_income = nov_data.get("total_income", 0)
            nov_expense = abs(nov_data.get("total_expense", 0))
            dec_income = dec_data.get("total_income", 0)
            dec_expense = abs(dec_data.get("total_expense", 0))
            
            income_values = ([nov_income/30]*30 if nov_income > 0 else [0]*30) + \
                           ([dec_income/31]*31 if dec_income > 0 else [0]*31)
            expense_values = ([nov_expense/30]*30 if nov_expense > 0 else [0]*30) + \
                            ([dec_expense/31]*31 if dec_expense > 0 else [0]*31)
        
        # Отрисовка графиков
        ax.plot(dates, income_values, label='Доходы', color='#27ae60', 
                linewidth=2.5, marker='o', markersize=4, alpha=0.8)
        ax.plot(dates, expense_values, label='Расходы', color='#c0392b', 
                linewidth=2.5, marker='s', markersize=4, alpha=0.8)
        
        # Добавление подписей для ключевых точек
        if len(dates) <= 20:
            for i, (date, income, expense) in enumerate(zip(dates, income_values, expense_values)):
                if income > 1000:  # Только значимые значения
                    income_offset = 8 if i % 2 == 0 else 18
                    ax.annotate(f'{income:,.0f}', 
                               (date, income),
                               textcoords="offset points",
                               xytext=(0, income_offset),
                               ha='center',
                               fontsize=8,
                               color='#27ae60',
                               alpha=0.9)
                
                if expense > 1000:  # Только значимые значения
                    expense_offset = -8 if i % 2 == 0 else -18
                    ax.annotate(f'{expense:,.0f}', 
                               (date, expense),
                               textcoords="offset points",
                               xytext=(0, expense_offset),
                               ha='center',
                               fontsize=8,
                               color='#c0392b',
                               alpha=0.9)
        
        # Настройка графика
        ax.set_xlabel('Дата', fontsize=11)
        ax.set_ylabel('Сумма (руб)', fontsize=11)
        ax.set_title('Динамика доходов и расходов (Ноябрь-Декабрь 2025)', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Форматирование осей
        ax.xaxis.set_major_formatter(DateFormatter('%d.%m'))
        fig.autofmt_xdate(rotation=30, ha='right')
        
        max_value = max(max(income_values) if income_values else 0, 
                       max(expense_values) if expense_values else 0, 1000)
        ax.set_ylim(0, max_value * 1.2)
        
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K' if x >= 1000 else f'{x:.0f}'))
        fig.tight_layout()
        
        # Встраивание графика
        canvas = FigureCanvasTkAgg(fig, self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _create_stats(self, nov_data, dec_data):
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        # Данные
        nov_income = nov_data.get("total_income", 0) if nov_data else 0
        nov_expense = abs(nov_data.get("total_expense", 0)) if nov_data else 0
        nov_balance = nov_income - nov_expense
        
        dec_income = dec_data.get("total_income", 0) if dec_data else 0
        dec_expense = abs(dec_data.get("total_expense", 0)) if dec_data else 0
        dec_balance = dec_income - dec_expense
        
        total_income = nov_income + dec_income
        total_expense = nov_expense + dec_expense
        total_balance = total_income - total_expense
        
        # Создание статистики
        stats_container = ttk.Frame(self.stats_frame)
        stats_container.pack(fill="x", expand=True, padx=10)
        
        # Ноябрь
        nov_frame = ttk.LabelFrame(stats_container, text="📈 НОЯБРЬ 2025", padding=10)
        nov_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        ttk.Label(nov_frame, text=f"Доходы: {nov_income:,.0f} ₽", 
                 font=("TkDefaultFont", 11)).pack(anchor="w", pady=2)
        ttk.Label(nov_frame, text=f"Расходы: {nov_expense:,.0f} ₽", 
                 font=("TkDefaultFont", 11)).pack(anchor="w", pady=2)
        ttk.Label(nov_frame, text=f"Баланс: {nov_balance:+,.0f} ₽", 
                 font=("TkDefaultFont", 11, "bold"),
                 foreground="green" if nov_balance >= 0 else "red").pack(anchor="w", pady=2)
        
        # Декабрь
        dec_frame = ttk.LabelFrame(stats_container, text="📈 ДЕКАБРЬ 2025", padding=10)
        dec_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        ttk.Label(dec_frame, text=f"Доходы: {dec_income:,.0f} ₽", 
                 font=("TkDefaultFont", 11)).pack(anchor="w", pady=2)
        ttk.Label(dec_frame, text=f"Расходы: {dec_expense:,.0f} ₽", 
                 font=("TkDefaultFont", 11)).pack(anchor="w", pady=2)
        ttk.Label(dec_frame, text=f"Баланс: {dec_balance:+,.0f} ₽", 
                 font=("TkDefaultFont", 11, "bold"),
                 foreground="green" if dec_balance >= 0 else "red").pack(anchor="w", pady=2)
        
        # Общее
        total_frame = ttk.LabelFrame(stats_container, text="📊 ОБЩАЯ СТАТИСТИКА", padding=10)
        total_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        ttk.Label(total_frame, text=f"Доходы: {total_income:,.0f} ₽", 
                 font=("TkDefaultFont", 11)).pack(anchor="w", pady=2)
        ttk.Label(total_frame, text=f"Расходы: {total_expense:,.0f} ₽", 
                 font=("TkDefaultFont", 11)).pack(anchor="w", pady=2)
        ttk.Label(total_frame, text=f"Баланс: {total_balance:+,.0f} ₽", 
                 font=("TkDefaultFont", 12, "bold"),
                 foreground="green" if total_balance >= 0 else "red").pack(anchor="w", pady=2)


