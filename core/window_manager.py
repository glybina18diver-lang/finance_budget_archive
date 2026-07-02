# core/window_manager.py
import tkinter as tk
import importlib
import inspect
import sys
import os
from pathlib import Path
from typing import Dict, Type, Optional

class SmartWindowManager:
    """
    Умный менеджер окон с автоматическим обнаружением всех диалогов.
    Автоматически находит ВСЕ классы Toplevel в папке ui/dialogs/
    """
    
    def __init__(self, parent):
        self.parent = parent  # Главное окно BudgetApp
        self.open_windows: Dict[str, tk.Toplevel] = {}
        self.window_classes: Dict[str, Type[tk.Toplevel]] = {}
        
        # Автоматически находим все классы окон
        self._discover_window_classes()
        # print(f"DEBUG: Найдено {len(self.window_classes)} окон")
    
    def _discover_window_classes(self):
        """Автоматически находит все классы окон в папке ui/dialogs/"""
        # Путь к папке с диалогами
        dialogs_dir = Path(__file__).parent.parent / 'ui' / 'dialogs'
        
        if not dialogs_dir.exists():
            print(f"WARNING: Папка {dialogs_dir} не найдена")
            return
        
        # Добавляем путь для импорта
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Сканируем все Python файлы
        for file_path in dialogs_dir.glob('*.py'):
            if file_path.name == '__init__.py':
                continue
            
            # Имя модуля: ui.dialogs.filename
            module_name = f"ui.dialogs.{file_path.stem}"
            
            try:
                # Импортируем модуль
                module = importlib.import_module(module_name)
                
                # Ищем все классы Toplevel в модуле
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, tk.Toplevel) and 
                        obj != tk.Toplevel):
                        
                        # Генерируем ID окна
                        window_id = self._generate_window_id(name)
                        self.window_classes[window_id] = obj
                        
                        print(f"  ✓ {window_id} -> {name}")
                        
            except Exception as e:
                print(f"  ✗ Ошибка загрузки {module_name}: {e}")
                
        # Также ищем SimpleDashboard
        try:
            from ui.dashboard import SimpleDashboard
            self.window_classes['dashboard'] = SimpleDashboard
            print(f"  ✓ dashboard -> SimpleDashboard (Frame)")
        except ImportError as e:
            print(f"  ✗ Не удалось загрузить SimpleDashboard: {e}")
    
    @staticmethod
    def _generate_window_id(class_name: str) -> str:
        """Генерирует удобные ID для окон"""
        # Специальные случаи
        special_cases = {
            'AccountManagementDialog': 'accounts',
            'CategoryManagementDialog': 'categories', 
            'TransferDialog': 'transfer',
            'ReconciliationDialog': 'reconciliation',
            'DateRangeDialog': 'date_range',
            'CreditCardsWindow': 'credit_cards',
            'EditTransactionDialog': 'edit',
            'LoanManagementWindow': 'loans',
            'SimpleDashboard': 'dashboard'
        }
        
        if class_name in special_cases:
            return special_cases[class_name]
        
        # Общий случай: AccountManagementDialog -> accounts
        import re
        
        # Удаляем суффиксы
        name = class_name
        suffixes = ['Dialog', 'Window', 'Management']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break
        
        # Конвертируем в snake_case и делаем множественное число
        name = re.sub(r'([a-z])([A-Z])', r'\1_\2', name)
        name = name.lower()
        
        # Делаем множественное число для некоторых окон
        if name.endswith(('category', 'account')):
            name = name + 's'
        
        return name
    
    # В core/window_manager.py

    def open_window(self, window_id: str, *args, **kwargs) -> Optional[tk.Toplevel]:
        """
        Универсальный метод открытия окон.
        Поддерживает: Toplevel, Frame, модальные диалоги.
        
        Args:
            window_id: ID окна ('accounts', 'transfer', 'dashboard', etc.)
            *args, **kwargs: аргументы для конструктора окна
        
        Returns:
            Созданное или существующее окно, или None в случае ошибки
        """
        import tkinter as tk
        from tkinter import ttk
        
        # 1. Проверяем алиасы если есть
        if hasattr(self, 'aliases') and window_id in self.aliases:
            window_id = self.aliases[window_id]
        
        # 2. Проверяем, открыто ли уже окно
        if window_id in self.open_windows:
            win = self.open_windows[window_id]
            if win and win.winfo_exists():
                # Поднимаем существующее окно
                win.lift()
                win.focus_set()
                
                # Обновляем данные если есть такой метод
                self._refresh_window(win)
                
                # Для модальных окон - фокус и поднятие
                if getattr(win, '_is_modal', False):
                    win.grab_set()
                    
                return win
            else:
                # Окно было закрыто, удаляем из списка
                del self.open_windows[window_id]
        
        # 3. Находим класс окна
        if window_id not in self.window_classes:
            # Пробуем найти по частичному совпадению
            found = False
            for key, cls in self.window_classes.items():
                if window_id in key or key in window_id:
                    window_id = key
                    found = True
                    break
            
            if not found:
                print(f"ERROR: Окно '{window_id}' не найдено!")
                print(f"Доступные окна: {list(self.window_classes.keys())}")
                
                # Специальная обработка для common окон
                if window_id in ['dashboard', 'statistics', 'reports']:
                    print(f"NOTE: {window_id} должен наследовать от tk.Toplevel")
                
                return None
        
        window_class = self.window_classes[window_id]
        
        # 4. Определяем тип окна
        is_toplevel = issubclass(window_class, tk.Toplevel)
        is_frame = issubclass(window_class, (ttk.Frame, tk.Frame))
        
        # 5. Создаем окно в зависимости от типа
        try:
            if is_toplevel:
                # ---------- ОБЫЧНЫЕ TOPLEVEL ОКНА ----------
                window = window_class(self.parent, *args, **kwargs)
                self.open_windows[window_id] = window
                
                # Настраиваем обработчик закрытия
                def on_close():
                    if window_id in self.open_windows:
                        del self.open_windows[window_id]
                    if window.winfo_exists():
                        window.destroy()
                    # Освобождаем grab для модальных
                    if getattr(window, '_is_modal', False):
                        window.grab_release()
                
                window.protocol("WM_DELETE_WINDOW", on_close)
                
                # Центрируем
                self._center_window(window)
                
                # Для модальных окон
                if getattr(window, '_is_modal', False):
                    window.transient(self.parent)
                    window.grab_set()
                    # Ждем закрытия если нужно
                    if kwargs.get('wait', False):
                        self.parent.wait_window(window)
                
                return window
                
            elif is_frame:
                # ---------- FRAME ОКНА (как SimpleDashboard) ----------
                # Создаем Toplevel как контейнер
                container = tk.Toplevel(self.parent)
                
                # Устанавливаем заголовок из класса или window_id
                title = getattr(window_class, 'title', 
                        window_id.replace('_', ' ').title() + ' Dashboard')
                container.title(title)
                
                # Настройки размера
                container.geometry(kwargs.get('geometry', '900x600'))
                container.minsize(800, 500)
                
                # Создаем Frame внутри контейнера
                frame_instance = window_class(container, *args, **kwargs)
                frame_instance.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Сохраняем контейнер
                self.open_windows[window_id] = container
                
                # Сохраняем ссылку на Frame для обновления
                container._frame_instance = frame_instance
                
                # Настраиваем закрытие
                def on_close():
                    if window_id in self.open_windows:
                        del self.open_windows[window_id]
                    if container.winfo_exists():
                        container.destroy()
                
                container.protocol("WM_DELETE_WINDOW", on_close)
                
                # Центрируем
                self._center_window(container)
                
                return container
                
            else:
                print(f"ERROR: Неподдерживаемый тип окна {window_class}")
                return None
                
        except TypeError as e:
            # Частая ошибка - неправильные аргументы
            print(f"ERROR: Неправильные аргументы для {window_id}: {e}")
            print(f"Класс: {window_class.__name__}")
            print(f"Ожидаемые аргументы: {window_class.__init__.__code__.co_varnames[1:]}")
            return None
            
        except Exception as e:
            print(f"ERROR: Не удалось создать окно {window_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def open_window_by_class_name(self, class_name: str, *args, **kwargs):
        """Открывает окно по имени класса"""
        window_id = self._generate_window_id(class_name)
        return self.open_window(window_id, *args, **kwargs)
    
    def _refresh_window(self, window: tk.Toplevel):
        """Обновляет данные в окне если есть соответствующий метод"""
        refresh_methods = ['refresh', 'load_data', 'update_data', 'reload']
        for method_name in refresh_methods:
            if hasattr(window, method_name):
                try:
                    getattr(window, method_name)()
                    break
                except Exception as e:
                    print(f"DEBUG: Ошибка при обновлении окна: {e}")
    
    def _center_window(self, window: tk.Toplevel):
        """Центрирует окно относительно родителя"""
        try:
            window.update_idletasks()
            width = window.winfo_width()
            height = window.winfo_height()
            
            if hasattr(self.parent, 'winfo_width'):
                parent_x = self.parent.winfo_rootx()
                parent_y = self.parent.winfo_rooty()
                parent_width = self.parent.winfo_width()
                parent_height = self.parent.winfo_height()
                
                x = parent_x + (parent_width - width) // 2
                y = parent_y + (parent_height - height) // 2
                
                # Не выходим за пределы экрана
                screen_width = window.winfo_screenwidth()
                screen_height = window.winfo_screenheight()
                
                x = max(0, min(x, screen_width - width - 10))
                y = max(0, min(y, screen_height - height - 10))
                
                window.geometry(f"+{x}+{y}")
        except Exception as e:
            print(f"DEBUG: Ошибка центрирования окна: {e}")
    
    def _refresh_window(self, window):
        """Обновляет данные в окне если есть соответствующий метод"""
        refresh_methods = ['refresh', 'load_data', 'update_data', 'reload', 'refresh_data']
        
        # Для Frame окон сначала получаем Frame instance
        if hasattr(window, '_frame_instance'):
            window = window._frame_instance
        
        for method_name in refresh_methods:
            if hasattr(window, method_name):
                try:
                    method = getattr(window, method_name)
                    # Проверяем что это метод, а не атрибут
                    if callable(method):
                        method()
                        print(f"DEBUG: Вызван {method_name}() для окна")
                        break
                except Exception as e:
                    print(f"DEBUG: Ошибка при вызове {method_name}: {e}")
                    continue

    def open_modal_window(self, window_id: str, *args, **kwargs):
        """Открывает модальное окно (блокирует родительское)"""
        kwargs['wait'] = True
        window = self.open_window(window_id, *args, **kwargs)
        
        if window:
            # Помечаем как модальное
            window._is_modal = True
            # Ждем закрытия
            self.parent.wait_window(window)
            
            # Возвращаем результат если есть
            if hasattr(window, 'result'):
                return window.result
            elif hasattr(window, 'get_result'):
                return window.get_result()
        
        return None

    def open_frame_as_window(self, frame_class, window_id: str, title: str = None, 
                            geometry: str = "800x600", *args, **kwargs):
        """Специальный метод для открытия Frame как окна"""
        import tkinter as tk
        
        # Добавляем в window_classes если еще нет
        if window_id not in self.window_classes:
            self.window_classes[window_id] = frame_class
        
        # Создаем контейнер
        container = tk.Toplevel(self.parent)
        container.title(title or frame_class.__name__)
        container.geometry(geometry)
        
        # Создаем Frame с правильными аргументами
        try:
            # Пробуем создать с позиционными аргументами
            frame = frame_class(container, *args)
        except TypeError:
            # Если не получилось, пробуем с keyword arguments
            frame = frame_class(container, **kwargs)
        
        frame.pack(fill="both", expand=True)
        
        # Сохраняем
        self.open_windows[window_id] = container
        container._frame_instance = frame
        
        def on_close():
            if window_id in self.open_windows:
                del self.open_windows[window_id]
            container.destroy()
        
        container.protocol("WM_DELETE_WINDOW", on_close)
        self._center_window(container)
        
        return container
    
    def close_window(self, window_id: str):
        """Закрывает окно по ID"""
        if window_id in self.open_windows:
            window = self.open_windows[window_id]
            if window and window.winfo_exists():
                window.destroy()
            del self.open_windows[window_id]
    
    def close_all(self):
        """Закрывает все открытые окна"""
        for window_id in list(self.open_windows.keys()):
            self.close_window(window_id)
    
    def get_open_windows(self) -> Dict[str, tk.Toplevel]:
        """Возвращает все открытые окна"""
        return self.open_windows.copy()
    
    def is_open(self, window_id: str) -> bool:
        """Проверяет открыто ли окно"""
        if window_id in self.open_windows:
            window = self.open_windows[window_id]
            return window and window.winfo_exists()
        return False
        