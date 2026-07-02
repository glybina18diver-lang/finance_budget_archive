# ui/dialogs/operations_dialog.py - Диалог для операций и таблицы транзакций
import tkinter as tk
from tkinter import ttk
from datetime import date, datetime, timedelta
from tkinter import messagebox
import os

from core.database import DatabaseManager
from ui.widgets.calendar_widgets import TtkDateEntry
from ui.dialogs.edit_transaction_dialog import EditTransactionDialog
from ui.dialogs.date_range_dialog import DateRangeDialog
from ui.widgets.window_utils import center_window_relative


class OperationsDialog(tk.Toplevel):
    def __init__(self, parent, db, accounts_data=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.title("Операции и транзакции")
        self.geometry("1200x600")
        
        # Предотвращаем дублирование событий
        self._processing_shortcut = False
        
        self.accounts_data = accounts_data or {}
        self.categories_by_name = {}
        self.categories_income = {}
        self.categories_expense = {}
        self.current_filters = {
            "date_from": None, "date_to": None, "trans_type": None, 
            "category_id": None, "account_id": None, "description_text": None
        }
        self.header_menus = {}
        self.last_selected_date = date.today().strftime('%Y-%m-%d')
        self.category_id_by_display_name = {}
        
        self._init_ui()
        self._load_all_data()
        self._update_display()
        self._setup_keyboard_shortcuts()
        
    def _setup_keyboard_shortcuts(self):
        """Настройка горячих клавиш - финальная версия."""
        # Очищаем все старые биндинги
        for event in ['<Control-v>', '<Control-V>', '<Control-c>', '<Control-C>', 
                     '<Control-x>', '<Control-X>', '<Control-a>', '<Control-A>',
                     '<Key>', '<Control-Key>']:
            self.unbind(event)
        
        # Биндим только на низком уровне с prevent_default
        self.bind('<Control-KeyPress>', self._on_control_keypress, add='+')
        self.bind('<Key>', self._on_key, add='+')
        
        # Enter и Tab - отдельно
        self.bind('<Return>', self._on_return, add='+')
        self.bind('<Tab>', self._on_tab, add='+')
        self.bind('<Shift-Tab>', self._on_shift_tab, add='+')
        self.bind('<Delete>', self._on_delete, add='+')
        
        # Дополнительно биндим на все виджеты ввода
        for widget in [self.amount_input, self.description_input]:
            widget.bind('<Control-KeyPress>', self._on_control_keypress, add='+')
            widget.bind('<Key>', self._on_key, add='+')
        
    def _on_control_keypress(self, event):
        """Обработка Control+клавиша - ГЛАВНЫЙ ОБРАБОТЧИК."""
        # Проверяем состояние Control
        if not (event.state & 0x0004):  # Control не нажат
            return None
        
        # Получаем символ в нижнем регистре
        char = event.char.lower() if event.char else ''
        keysym = event.keysym.lower()
        
        # Отладочная информация
        # print(f"Control pressed: char='{char}', keysym='{keysym}', keycode={event.keycode}")
        
        # Обрабатываем по keycode (надежнее)
        keycode = event.keycode
        
        # Маппинг keycode на действия
        # V (86) и М (русская, обычно 1062 или 86 с другой раскладкой)
        if keycode == 86 or (char and char in 'vм'):  # V или М
            self._safe_paste()
            return 'break'
        
        # C (67) и С (русская)
        elif keycode == 67 or (char and char in 'cс'):  # C или С
            self._safe_copy()
            return 'break'
        
        # X (88) и Ч (русская)
        elif keycode == 88 or (char and char in 'xч'):  # X или Ч
            self._safe_cut()
            return 'break'
        
        # A (65) и Ф (русская)
        elif keycode == 65 or (char and char in 'aф'):  # A или Ф
            self._safe_select_all()
            return 'break'
        
        return None
    
    def _on_key(self, event):
        """Обработка одиночных клавиш."""
        # Enter уже обработан в _on_return
        if event.keysym == 'Return':
            return None
            
        return None
    
    def _on_return(self, event):
        """Обработка Enter."""
        focused = self.focus_get()
        
        # Если фокус в поле описания - добавляем операцию
        if focused == self.description_input:
            self._add_transaction()
            return 'break'
        
        # Если фокус в других полях ввода - переходим к следующему
        elif focused in [self.amount_input, self.date_input]:
            self._navigate_next_widget(None)
            return 'break'
        
        return None
    
    def _on_tab(self, event):
        """Обработка Tab."""
        self._navigate_next_widget(None)
        return 'break'
    
    def _on_shift_tab(self, event):
        """Обработка Shift+Tab."""
        self._navigate_prev_widget(None)
        return 'break'
    
    def _on_delete(self, event):
        """Обработка Delete."""
        focused = self.focus_get()
        
        if focused == self.transactions_tree:
            self._delete_selected_transactions()
            return 'break'
        
        return None
    
    def _navigate_next_widget(self, event):
        """Переход к следующему виджету."""
        widgets = [
            self.date_input,
            self.amount_input,
            self.type_combo,
            self.category_combo,
            self.account_combo,
            self.description_input
        ]
        
        focused = self.focus_get()
        if focused in widgets:
            idx = widgets.index(focused)
            next_idx = (idx + 1) % len(widgets)
            widgets[next_idx].focus_set()
        
        return 'break' if event else None
    
    def _navigate_prev_widget(self, event):
        """Переход к предыдущему виджету."""
        widgets = [
            self.date_input,
            self.amount_input,
            self.type_combo,
            self.category_combo,
            self.account_combo,
            self.description_input
        ]
        
        focused = self.focus_get()
        if focused in widgets:
            idx = widgets.index(focused)
            prev_idx = (idx - 1) % len(widgets)
            widgets[prev_idx].focus_set()
        
        return 'break' if event else None
    
    def _safe_paste(self):
        """Безопасная вставка без дублирования."""
        if self._processing_shortcut:
            return
            
        self._processing_shortcut = True
        try:
            focused = self.focus_get()
            
            if focused in [self.amount_input, self.description_input]:
                try:
                    clipboard_text = self.clipboard_get()
                except tk.TclError:
                    clipboard_text = ""
                
                if clipboard_text:
                    # Для поля суммы обрабатываем placeholder
                    if focused == self.amount_input:
                        if self.amount_input.get() == "Сумма":
                            self.amount_input.delete(0, tk.END)
                            self.amount_input.config(foreground="black")
                    
                    # Удаляем выделенный текст, если есть
                    try:
                        if focused.selection_present():
                            focused.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    except tk.TclError:
                        pass
                    
                    # Вставляем в текущую позицию
                    try:
                        current_pos = focused.index(tk.INSERT)
                        focused.insert(current_pos, clipboard_text)
                    except tk.TclError:
                        # Запасной вариант - вставляем в конец
                        focused.insert(tk.END, clipboard_text)
                        
                    self.show_status_message("Текст вставлен", 1000)
        finally:
            self._processing_shortcut = False
    
    def _safe_copy(self):
        """Безопасное копирование."""
        if self._processing_shortcut:
            return
            
        self._processing_shortcut = True
        try:
            focused = self.focus_get()
            
            if focused in [self.amount_input, self.description_input]:
                try:
                    if focused.selection_present():
                        selected_text = focused.selection_get()
                        self.clipboard_clear()
                        self.clipboard_append(selected_text)
                        self.show_status_message("Текст скопирован", 1000)
                except tk.TclError:
                    pass
        finally:
            self._processing_shortcut = False
    
    def _safe_cut(self):
        """Безопасное вырезание."""
        if self._processing_shortcut:
            return
            
        self._processing_shortcut = True
        try:
            focused = self.focus_get()
            
            if focused in [self.amount_input, self.description_input]:
                try:
                    if focused.selection_present():
                        selected_text = focused.selection_get()
                        self.clipboard_clear()
                        self.clipboard_append(selected_text)
                        focused.delete(tk.SEL_FIRST, tk.SEL_LAST)
                        self.show_status_message("Текст вырезан", 1000)
                except tk.TclError:
                    pass
        finally:
            self._processing_shortcut = False
    
    def _safe_select_all(self):
        """Безопасное выделение всего текста."""
        if self._processing_shortcut:
            return
            
        self._processing_shortcut = True
        try:
            focused = self.focus_get()
            
            if focused in [self.amount_input, self.description_input]:
                focused.select_range(0, tk.END)
                focused.icursor(tk.END)
                self.show_status_message("Весь текст выделен", 1000)
        finally:
            self._processing_shortcut = False
    
    def _init_ui(self):
        """Инициализация интерфейса диалога операций."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- Панель дополнительных операций ---
        operations_panel = ttk.Frame(main_frame)
        operations_panel.pack(fill="x", pady=(0, 10))
        
        ttk.Button(operations_panel, text="Управление счетами", 
                  command=self._open_account_management).pack(side="left", padx=5)
        
        ttk.Button(operations_panel, text="Управление категориями", 
                  command=self._open_category_management).pack(side="left", padx=5)        
        
        ttk.Button(operations_panel, text="📤 Переводы", 
                  command=self._open_transfer_dialog).pack(side="left", padx=5)
        
        ttk.Button(operations_panel, text="🔍 Сверка баланса", 
                  command=self._open_reconciliation_dialog).pack(side="left", padx=5)
        
        ttk.Button(operations_panel, text="💰 Управление займами", 
                  command=self._open_loan_management).pack(side="left", padx=5)
        
        ttk.Button(operations_panel, text="💳 Кредитные карты", 
                  command=self._open_credit_cards).pack(side="left", padx=5)
               
        # --- Форма ввода транзакции ---
        self.input_form_frame = ttk.LabelFrame(main_frame, text="Новая операция")
        self.input_form_frame.pack(fill="x", pady=(0, 10))
        
        input_grid = ttk.Frame(self.input_form_frame)
        input_grid.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(input_grid, text="Дата:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.date_input = TtkDateEntry(input_grid)
        self.date_input.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        
        ttk.Label(input_grid, text="Сумма:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.amount_input = tk.Entry(input_grid)
        self.amount_input.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        self.amount_input.insert(0, "Сумма")
        self.amount_input.config(foreground="grey")
        
        def on_amount_focusin(event):
            if self.amount_input.get() == "Сумма":
                self.amount_input.delete(0, tk.END)
                self.amount_input.config(foreground="black")
        
        def on_amount_focusout(event):
            if not self.amount_input.get():
                self.amount_input.insert(0, "Сумма")
                self.amount_input.config(foreground="grey")
        
        self.amount_input.bind("<FocusIn>", on_amount_focusin)
        self.amount_input.bind("<FocusOut>", on_amount_focusout)

        ttk.Label(input_grid, text="Тип:").grid(row=0, column=4, padx=5, pady=2, sticky="w")
        self.type_combo_var = tk.StringVar(self)
        self.type_combo = ttk.Combobox(input_grid, textvariable=self.type_combo_var, values=["Расход", "Доход"], state="readonly")
        self.type_combo.set("Расход")
        self.type_combo.bind("<<ComboboxSelected>>", self._update_category_and_account_combos)
        self.type_combo.grid(row=0, column=5, padx=5, pady=2, sticky="ew")

        ttk.Label(input_grid, text="Категория:").grid(row=0, column=6, padx=5, pady=2, sticky="w")
        self.category_combo_var = tk.StringVar(self)
        self.category_combo = ttk.Combobox(input_grid, textvariable=self.category_combo_var, state="readonly")
        self.category_combo.grid(row=0, column=7, padx=5, pady=2, sticky="ew")
        
        ttk.Label(input_grid, text="Счет:").grid(row=0, column=8, padx=5, pady=2, sticky="w")
        self.account_combo_var = tk.StringVar(self)
        self.account_combo = ttk.Combobox(input_grid, textvariable=self.account_combo_var, state="readonly")
        self.account_combo.grid(row=0, column=9, padx=5, pady=2, sticky="ew")

        ttk.Label(input_grid, text="Описание:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.description_input = tk.Entry(input_grid)
        self.description_input.grid(row=1, column=1, columnspan=8, padx=5, pady=2, sticky="ew")

        add_button = ttk.Button(input_grid, text="Добавить", command=self._add_transaction)
        add_button.grid(row=1, column=9, padx=5, pady=2, sticky="ew")

        input_grid.grid_columnconfigure(1, weight=1) 
        input_grid.grid_columnconfigure(3, weight=1) 
        input_grid.grid_columnconfigure(5, weight=1) 
        input_grid.grid_columnconfigure(7, weight=1) 
        input_grid.grid_columnconfigure(9, weight=1) 
        input_grid.grid_columnconfigure(1, weight=3) 

        # --- Таблица транзакций ---
        transactions_frame = ttk.Frame(main_frame)
        transactions_frame.pack(fill="both", expand=True, pady=5)

        self.transactions_tree = ttk.Treeview(
                transactions_frame, 
                columns=("Дата", "Тип", "Сумма", "quantity", "Категория", "Счет", "Описание"), 
                show="headings",
                height=15
            )        
        self.transactions_tree.heading("Дата", text="Дата")
        self.transactions_tree.heading("Тип", text="Тип")
        self.transactions_tree.heading("Сумма", text="Сумма")
        self.transactions_tree.heading("quantity", text="Кол-во")
        self.transactions_tree.heading("Категория", text="Категория")
        self.transactions_tree.heading("Счет", text="Счет")
        self.transactions_tree.heading("Описание", text="Описание")

        self.transactions_tree.column("Дата", width=100)
        self.transactions_tree.column("Тип", width=80)
        self.transactions_tree.column("Сумма", width=100, anchor="e")
        self.transactions_tree.column("quantity", width=60, anchor="center")
        self.transactions_tree.column("Категория", width=120)
        self.transactions_tree.column("Счет", width=120)
        self.transactions_tree.column("Описание", width=200, stretch=tk.YES)
        
        self.transactions_tree.pack(side="left", fill="both", expand=True)

        yscrollbar = ttk.Scrollbar(transactions_frame, orient="vertical", command=self.transactions_tree.yview)
        yscrollbar.pack(side="right", fill="y")
        self.transactions_tree.config(yscrollcommand=yscrollbar.set)
        
        self.transactions_tree.config(selectmode="extended")
        
        self.setup_treeview_management(
            self,
            self.transactions_tree,
            self._delete_selected_transactions,
            additional_commands=[
                ("📋 Копировать", self._copy_transaction),
                ("✏️ Редактировать", self._edit_transaction),
                ("🔍 Детали", self._show_transaction_details)
            ]
        )
        
        self._create_filter_menus()
        
        # Кнопки управления
        management_buttons_frame = ttk.Frame(main_frame)
        management_buttons_frame.pack(fill="x", pady=10)

        reset_all_filters_btn = ttk.Button(management_buttons_frame, text="Сбросить все фильтры", 
                                          command=self._reset_all_filters)
        reset_all_filters_btn.pack(side="right", padx=10)

        close_button = ttk.Button(management_buttons_frame, text="Закрыть", 
                                 command=self.destroy)
        close_button.pack(side="right", padx=10)
        
        # Строка статуса
        self.status_bar = ttk.Label(self, text="Готово.", relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(side="bottom", fill="x")
    
      
    def _load_all_data(self):
        """Загружает все данные из БД."""
        self.accounts_data = {acc[0]: {"name": acc[1], "type": acc[2], "balance": acc[4]} 
                             for acc in self.db.get_accounts()}
        
        all_categories = self.db.get_categories(include_subcategories=True)
        
        self.all_categories_data = {cat[0]: cat for cat in all_categories}
        self.categories_by_name = {cat[1]: cat[0] for cat in all_categories}
        
        self.categories_income = {
            cat[0]: cat[1] for cat in self.db.get_categories(type='income', include_subcategories=True)
        }
        self.categories_expense = {
            cat[0]: cat[1] for cat in self.db.get_categories(type='expense', include_subcategories=True)
        }
        
        self._update_category_and_account_combos()
        self._update_filter_menus_content()
    
    def _update_category_and_account_combos(self, event=None):
        """Обновляет списки категорий с учетом иерархии."""
        current_type = self.type_combo_var.get()
        current_category = self.category_combo_var.get()
        current_account = self.account_combo_var.get()

        if current_type == "Доход":
            categories = self.db.get_categories_with_hierarchy(type_filter='income')
        elif current_type == "Расход":
            categories = self.db.get_categories_with_hierarchy(type_filter='expense')
        else:
            categories = self.db.get_categories_with_hierarchy()
        
        display_names = []
        self.category_id_by_display_name = {}
        
        for cat_id, name, cat_type, budget, parent_id, level, path in categories:
            if level == 0:
                display_name = name
            else:
                indent = "    " * level
                display_name = f"{indent}{name}"
            
            display_names.append(display_name)
            self.category_id_by_display_name[display_name] = cat_id
        
        self.category_combo['values'] = display_names
        
        if current_category in display_names:
            self.category_combo_var.set(current_category)
        elif display_names:
            clean_current = current_category.strip() if current_category else ""
            for display_name in display_names:
                if display_name.strip() == clean_current:
                    self.category_combo_var.set(display_name)
                    break
            else:
                self.category_combo_var.set(display_names[0])
        else:
            self.category_combo_var.set("")
        
        account_names = [acc_info['name'] for acc_info in self.accounts_data.values()]
        self.account_combo['values'] = account_names
        
        if current_account in account_names:
            self.account_combo_var.set(current_account)
        elif account_names:
            self.account_combo_var.set(account_names[0])
        else:
            self.account_combo_var.set("")
        
        if current_type in ["Доход", "Расход"]:
            self.type_combo_var.set(current_type)
        else:
            self.type_combo_var.set("Расход")
    
    def _add_transaction(self):
        """Добавляет новую транзакцию."""
        date_str = self.date_input.get_date()
        self.last_selected_date = date_str
        
        amount_str = self.amount_input.get().strip()
        if amount_str == "Сумма" or not amount_str:
            messagebox.showwarning("Ошибка ввода", "Пожалуйста, введите сумму.", parent=self)
            return
        
        amount_str = amount_str.replace(',', '.')
        
        quantity = 1.0
        price_per_unit = None
        
        if '*' in amount_str:
            try:
                parts = amount_str.split('*')
                if len(parts) == 2:
                    price_per_unit = float(parts[0].strip())
                    quantity = float(parts[1].strip())
                    total_amount = price_per_unit * quantity
                    
                    if quantity <= 0:
                        messagebox.showwarning("Ошибка ввода", "Количество должно быть положительным.", parent=self)
                        return
                        
                    if not self.description_input.get().strip():
                        self.description_input.insert(0, f"({quantity} ед.)")
                else:
                    total_amount = float(amount_str)
            except ValueError as e:
                messagebox.showwarning("Ошибка ввода", f"Некорректный формат суммы: {e}", parent=self)
                return
        else:
            try:
                total_amount = float(amount_str)
            except ValueError as e:
                messagebox.showwarning("Ошибка ввода", f"Некорректная сумма: {e}", parent=self)
                return
        
        transaction_type_text = self.type_combo_var.get().lower()
        category_display_name = self.category_combo_var.get()     
        account_name = self.account_combo_var.get()       
        description = self.description_input.get().strip()

        if not category_display_name or category_display_name == "Сумма":
            messagebox.showwarning("Ошибка ввода", "Пожалуйста, выберите категорию.", parent=self)
            return
        
        category_name = category_display_name.strip()
        category_id = self.category_id_by_display_name.get(category_display_name)
        
        if category_id is None:
            for cat in self.db.get_categories():
                if cat[1] == category_name:
                    category_id = cat[0]
                    break
        
        if category_id is None:
            messagebox.showwarning("Ошибка ввода", "Пожалуйста, выберите категорию.", parent=self)
            return
        
        account_id = next((acc_id for acc_id, info in self.accounts_data.items() if info['name'] == account_name), None)
        
        need_confirmation = False
        confirmation_message = ""
        
        if transaction_type_text == "расход" and total_amount < 0:
            need_confirmation = True
            abs_amount = abs(total_amount)
            confirmation_message = (f"Вы добавляете ВОЗВРАТ покупки: {abs_amount:.2f} ₽\n"
                                   f"Баланс счета УВЕЛИЧИТСЯ на эту сумму.\n\n"
                                   f"Продолжить?")
        
        elif transaction_type_text == "доход" and total_amount < 0:
            need_confirmation = True
            abs_amount = abs(total_amount)
            confirmation_message = (f"Вы добавляете УБЫТОК: {abs_amount:.2f} ₽\n"
                                   f"Баланс счета ВСЕ РАВНО УВЕЛИЧИТСЯ на эту сумму.\n\n"
                                   f"Продолжить?")
        
        if need_confirmation:
            if not messagebox.askyesno("Подтверждение операции", confirmation_message, parent=self):
                return
        
        if self.db.add_transaction(date_str, total_amount, transaction_type_text, 
                                   category_id, description, account_id, quantity):
            
            abs_amount = abs(total_amount)
            
            if transaction_type_text == "расход":
                if total_amount > 0:
                    if quantity != 1.0:
                        success_msg = f"✅ Расход добавлен: {abs_amount:.2f} ₽ ({quantity} ед.)"
                    else:
                        success_msg = f"✅ Расход добавлен: {abs_amount:.2f} ₽"
                else:
                    if quantity != 1.0:
                        success_msg = f"✅ Возврат покупки: {abs_amount:.2f} ₽ ({quantity} ед.)"
                    else:
                        success_msg = f"✅ Возврат покупки: {abs_amount:.2f} ₽"
                        
            elif transaction_type_text == "доход":
                if total_amount > 0:
                    if quantity != 1.0:
                        success_msg = f"✅ Доход добавлен: {abs_amount:.2f} ₽ ({quantity} ед.)"
                    else:
                        success_msg = f"✅ Доход добавлен: {abs_amount:.2f} ₽"
                else:
                    if quantity != 1.0:
                        success_msg = f"✅ Убыток учтен: {abs_amount:.2f} ₽ ({quantity} ед.)"
                    else:
                        success_msg = f"✅ Убыток учтен: {abs_amount:.2f} ₽"
                        
            else:
                if total_amount > 0:
                    if quantity != 1.0:
                        success_msg = f"✅ Корректировка: +{abs_amount:.2f} ₽ ({quantity} ед.)"
                    else:
                        success_msg = f"✅ Корректировка: +{abs_amount:.2f} ₽"
                else:
                    if quantity != 1.0:
                        success_msg = f"✅ Корректировка: -{abs_amount:.2f} ₽ ({quantity} ед.)"
                    else:
                        success_msg = f"✅ Корректировка: -{abs_amount:.2f} ₽"
            
            self.show_status_message(success_msg, 3000)
            
            self._load_all_data()
            self._update_display()
            self._clear_input_fields()
            
            # Автоматически фокусируемся на поле суммы после добавления
            self.amount_input.focus_set()
            self.amount_input.select_range(0, tk.END)
            
            # Обновляем родительское окно
            if hasattr(self.parent, '_post_dialog_update'):
                self.parent._post_dialog_update()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить операцию.", parent=self)
    
    def _clear_input_fields(self):
        """Очищает поля ввода суммы и описания с учетом placeholder."""
        self.amount_input.delete(0, tk.END)
        self.amount_input.insert(0, "Сумма")
        self.amount_input.config(foreground="grey")
        
        self.description_input.delete(0, tk.END)
    
    def _update_display(self):
        """Обновляет все элементы отображения."""
        self._update_transactions_tree(**self.current_filters)
    
    def _update_transactions_tree(self, date_from=None, date_to=None, trans_type=None, 
                                  category_id=None, account_id=None, description_text=None):
        """Обновляет таблицу транзакций с учетом фильтров."""
        for i in self.transactions_tree.get_children():
            self.transactions_tree.delete(i)
        
        all_transactions = self.db.get_transactions(
            date_from=date_from, date_to=date_to, trans_type=trans_type,
            category_id=category_id, account_id=account_id, description_text=description_text
        )
        
        if all_transactions:
            for t in all_transactions:
                t_id, date, amount, t_type, category_name, description, account_name, account_id_db, quantity = t
                
                if quantity == int(quantity):
                    qty_display = f"{int(quantity)} ед"
                else:
                    qty_display = f"{quantity:.1f} ед"
                
                self.transactions_tree.insert("", "end", iid=t_id, 
                                            values=(date,
                                                    t_type.capitalize(),
                                                    f"{amount:.2f} ₽",
                                                    qty_display,
                                                    category_name if category_name else "Без категории",
                                                    account_name,
                                                    description))
        else:
            has_filters = any([date_from, date_to, trans_type, category_id, account_id, description_text])
            
            if has_filters:
                filter_info = []
                
                if category_id:
                    category_name = "Неизвестная категория"
                    for cat in self.db.get_categories():
                        if cat[0] == category_id:
                            category_name = cat[1]
                            break
                    filter_info.append(f"'{category_name}'")
                
                if trans_type:
                    type_name = "Доход" if trans_type == "income" else "Расход"
                    filter_info.append(f"тип: {type_name}")
                
                if date_from or date_to:
                    date_str = ""
                    if date_from:
                        date_str += f"от {date_from} "
                    if date_to:
                        date_str += f"до {date_to}"
                    filter_info.append(f"дата: {date_str.strip()}")
                
                if category_id and len(filter_info) == 1:
                    message = f"📭 В категории {filter_info[0]} пока нет транзакций"
                else:
                    filters_text = ", ".join(filter_info)
                    message = f"📭 По выбранным фильтрам ({filters_text}) транзакций не найдено"
                
                self.transactions_tree.insert("", "end", 
                                            values=("", "", "", "", message, "", ""),
                                            tags=("info",))
                
                self.transactions_tree.tag_configure("info", foreground="gray", font=("TkDefaultFont", 9, "italic"))
    
    # --- Методы для фильтрации транзакций ---
    def _create_filter_menus(self):
        """Создает контекстные меню для заголовков столбцов Treeview."""
        self.header_menus = {}
        
        columns = self.transactions_tree["columns"]
        
        filterable_columns_map = {
            "Тип": self._show_type_filter_menu,
            "Категория": self._show_category_filter_menu,
            "Счет": self._show_account_filter_menu,
            "Дата": self._show_date_filter_menu
        }

        for col_name in columns:
            if col_name in filterable_columns_map:
                menu = tk.Menu(self, tearoff=0)
                self.header_menus[col_name] = menu
                self.transactions_tree.heading(col_name, command=filterable_columns_map[col_name])

    def _update_filter_menus_content(self):
        """Обновляет содержимое выпадающих меню фильтров."""
        if "Тип" in self.header_menus:
            menu = self.header_menus["Тип"]
            menu.delete(0, tk.END)
            menu.add_command(label="Все", command=lambda: self._apply_column_filter("Тип", None))
            menu.add_separator()
            menu.add_command(label="Доход", command=lambda: self._apply_column_filter("Тип", "Доход"))
            menu.add_command(label="Расход", command=lambda: self._apply_column_filter("Тип", "Расход"))

        if "Категория" in self.header_menus:
            menu = self.header_menus["Категория"]
            menu.delete(0, tk.END)
            menu.add_command(label="Все", command=lambda: self._apply_column_filter("Категория", None))
            menu.add_separator()
            
            all_categories = self.db.get_categories_with_hierarchy()
            
            for cat_id, name, cat_type, budget, parent_id, level, path in all_categories:
                display_name = "    " * level + name
                menu.add_command(label=display_name, 
                               command=lambda n=name: self._apply_column_filter("Категория", n))

        if "Счет" in self.header_menus:
            menu = self.header_menus["Счет"]
            menu.delete(0, tk.END)
            menu.add_command(label="Все", command=lambda: self._apply_column_filter("Счет", None))
            menu.add_separator()
            account_names = sorted([acc_info['name'] for acc_id, acc_info in self.accounts_data.items()])
            for name in account_names:
                menu.add_command(label=name, command=lambda n=name: self._apply_column_filter("Счет", n))
                
        if "Дата" in self.header_menus:
            menu = self.header_menus["Дата"]
            menu.delete(0, tk.END)
            today = date.today()
            this_month_start = today.replace(day=1)
            this_year_start = today.replace(month=1, day=1)
            
            menu.add_command(label="Все", command=lambda: self._apply_column_filter("Дата", None, None))
            menu.add_separator()
            menu.add_command(label="Сегодня", command=lambda: self._apply_column_filter("Дата", today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
            menu.add_command(label="Последние 7 дней", command=lambda: self._apply_column_filter("Дата", (today - timedelta(days=7)).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
            menu.add_command(label="Этот месяц", command=lambda: self._apply_column_filter("Дата", this_month_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
            menu.add_command(label="Этот год", command=lambda: self._apply_column_filter("Дата", this_year_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
            menu.add_separator()
            menu.add_command(label="Выбрать диапазон...", command=self._open_date_range_dialog)

    def _show_type_filter_menu(self):
        if "Тип" in self.header_menus:
            self.header_menus["Тип"].post(self.transactions_tree.winfo_pointerx(), self.transactions_tree.winfo_pointery())

    def _show_category_filter_menu(self):
        if "Категория" in self.header_menus:
            self.header_menus["Категория"].post(self.transactions_tree.winfo_pointerx(), self.transactions_tree.winfo_pointery())

    def _show_account_filter_menu(self):
        if "Счет" in self.header_menus:
            self.header_menus["Счет"].post(self.transactions_tree.winfo_pointerx(), self.transactions_tree.winfo_pointery())
        
    def _show_date_filter_menu(self):
        if "Дата" in self.header_menus:
            self.header_menus["Дата"].post(self.transactions_tree.winfo_pointerx(), self.transactions_tree.winfo_pointery())

    def _open_date_range_dialog(self):
        """Модальный диалог - особая логика"""
        from ui.dialogs.date_range_dialog import DateRangeDialog
        dialog = DateRangeDialog(self.parent)
        dialog.wait_window()  # Ждем закрытия
        
        if hasattr(dialog, 'result') and dialog.result:
            date_from, date_to = dialog.result
            self._apply_column_filter("Дата", date_from, date_to)

    def _apply_column_filter(self, column_name, value, date_to_value=None):
        """Применяет фильтр для конкретного столбца."""
        if column_name == "Тип":
            self.current_filters["trans_type"] = value.lower() if value else None
        elif column_name == "Категория":
            clean_category_name = value.strip() if value else None
            
            all_categories = self.db.get_categories(include_subcategories=True)
            
            category_id_from_name = None
            if clean_category_name:
                for cat_id, cat_name, cat_type, budget, parent_id in all_categories:
                    if cat_name == clean_category_name:
                        category_id_from_name = cat_id
                        break
            
            self.current_filters["category_id"] = category_id_from_name
            
        elif column_name == "Счет":
            account_id_from_name = next(
                (acc_id for acc_id, info in self.accounts_data.items() 
                 if info['name'] == value), 
                None
            ) if value else None
            self.current_filters["account_id"] = account_id_from_name
        elif column_name == "Дата":
            self.current_filters["date_from"] = value
            self.current_filters["date_to"] = date_to_value
        
        self._update_transactions_tree(**self.current_filters)
        if value:
            self.show_status_message(
                f"🔍 Фильтр: {column_name} = '{value}'", 
                message_type="info",
                duration_ms=2000
            )
        else:
            self.show_status_message("🔍 Фильтр сброшен", message_type="info", duration_ms=1500)
        
        return
        
    def _reset_all_filters(self):
        """Сбрасывает все примененные фильтры."""
        self.current_filters = {
            "date_from": None, "date_to": None, "trans_type": None, 
            "category_id": None, "account_id": None, "description_text": None
        }
        self._update_transactions_tree(**self.current_filters)
        self.show_status_message("Все фильтры сброшены.", 1500)
    
    # --- Управление транзакциями ---
    def _delete_selected_transactions(self):
        """Удаляет выбранные транзакции."""
        self.delete_selected_items_universal(
            treeview=self.transactions_tree,
            item_type="операции",
            delete_callback=lambda transaction_id: self.db.delete_transaction(transaction_id),
            refresh_callback=self._update_display
        )
    
    def _edit_transaction(self):
        """Редактирование транзакции - особая логика"""
        selected_items = self.transactions_tree.selection()
        if not selected_items:
            messagebox.showinfo("Редактирование", "Выберите транзакцию", parent=self)
            return
        
        transaction_id = int(selected_items[0])
        transaction_data = self._get_transaction_by_id(transaction_id)
        
        if transaction_data:
            # Открываем с данными
            from ui.dialogs.edit_transaction_dialog import EditTransactionDialog
            EditTransactionDialog(self.parent, self.db, transaction_data)
    
    def _get_transaction_by_id(self, transaction_id):
        """Получает полные данные транзакции по ID."""
        transactions = self.db.get_transactions()
        for trans in transactions:
            if trans[0] == transaction_id:
                return trans
        return None
    
    def _copy_transaction(self):
        """Создает копию выбранной транзакции."""
        selected_items = self.transactions_tree.selection()
        if not selected_items:
            messagebox.showinfo("Копирование", "Выберите транзакцию для копирования.", parent=self)
            return
        
        transaction_id = int(selected_items[0])
        transaction_data = self._get_transaction_by_id(transaction_id)
        
        if transaction_data:
            copied_data = list(transaction_data)
            copied_data[0] = None
            copied_data[1] = date.today().strftime('%Y-%m-%d')
            
            EditTransactionDialog(self, self.db, copied_data)
    
    def _show_transaction_details(self):
        """Показывает детали выбранной транзакции"""
        selected_items = self.transactions_tree.selection()
        if not selected_items:
            messagebox.showinfo("Детали", "Выберите транзакцию для просмотра деталей", parent=self)
            return
        
        transaction_id = int(selected_items[0])
        transaction_data = self.transactions_tree.item(selected_items[0], 'values')
        
        full_transaction = self._get_transaction_by_id(transaction_id)
        
        details_text = f"ID: {transaction_id}\n"
        details_text += f"Дата: {transaction_data[0]}\n"
        details_text += f"Тип: {transaction_data[1]}\n" 
        details_text += f"Сумма: {transaction_data[2]}\n"
        details_text += f"Категория: {transaction_data[4]}\n"
        details_text += f"Счет: {transaction_data[5]}\n"
        details_text += f"Описание: {transaction_data[6]}\n"
        
        if full_transaction:
            account_info = self.accounts_data.get(full_transaction[7], {})
            details_text += f"\nДополнительно:\n"
            details_text += f"Тип счета: {account_info.get('type', 'Неизвестно')}\n"
            details_text += f"Баланс счета: {account_info.get('balance', 0):.2f} ₽"
        
        messagebox.showinfo("Детали транзакции", details_text, parent=self)
    
    # --- Утилиты ---
    def show_status_message(self, message, duration_ms=3000, message_type="info", icon=""):
        """Показывает сообщение в строке статуса."""
        if hasattr(self, '_status_message_timer'):
            try:
                self.after_cancel(self._status_message_timer)
            except:
                pass
        
        if icon:
            display_message = f"{icon} {message}"
        else:
            icon_map = {
                "success": "✅",
                "warning": "⚠️", 
                "error": "❌",
                "info": "ℹ️"
            }
            display_message = f"{icon_map.get(message_type, '')} {message}"
        
        colors = {
            "info": "black",
            "success": "#2e7d32",
            "warning": "#f57c00",
            "error": "#c62828"
        }
        
        font = ("TkDefaultFont", 9)
        if message_type in ["error", "warning"]:
            font = ("TkDefaultFont", 9, "bold")
        
        self.status_bar.config(
            text=display_message.strip(),
            foreground=colors.get(message_type, "black"),
            font=font,
            relief=tk.RAISED if message_type in ["error", "warning"] else tk.SUNKEN
        )
        
        self.status_bar.update_idletasks()
        
        if not hasattr(self, '_original_status_text'):
            self._original_status_text = "Готово."
        
        self._status_message_timer = self.after(
            duration_ms, 
            self._reset_status_message
        )

    def _reset_status_message(self):
        """Сбрасывает статусное сообщение к исходному состоянию."""
        self.status_bar.config(
            text="Готово.",
            foreground="black",
            font=("TkDefaultFont", 9),
            relief=tk.SUNKEN
        )
    
    # --- Универсальные методы ---
    def setup_treeview_management(self, parent, treeview, delete_callback, edit_callback=None, additional_commands=None):
        """
        Универсальная настройка управления Treeview
        """
        
        def on_key_press(event):
            if event.keysym == 'Delete':
                selected_items = treeview.selection()
                if selected_items:
                    delete_callback()
                    return "break"
        
        treeview.bind('<Delete>', on_key_press)
        
        context_menu = tk.Menu(parent, tearoff=0)
        
        if edit_callback:
            context_menu.add_command(label="✏️ Редактировать", command=edit_callback)
            context_menu.add_separator()
        
        context_menu.add_command(label="🗑️ Удалить", command=delete_callback)
        
        if additional_commands:
            context_menu.add_separator()
            for label, command in additional_commands:
                context_menu.add_command(label=label, command=command)
        
        def show_context_menu(event):
            selected_items = treeview.selection()
            if selected_items:
                try:
                    context_menu.tk_popup(event.x_root, event.y_root)
                finally:
                    context_menu.grab_release()
        
        treeview.bind("<Button-3>", show_context_menu)
        
        def on_click(event):
            treeview.focus()
        
        treeview.bind('<Button-1>', on_click)
        
        if edit_callback:
            treeview.bind("<Double-1>", lambda e: edit_callback())
    
    def delete_selected_items_universal(self, treeview, item_type, delete_callback, refresh_callback=None):
        """
        Универсальный метод для удаления выбранных элементов из любого Treeview
        """
        selected_items = treeview.selection()
        if not selected_items:
            messagebox.showinfo("Удаление", f"Выберите {item_type} для удаления.", parent=self)
            return False
        
        if not messagebox.askyesno("Подтверждение удаления", 
                                  f"Вы уверены, что хотите удалить {len(selected_items)} выбранных {item_type}?",
                                  parent=self):
            return False
        
        success_count = 0
        failed_count = 0
        
        for item_id in selected_items:
            try:
                item_id_int = int(item_id)
                if delete_callback(item_id_int):
                    success_count += 1
                else:
                    failed_count += 1
            except ValueError:
                failed_count += 1
        
        if success_count > 0:
            message_text = f"Успешно удалено {success_count} {item_type}."
            if failed_count > 0:
                message_text += f"\nНе удалось удалить {failed_count} {item_type}."
            messagebox.showinfo("Результат", message_text, parent=self)
            
            if refresh_callback:
                refresh_callback()
            
            # Обновляем родительское окно
            if hasattr(self.parent, '_post_dialog_update'):
                self.parent._post_dialog_update()
            
            return True
        else:
            messagebox.showerror("Ошибка", f"Не удалось удалить выбранные {item_type}.", parent=self)
            return False
          
    # Открытие деалогов
    def _open_transfer_dialog(self):
            return self.parent.window_manager.open_window('transfer', self.db, self.accounts_data)
    
    def _open_reconciliation_dialog(self):
            return self.parent.window_manager.open_window('reconciliation', self.db, self.accounts_data)
    
    def _open_account_management(self):
        return self.parent.window_manager.open_window('accounts', self.db)
    
    def _open_category_management(self):
        return self.parent.window_manager.open_window('categories', self.db)
    
    def _open_credit_cards(self):
        return self.parent.window_manager.open_window('credit_cards', self.db)
    
    def _open_loan_management(self):
        return self.parent.window_manager.open_window('loans', self.db)