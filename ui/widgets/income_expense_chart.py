# ui/widgets/income_expense_chart.py - График доходов/расходов и остатка
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime, date
import numpy as np


class IncomeExpenseChart(ttk.Frame):
    """График доходов, расходов и остатка по месяцам."""
    
    def __init__(self, parent, db_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.db = db_manager
        
        self.configure(relief="solid", borderwidth=1)
        
        # Текущий год по умолчанию
        self.current_year = datetime.now().year
        
        # Создаем интерфейс
        self._setup_ui()
    
    def _setup_ui(self):
        """Настраивает интерфейс виджета."""
        # Заголовок и элементы управления
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        # ttk.Label(header_frame, text="📈 Динамика доходов/расходов", 
                 # font=("TkDefaultFont", 11, "bold")).pack(side="left")
        
        # Выбор года (справа)
        year_frame = ttk.Frame(header_frame)
        year_frame.pack(side="right")
        
        ttk.Label(year_frame, text="Год:").pack(side="left", padx=(0, 5))
        
        self.year_var = tk.StringVar(value=str(self.current_year))
        self.year_combo = ttk.Combobox(year_frame, textvariable=self.year_var, 
                                      width=8, state="readonly")
        self.year_combo.pack(side="left")
        
        # Добавляем правильную привязку с учетом события
        self.year_combo.bind('<<ComboboxSelected>>', self._on_year_change)
        
        # Кнопка обновления
        ttk.Button(year_frame, text="Обновить", 
                  command=self.update_chart,
                  width=10).pack(side="left", padx=(5, 0))
        
        # Фрейм для графика
        self.chart_frame = ttk.Frame(self)
        self.chart_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        
        # Инициализируем переменные
        self.fig = None
        self.canvas = None
        
        # Заполняем годы
        self._populate_years()
        
        # Первоначальное обновление
        self.update_chart()
    
    def _on_year_change(self, event):
        """Обработчик изменения года."""
        self.update_chart()
    
    def _populate_years(self):
        """Заполняет список годов."""
        current_year = datetime.now().year
        # Годы от 2020 до текущего + 1
        years = list(range(2020, current_year + 2))
        self.year_combo['values'] = [str(year) for year in years]
    
    def update_chart(self):
        """Обновляет график с данными из БД."""
        # Очищаем предыдущий график
        if self.fig:
            plt.close(self.fig)
        
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        try:
            year = int(self.year_var.get())
        except ValueError:
            year = datetime.now().year
            self.year_var.set(str(year))
        
        # Получаем данные по месяцам
        monthly_data = self._get_monthly_data(year)
        
        if not monthly_data:
            # Показываем сообщение, если нет данных
            no_data_label = ttk.Label(self.chart_frame, 
                                     text=f"Нет данных за {year} год",
                                     font=("TkDefaultFont", 12, "italic"),
                                     foreground="#8b8b8b",
                                     justify="center")
            no_data_label.pack(expand=True, fill="both", padx=20, pady=20)
            return
        
        # Если данные есть, создаем график
        self.fig = Figure(figsize=(6, 4), dpi=70, facecolor='#f5f5f5')
        ax = self.fig.add_subplot(111)
        
        # Создаем новый график с максимальным использованием пространства
        self.fig = Figure(figsize=(6, 4), dpi=70, facecolor='#f5f5f5')
        ax = self.fig.add_subplot(111)
        
        # Убираем отступы для максимального использования пространства
        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.15)
        
        # Подготавливаем данные
        months = list(range(1, 13))
        month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 
                      'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
        
        incomes = []
        expenses = []
        balances = []
        
        for month in months:
            month_key = f"{year}-{month:02d}"
            if month_key in monthly_data:
                data = monthly_data[month_key]
                incomes.append(data['income'])
                expenses.append(-data['expense'])
                balances.append(data['balance'])
            else:
                incomes.append(0)
                expenses.append(0)
                balances.append(0)
        
        # Создаем линейные графики
        line_incomes = ax.plot(months, incomes, label='Доходы', 
                               color='#2e7d32', marker='o', linewidth=2)
        line_expenses = ax.plot(months, expenses, label='Расходы',  # Используем положительные значения
                                color='#c62828', marker='s', linewidth=2)
        # line_balance = ax.plot(months, balances, label='Остаток', 
                               # color='#1565c0', marker='^', linewidth=2, linestyle='--')
        
        # Убираем подписи осей и заголовок
        ax.set_xlabel('')
        ax.set_ylabel('')
        
        # Устанавливаем метки месяцев на оси X (компактнее)
        ax.set_xticks(months)
        ax.set_xticklabels(month_names, rotation=45, fontsize=8)
        
        # Форматируем оси Y (с разделителями тысяч и символом валюты)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,} ₽'))
        
        # Увеличиваем размер шрифта для осей Y
        ax.tick_params(axis='y', labelsize=9)
        
        # Добавляем сетку
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Добавляем легенду (компактнее)
        ax.legend(loc='upper left', fontsize=8, framealpha=0.9)
        
        # Добавляем подписи к точкам для текущего месяца (если есть данные)
        if year == datetime.now().year:
            current_month = datetime.now().month
            if current_month <= len(incomes):
                # Подпись для доходов текущего месяца
                if incomes[current_month-1] > 0:
                    ax.annotate(f'{incomes[current_month-1]:,.0f} ₽', 
                               xy=(current_month, incomes[current_month-1]),
                               xytext=(5, 5), textcoords='offset points',
                               fontsize=7, color='#2e7d32')
                
                # Подпись для расходов текущего месяца
                if expenses[current_month-1] > 0:
                    ax.annotate(f'{expenses[current_month-1]:,.0f} ₽',  # Используем положительное значение
                               xy=(current_month, expenses[current_month-1]),
                               xytext=(5, -15), textcoords='offset points',
                               fontsize=7, color='#c62828')
        
        # Добавляем горизонтальную линию на уровне 0
        ax.axhline(y=0, color='gray', linewidth=0.5, linestyle='-', alpha=0.5)
        
        # Автоматически настраиваем пределы осей для лучшего отображения
        ax.set_xlim(0.5, 12.5)
        
        # Настраиваем отступы для максимального использования пространства
        self.fig.tight_layout(pad=0.1)
        
        # Создаем канвас для отображения графика
        self.canvas = FigureCanvasTkAgg(self.fig, self.chart_frame)
        self.canvas.draw()
        
        # Размещаем график
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True)
        
    def _get_monthly_data(self, year):
        """Получает данные по месяцам за указанный год."""
        try:
            data = self.db.get_yearly_summary(year)
            # Проверяем наличие данных
            if not data:
                return {}
            return data
        except Exception as e:
            print(f"DEBUG: Ошибка получения данных: {e}")
            return {}

            
    def destroy(self):
        """Корректное удаление виджета."""
        if self.fig:
            plt.close(self.fig)
        super().destroy()