# ui/widgets/pie_chart_widget.py - Виджет круговой диаграммы
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime, timedelta
import matplotlib.patheffects as path_effects


class PieChartWidget(ttk.Frame):
    """Виджет круговой диаграммы расходов по категориям."""
    
    def __init__(self, parent, db_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.db = db_manager
        
        self.configure(relief="solid", borderwidth=1)
        
        # УБИРАЕМ ЗАГОЛОВОК И КНОПКУ - только диаграмма
        
        # Фрейм для диаграммы - заполняет весь виджет
        self.chart_frame = ttk.Frame(self)
        self.chart_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Инициализируем переменные
        self.fig = None
        self.canvas = None
        
        # УБИРАЕМ КНОПКУ ОБНОВЛЕНИЯ
        
        # Первоначальное обновление
        self.update_chart()
    
    def _get_current_month_range(self):
        """Получает диапазон дат для текущего месяца."""
        today = datetime.now()
        # Первый день текущего месяца
        date_from = datetime(today.year, today.month, 1)
        # Последний день текущего месяца
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)
        date_to = next_month - timedelta(days=1)
        
        return date_from, date_to
    
    def update_chart(self):
        """Обновляет диаграмму с данными из БД."""
        # Очищаем предыдущую диаграмму
        if self.fig:
            plt.close(self.fig)
        
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Получаем диапазон дат для текущего месяца
        date_from, date_to = self._get_current_month_range()
        
        # Получаем статистику по категориям за текущий месяц
        try:
            stats = self.db.get_category_statistics(
                include_subcategories=True,
                date_from=date_from,
                date_to=date_to
            )
        except Exception as e:
            # Показываем сообщение об ошибке
            error_label = ttk.Label(self.chart_frame, 
                                   text=f"Ошибка загрузки данных:\n{str(e)}",
                                   font=("TkDefaultFont", 9, "italic"),
                                   foreground="red",
                                   justify="center")
            error_label.pack(expand=True, fill="both")
            return
        
        # Фильтруем только расходы
        expense_stats = []
        for stat in stats:
            cat_id, name, cat_type, budget, parent_id, total_expense, total_income, count, avg_amount = stat
            if cat_type == 'expense' and total_expense > 0 and parent_id is None:
                expense_stats.append({
                    'name': name,
                    'amount': total_expense,
                    'count': count
                })
        
        if not expense_stats:
            # Показываем сообщение, если нет данных
            no_data_label = ttk.Label(self.chart_frame, 
                                     text="Нет данных по расходам\nза текущий месяц",
                                     font=("TkDefaultFont", 9, "italic"),
                                     foreground="gray",
                                     justify="center")
            no_data_label.pack(expand=True, fill="both")
            return
        
        # Сортируем по убыванию суммы
        expense_stats.sort(key=lambda x: x['amount'], reverse=True)
        
        # Подготовка данных для диаграммы
        labels = []
        amounts = []
        
        # Контрастная, но не яркая палитра
        color_palette = [
            '#2E5D7E', '#3A7B5F', '#6A4C93', '#8B4513', '#2F4F4F',
            '#556B2F', '#483D8B', '#8B0000', '#5D4037', '#4A6572',
            '#6B4226', '#4B0082', '#006400', '#8B7355', '#2F4F4F',
            '#8B6969', '#5F9EA0', '#696969', '#8B636C', '#708090'
        ]
        
        colors = []
        for i, stat in enumerate(expense_stats):
            labels.append(stat['name'])
            amounts.append(stat['amount'])
            colors.append(color_palette[i % len(color_palette)])
        
        # Вычисляем общую сумму
        total = sum(amounts) if amounts else 0
        
        # Функция для форматирования подписей на диаграмме
        def format_percent(pct, allvals):
            """Форматирует подписи на диаграмме с суммой и процентом."""
            # Вычисляем абсолютное значение для текущего процента
            absolute = pct / 100. * np.sum(allvals)
            
            # Если процент меньше 5, не показываем ничего
            if pct < 5:
                return ""
            
            # Форматируем сумму
            if absolute >= 1000000:
                amount_str = f"{absolute/1000000:.1f}М ₽"
            elif absolute >= 1000:
                amount_str = f"{absolute/1000:.0f}К ₽"
            else:
                amount_str = f"{absolute:,.0f} ₽"
            
            # Возвращаем процент и сумму
            return f"{pct:.1f}%\n{amount_str}"
        
        # Вычисляем проценты для каждого сегмента
        percentages = [(amount / total * 100) if total > 0 else 0 for amount in amounts]
        
        # Уменьшаем отступы вокруг диаграммы - УМЕНЬШИЛИ РАЗМЕР
        self.fig = Figure(figsize=(5.3, 4.5), dpi=80, facecolor='#f5f5f5')  # Уменьшили размер
        ax = self.fig.add_subplot(111)
        
        # Уменьшаем отступы вокруг subplot
        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        
        # Создаем круговую диаграмму
        wedges, texts, autotexts = ax.pie(
            amounts, 
            labels=None,
            colors=colors,
            autopct=lambda pct: format_percent(pct, amounts),
            startangle=90,
            wedgeprops={'edgecolor': 'white', 'linewidth': 1.2},  # Уменьшили толщину границы
            textprops={'fontsize': 6, 'fontweight': 'bold', 'color': 'black'},  # Шрифт 6 п.
            explode=[0.02] * len(amounts),
            pctdistance=0.75
        )
        
        # Улучшаем видимость текста на диаграмме - УМЕНЬШИЛИ ШРИФТ
        for autotext in autotexts:
            autotext.set_fontsize(7.5)  # Шрифт 6 п.
            autotext.set_fontweight('bold')
            autotext.set_color('black')
            # Уменьшили обводку
            autotext.set_path_effects([
                path_effects.withStroke(
                    linewidth=2,  # Уменьшили толщину обводки
                    foreground='white',
                    alpha=0.8
                )
            ])
        
        ax.axis('equal')
        
        # Создаем кастомные выноски с линиями
        self._create_custom_labels(ax, wedges, labels, amounts, colors, percentages)
        
        # Создаем канвас для отображения диаграммы
        self.canvas = FigureCanvasTkAgg(self.fig, self.chart_frame)
        self.canvas.draw()
        
        # Размещаем диаграмму с минимальными отступами
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Добавляем общую сумму в центр диаграммы - УМЕНЬШИЛИ ШРИФТ
        if total > 0:
            center_text = f"{total:,.0f} ₽"
            ax.text(0, 0, center_text, 
                   ha='center', va='center',
                   fontsize=11, fontweight='bold',  # Уменьшили шрифт
                   color='#2e7d32',
                   bbox=dict(boxstyle="round,pad=0.3",  # Уменьшили отступ
                            facecolor="white", 
                            edgecolor="#2e7d32",
                            alpha=0.9))
    
    def _create_custom_labels(self, ax, wedges, labels, amounts, colors, percentages):
        """Создает кастомные выноски с линиями."""
        from matplotlib.patches import ConnectionPatch
        
        # Уменьшаем расстояние для подписей
        label_distance_x = 1.25
        
        # Разделяем сегменты только на левые и правые
        left_segments = []
        right_segments = []
        
        for i, (wedge, percentage) in enumerate(zip(wedges, percentages)):
            theta1, theta2 = wedge.theta1, wedge.theta2
            angle = (theta1 + theta2) / 2
            
            # Нормализуем угол к [-180, 180) для удобства
            # matplotlib использует углы от -180 до 180
            angle_norm = angle % 360
            if angle_norm > 180:
                angle_norm -= 360  # Приводим к диапазону [-180, 180)
            
            # Правая сторона: от -90° до 90° (включая верх и низ справа)
            # Левая сторона: от 90° до 270° и от -90° до -180°
            is_right_side = -90 <= angle_norm <= 90
            
            segment_info = {
                'index': i,
                'wedge': wedge,
                'angle': angle,
                'percentage': percentage,
                'amount': amounts[i],
                'angle_norm': angle_norm,  # Теперь в диапазоне [-180, 180)
                'y_pos': np.sin(np.radians(angle))
            }
            
            if is_right_side:
                right_segments.append(segment_info)
            else:
                left_segments.append(segment_info)
        
        # Сортируем сегменты по вертикали (сверху вниз)
        right_segments.sort(key=lambda x: x['y_pos'], reverse=True)
        left_segments.sort(key=lambda x: x['y_pos'], reverse=True)
        
        # Обрабатываем обе стороны
        self._place_side_labels(ax, right_segments, labels, amounts, 
                               label_distance_x, side='right')
        self._place_side_labels(ax, left_segments, labels, amounts,
                               label_distance_x, side='left')
                               
    def _place_side_labels(self, ax, segments, labels, amounts, label_distance_x, side='right'):
        """Размещает подписи на указанной стороне."""
        from matplotlib.patches import ConnectionPatch
        
        if not segments:
            return
        
        # Вертикальное размещение для левых и правых подписей
        total_height = 2.1
        start_y = total_height / 2
        y_positions = np.linspace(start_y, -start_y, len(segments))
        
        for idx, (segment, y_pos) in enumerate(zip(segments, y_positions)):
            i = segment['index']
            wedge = segment['wedge']
            angle = segment['angle']
            percentage = segment['percentage']
            amount = segment['amount']
            
            segment_color = wedge.get_facecolor()
            name = labels[i]
            if len(name) > 15:
                name = name[:15] + "..."
            
            # Координаты точки на краю сегмента
            rad_angle = np.radians(angle)
            explode_distance = 0.02
            exploded_x = np.cos(rad_angle) * explode_distance
            exploded_y = np.sin(rad_angle) * explode_distance
            
            x = np.cos(rad_angle) * 1.0 + exploded_x
            y = np.sin(rad_angle) * 1.0 + exploded_y
            
            # Определяем координаты для текста
            if side == 'right':
                text_x = label_distance_x
                ha = 'left'
                line_end_x = label_distance_x - 0.2
            else:  # left
                text_x = -label_distance_x
                ha = 'right'
                line_end_x = -label_distance_x + 0.2
            
            text_y = y_pos
            line_end_y = y_pos
            va = 'center'
            
            line_color = self._darken_color(segment_color, 0.4)
            
            # Создаем линию
            con = ConnectionPatch(
                xyA=(x, y), 
                xyB=(line_end_x, line_end_y),
                coordsA="data", 
                coordsB="data",
                axesA=ax, 
                axesB=ax,
                color=line_color,
                linewidth=1.5 if percentage >= 5 else 1.2,
                alpha=0.85 if percentage >= 5 else 0.7,
                linestyle="-"
            )
            ax.add_artist(con)
            
            # Настройки для подписей как вы указали
            if percentage < 5:
                fontsize = 9
                bbox_pad = 0.18
                text_color = '#111111'
            else:
                fontsize = 9
                bbox_pad = 0.25
                text_color = '#000000'
            
            # Добавляем текст
            ax.text(text_x, text_y, name,
                   ha=ha, va=va,
                   fontsize=fontsize,
                   color=text_color,
                   bbox=dict(
                       boxstyle=f"round,pad={bbox_pad}",
                       facecolor="white",
                       edgecolor=line_color,
                       alpha=0.95,
                       linewidth=1.0
                   ))
                   
    def _darken_color(self, color, factor=0.3):
        """Затемняет цвет на указанный коэффициент."""
        import colorsys
        
        if isinstance(color, tuple) and len(color) >= 3:
            r, g, b = color[0], color[1], color[2]
        elif isinstance(color, str) and color.startswith('#'):
            color = color.lstrip('#')
            r = int(color[0:2], 16) / 255.0
            g = int(color[2:4], 16) / 255.0
            b = int(color[4:6], 16) / 255.0
        else:
            return '#555555'
        
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        v = max(0, v * (1 - factor))
        
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        
        return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))
    
    def destroy(self):
        """Корректное удаление виджета."""
        if self.fig:
            plt.close(self.fig)
        super().destroy()