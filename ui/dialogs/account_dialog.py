import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative
from ui.widgets.calendar_widgets import TtkDateEntry  # если используете

class AccountManagementDialog(tk.Toplevel):
    """Диалог для управления счетами в Tkinter."""
    
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager
        self.accounts = self.db.get_accounts()
        
        self.title("Управление Счетами")
        self.geometry("400x600")
        
        center_window_relative(self, self.parent)
        
        self._create_ui()
        
    def _create_ui(self):
        """Создает интерфейс диалога."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)
        
        self.accounts_tree = ttk.Treeview(tree_frame, columns=("Название", "Тип", "Баланс"), show="headings")
        self.accounts_tree.heading("Название", text="Название")
        self.accounts_tree.heading("Тип", text="Тип")
        self.accounts_tree.heading("Баланс", text="Баланс")
        self.accounts_tree.column("Название", width=150)
        self.accounts_tree.column("Тип", width=100)
        self.accounts_tree.column("Баланс", width=100)
        self.accounts_tree.pack(side="left", fill="both", expand=True)
        
        yscrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.accounts_tree.yview)
        yscrollbar.pack(side="right", fill="y")
        self.accounts_tree.config(yscrollcommand=yscrollbar.set)
        
        if hasattr(self.parent, 'setup_treeview_management'):
            self.parent.setup_treeview_management(
                parent=self,
                treeview=self.accounts_tree,
                delete_callback=self._delete_selected_account,
                edit_callback=self._edit_account,
                additional_commands=[
                    ("📊 Статистика счета", self._show_account_stats),
                    ("🔄 Обновить баланс", self._refresh_account_balance),
                    ("🧮 Пересчитать баланс", self._recalculate_single_account_balance)
                ]
            )

        self.accounts_tree.bind("<<TreeviewSelect>>", self._on_account_select)
        
        form_frame = ttk.LabelFrame(main_frame, text="Добавить/Редактировать счет")
        form_frame.pack(pady=5, fill="x")
        
        form_grid = ttk.Frame(form_frame)
        form_grid.pack(padx=5, pady=5, fill="x")

        ttk.Label(form_grid, text="Название счета:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.name_input = ttk.Entry(form_grid)
        self.name_input.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_grid, text="Тип счета:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.type_combo_var = tk.StringVar()
        self.type_combo = ttk.Combobox(form_grid, textvariable=self.type_combo_var, 
                                      values=["Cash", "Bank Account", "Credit Card"], state="readonly")
        self.type_combo.set("Bank Account") 
        self.type_combo.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_grid, text="Начальный баланс:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.initial_balance_input = ttk.Entry(form_grid)
        self.initial_balance_input.insert(0, "0.0")
        self.initial_balance_input.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_grid, text="Кредитный лимит:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.credit_limit_input = ttk.Entry(form_grid)
        self.credit_limit_input.insert(0, "0.0")
        self.credit_limit_input.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_grid, text="День платежа (1-31):").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.payment_day_input = ttk.Entry(form_grid)
        self.payment_day_input.insert(0, "1")
        self.payment_day_input.grid(row=4, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(form_grid, text="Мин. платеж (%):").grid(row=5, column=0, padx=5, pady=2, sticky="w")
        self.min_payment_input = ttk.Entry(form_grid)
        self.min_payment_input.insert(0, "5.0")
        self.min_payment_input.grid(row=5, column=1, padx=5, pady=2, sticky="ew")

        self.type_combo.bind('<<ComboboxSelected>>', self._on_type_change)

        button_frame = ttk.Frame(form_grid)
        button_frame.grid(row=6, column=0, columnspan=2, pady=5, sticky="ew")

        self.add_button = ttk.Button(button_frame, text="Добавить", command=self._add_account)
        self.add_button.pack(side="left", expand=True, fill="x", padx=2)

        self.edit_button = ttk.Button(button_frame, text="Сохранить изменения", 
                                     command=self._edit_account, state="disabled")
        self.edit_button.pack(side="left", expand=True, fill="x", padx=2)

        special_buttons_frame = ttk.Frame(main_frame)
        special_buttons_frame.pack(fill="x", pady=5)

        self.load_initial_balance_btn = ttk.Button(
            special_buttons_frame, 
            text="🔄 Загрузить начальный баланс из БД", 
            command=self._load_initial_balance_from_db
        )
        self.load_initial_balance_btn.pack(fill="x", pady=2)

        self.fix_balances_btn = ttk.Button(
            special_buttons_frame, 
            text="⚙️ Исправить балансы (после импорта)", 
            command=self._fix_balances_after_import
        )
        self.fix_balances_btn.pack(fill="x", pady=2)

        self.recalculate_balances_btn = ttk.Button(
            special_buttons_frame, 
            text="🧮 Пересчитать все текущие балансы", 
            command=self._recalculate_current_balances
        )
        self.recalculate_balances_btn.pack(fill="x", pady=2)

        close_frame = ttk.Frame(main_frame)
        close_frame.pack(pady=5)

        close_btn = ttk.Button(close_frame, text="Закрыть", command=self.on_close)
        close_btn.pack(pady=5)

        form_grid.grid_columnconfigure(1, weight=1)

        self.editing_account_id = None 
        self.load_accounts_into_tree()
        
    def on_close(self):
        """Закрывает диалоговое окно."""
        self.grab_release()
        self.destroy()

    def _show_recalculation_details(self):
        """Показывает детали перерасчета балансов"""
        accounts = self.db.get_accounts()
        
        details_text = "Детали перерасчета:\n\n"
        
        for account in accounts:
            account_id, name, acc_type, initial_balance, current_balance = account
            details_text += f"• {name}: {current_balance:.2f} ₽\n"
        
        details_text += f"\nВсего обработано: {len(accounts)} счетов"
        
        details_window = tk.Toplevel(self)
        details_window.title("Детали перерасчета")
        details_window.geometry("400x300")
        details_window.transient(self)
        details_window.grab_set()
        
        text_frame = ttk.Frame(details_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 9))
        text_widget.insert("1.0", details_text)
        text_widget.config(state="disabled")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Button(details_window, text="Закрыть", command=details_window.destroy).pack(pady=10)
        
    def _recalculate_single_account_balance(self):
        """Пересчитывает баланс только для выбранного счета"""
        selected_item = self.accounts_tree.selection()
        if not selected_item:
            messagebox.showinfo("Перерасчет", "Выберите счет для перерасчета.", parent=self)
            return
        
        account_id = int(selected_item[0])
        account_name = self.accounts_tree.item(selected_item[0], 'values')[0]
        
        if self.db.recalculate_single_account_balance(account_id):
            self.load_accounts_into_tree()
            messagebox.showinfo(
                "Перерасчет завершен", 
                f"Баланс счета '{account_name}' пересчитан.",
                parent=self
            )
        else:
            messagebox.showerror("Ошибка", "Не удалось пересчитать баланс.", parent=self)
    
    def _recalculate_current_balances(self):
        """Пересчитывает текущие балансы для всех счетов на основе транзакций"""
        if not messagebox.askyesno(
            "Перерасчет балансов", 
            "Эта функция пересчитает текущие балансы ВСЕХ счетов на основе транзакций.\n\n"
            "Это полезно если:\n"
            "• Балансы не соответствуют транзакциям\n"
            "• Были прямые изменения в БД\n"
            "• Нужно восстановить корректные данные\n\n"
            "Процесс может занять несколько секунд.\nПродолжить?",
            parent=self
        ):
            return
        
        progress_window = tk.Toplevel(self)
        progress_window.title("Перерасчет балансов")
        progress_window.geometry("400x150")
        progress_window.transient(self)
        progress_window.grab_set()
        
        ttk.Label(progress_window, text="Пересчет текущих балансов...", 
                 font=("TkDefaultFont", 10, "bold")).pack(pady=10)
        
        progress_status = ttk.Label(progress_window, text="Подготовка...", 
                                   font=("TkDefaultFont", 9))
        progress_status.pack(pady=5)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, 
                                     maximum=100, length=350)
        progress_bar.pack(fill="x", padx=20, pady=10)
        
        import threading
        
        def run_recalculation():
            try:
                def update_progress(status, percent):
                    if progress_window.winfo_exists():
                        progress_window.after(0, lambda: update_ui(status, percent))
                
                def update_ui(status, percent):
                    progress_status.config(text=status)
                    progress_var.set(percent)
                    progress_window.update()
                
                result = self.db.recalculate_all_current_balances(update_progress)
                
                progress_window.after(0, lambda: finish_recalculation(result))
                
            except Exception as e:
                progress_window.after(0, lambda: finish_recalculation(0, str(e)))
        
        def finish_recalculation(success_count, error=None):
            progress_window.destroy()
            
            if error:
                messagebox.showerror(
                    "Ошибка перерасчета", 
                    f"Произошла ошибка:\n{error}",
                    parent=self
                )
            elif success_count > 0:
                self.load_accounts_into_tree()
                
                messagebox.showinfo(
                    "Перерасчет завершен", 
                    f"✅ Успешно пересчитано {success_count} счетов\n\n"
                    "Текущие балансы теперь соответствуют сумме всех транзакций.",
                    parent=self
                )
                
                self._show_recalculation_details()
            else:
                messagebox.showinfo(
                    "Перерасчет", 
                    "Не удалось пересчитать балансы.\n"
                    "Возможно, нет счетов или транзакций.",
                    parent=self
                )
        
        recalc_thread = threading.Thread(target=run_recalculation, daemon=True)
        recalc_thread.start()
        
    def _load_initial_balance_from_db(self):
        """Загружает начальный баланс из БД для выбранного счета"""
        selected_item = self.accounts_tree.focus()
        if not selected_item:
            messagebox.showinfo("Загрузка баланса", "Выберите счет для загрузки начального баланса.", parent=self)
            return
        
        account_id = int(selected_item)
        account_name = self.accounts_tree.item(selected_item, 'values')[0]
        
        fresh_account_data = self.db.get_account_by_id(account_id)
        if not fresh_account_data:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные счета '{account_name}' из БД.", parent=self)
            return
        
        fresh_initial_balance = float(fresh_account_data[3])
        fresh_current_balance = float(fresh_account_data[4])
        
        print(f"DEBUG: Fresh data from DB - initial: {fresh_initial_balance}, current: {fresh_current_balance}")
        
        if self.db.update_account_initial_balance(account_id, fresh_initial_balance):
            self.load_accounts_into_tree()
            
            messagebox.showinfo(
                "Баланс обновлен", 
                f"Счет: {account_name}\n"
                f"Начальный баланс обновлен: {fresh_initial_balance:.2f} ₽\n"
                f"Текущий баланс: {fresh_current_balance:.2f} ₽",
                parent=self
            )
        else:
            messagebox.showerror("Ошибка", "Не удалось обновить баланс в приложении.", parent=self)

    def _fix_balances_after_import(self):
        """Исправляет балансы после импорта CSV - устанавливает initial = current"""
        if not messagebox.askyesno(
            "Исправление балансов", 
            "Эта функция установит начальный баланс равным текущему для ВСЕХ счетов.\n\n"
            "Используйте после импорта из CSV, когда начальный баланс = 0, а текущий ≠ 0.\n\n"
            "Продолжить?",
            parent=self
        ):
            return
        
        fixed_count = 0
        accounts = self.db.get_accounts()
        
        for account in accounts:
            account_id, name, acc_type, initial_balance, current_balance = account
            
            if initial_balance == 0.0 and current_balance != 0.0:
                if self.db.update_account_initial_balance(account_id, current_balance):
                    fixed_count += 1
                    print(f"DEBUG: Fixed balances for {name}: initial={current_balance}")
        
        self.load_accounts_into_tree()
        
        if fixed_count > 0:
            messagebox.showinfo(
                "Балансы исправлены", 
                f"Исправлено {fixed_count} счетов.\n"
                f"Начальный баланс установлен равным текущему.",
                parent=self
            )
        else:
            messagebox.showinfo(
                "Исправление не требуется", 
                "Нет счетов для исправления.\n"
                "Все начальные балансы уже соответствуют текущим.",
                parent=self
            )
    
    def _on_account_select(self, event):
        print(f"DEBUG: _on_account_select вызван")
        selected_item = self.accounts_tree.focus()
        print(f"DEBUG: selected_item = {selected_item}")
        
        if selected_item:
            self.edit_button.config(state="normal")
            print(f"DEBUG: Кнопка 'Сохранить изменения' активирована")
            
            values = self.accounts_tree.item(selected_item, 'values')
            account_name = values[0]
            account_type = values[1]
            
            self.accounts = self.db.get_accounts()
            account_data = None
            
            for acc in self.accounts:
                if acc[0] == int(selected_item):
                    account_data = acc
                    break
            
            if account_data:
                print(f"DEBUG: Found account data: {account_data}")
                print(f"DEBUG: Account data length: {len(account_data)}")
                
                initial_balance = account_data[3] if len(account_data) > 3 else 0.0
                current_balance = account_data[4] if len(account_data) > 4 else 0.0
                
                self.type_combo_var.set(account_type)
                self._on_type_change()
                
                if account_type == "Credit Card" and len(account_data) > 7:
                    credit_limit = account_data[5] if len(account_data) > 5 else 0.0
                    payment_due_day = account_data[6] if len(account_data) > 6 else 1
                    min_payment_percent = account_data[7] if len(account_data) > 7 else 5.0
                    
                    print(f"DEBUG: Credit card data - limit={credit_limit}, day={payment_due_day}, min%={min_payment_percent}")
                    
                    self.credit_limit_input.delete(0, tk.END)
                    self.credit_limit_input.insert(0, f"{credit_limit:.2f}")
                    
                    self.payment_day_input.delete(0, tk.END)
                    self.payment_day_input.insert(0, str(payment_due_day))
                    
                    self.min_payment_input.delete(0, tk.END)
                    self.min_payment_input.insert(0, f"{min_payment_percent:.2f}")
                else:
                    self.credit_limit_input.delete(0, tk.END)
                    self.credit_limit_input.insert(0, "0.0")
                    self.payment_day_input.delete(0, tk.END)
                    self.payment_day_input.insert(0, "1")
                    self.min_payment_input.delete(0, tk.END)
                    self.min_payment_input.insert(0, "5.0")
                
                print(f"DEBUG Selected account {account_name}: initial={initial_balance}, current={current_balance}")
                
                self.name_input.delete(0, tk.END)
                self.name_input.insert(0, account_name)
                self.initial_balance_input.delete(0, tk.END)
                self.initial_balance_input.insert(0, f"{initial_balance:.2f}")
            
            self.editing_account_id = int(selected_item)
            self.initial_balance_input.config(state="disabled")
        else:
            print(f"DEBUG: No item selected, resetting form")
            self._reset_form_state()

    def load_accounts_into_tree(self):
        """Загружает счета из БД в таблицу"""
        for i in self.accounts_tree.get_children():
            self.accounts_tree.delete(i)
        
        self.accounts = self.db.get_accounts()
        if self.accounts:
            for account in self.accounts:
                acc_id = account[0]
                name = account[1]
                acc_type = account[2]
                initial_balance = account[3] if len(account) > 3 else 0.0
                current_balance = account[4] if len(account) > 4 else 0.0
                
                if acc_type == "Credit Card" and len(account) > 7:
                    credit_limit = account[5] if len(account) > 5 else 0.0
                    payment_due_day = account[6] if len(account) > 6 else 1
                    min_payment_percent = account[7] if len(account) > 7 else 5.0
                    print(f"DEBUG Loading CREDIT CARD {name}: credit_limit={credit_limit}, due_day={payment_due_day}, min%={min_payment_percent}")
                
                print(f"DEBUG Loading account {name}: initial={initial_balance}, current={current_balance}")
                
                self.accounts_tree.insert("", "end", iid=acc_id, 
                                        values=(name, acc_type, f"{current_balance:.2f} ₽"))
        
        self.accounts_tree.selection_remove(self.accounts_tree.selection())
        self._on_account_select(None)

    def _add_account(self):
        name = self.name_input.get().strip()
        acc_type = self.type_combo_var.get()
        initial_balance_str = self.initial_balance_input.get().strip()
        credit_limit_str = self.credit_limit_input.get().strip()
        payment_day_str = self.payment_day_input.get().strip()
        min_payment_str = self.min_payment_input.get().strip()
        
        if not name:
            messagebox.showerror("Ошибка", "Введите название счета.", parent=self)
            return
        
        try:
            initial_balance = float(initial_balance_str.replace(',', '.'))
            
            credit_limit = 0.0
            payment_due_day = 1
            min_payment_percent = 5.0
            
            if acc_type == "Credit Card":
                credit_limit = float(credit_limit_str.replace(',', '.')) if credit_limit_str else 0.0
                payment_due_day = int(payment_day_str) if payment_day_str else 1
                min_payment_percent = float(min_payment_str.replace(',', '.')) if min_payment_str else 5.0
                
                if payment_due_day < 1 or payment_due_day > 31:
                    messagebox.showerror("Ошибка", "День платежа должен быть от 1 до 31.", parent=self)
                    return
                
                if min_payment_percent < 0 or min_payment_percent > 100:
                    messagebox.showerror("Ошибка", "Минимальный платеж должен быть от 0 до 100%.", parent=self)
                    return
                    
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректное число: {e}", parent=self)
            return
        
        if self.db.add_account(name, acc_type, initial_balance, 
                              credit_limit, payment_due_day, min_payment_percent):
            self.load_accounts_into_tree()
            self._reset_form_state()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить счет.", parent=self)
      
    def _on_type_change(self, event=None):
        """Показывает/скрывает поля для кредитной карты."""
        acc_type = self.type_combo_var.get()
        
        if acc_type == "Credit Card":
            self.credit_limit_input.config(state="normal")
            self.payment_day_input.config(state="normal")
            self.min_payment_input.config(state="normal")
        else:
            self.credit_limit_input.config(state="disabled")
            self.payment_day_input.config(state="disabled")
            self.min_payment_input.config(state="disabled")
    
    def _edit_account(self):
        """Редактирует выбранный счет."""
        print(f"DEBUG: ===== _edit_account START =====")
        print(f"DEBUG: editing_account_id = {self.editing_account_id}")
        print(f"DEBUG: accounts_tree selection: {self.accounts_tree.selection()}")
        
        if not self.editing_account_id:
            messagebox.showwarning("Редактирование", "Выберите счет для редактирования.", parent=self)
            return
        
        name = self.name_input.get().strip()
        acc_type = self.type_combo_var.get()
        initial_balance_str = self.initial_balance_input.get().strip()
        credit_limit_str = self.credit_limit_input.get().strip()
        payment_day_str = self.payment_day_input.get().strip()
        min_payment_str = self.min_payment_input.get().strip()
        
        print(f"DEBUG: Form data - name='{name}', type='{acc_type}', initial_balance='{initial_balance_str}'")
        print(f"DEBUG: Credit card fields - credit_limit='{credit_limit_str}', payment_day='{payment_day_str}', min_payment='{min_payment_str}'")
        
        if not name:
            messagebox.showerror("Ошибка", "Введите название счета.", parent=self)
            return
        
        try:
            initial_balance = float(initial_balance_str.replace(',', '.'))
            
            credit_limit = 0.0
            payment_due_day = 1
            min_payment_percent = 5.0
            
            if acc_type == "Credit Card":
                credit_limit = float(credit_limit_str.replace(',', '.')) if credit_limit_str else 0.0
                payment_due_day = int(payment_day_str) if payment_day_str else 1
                min_payment_percent = float(min_payment_str.replace(',', '.')) if min_payment_str else 5.0
                
                if payment_due_day < 1 or payment_due_day > 31:
                    messagebox.showerror("Ошибка", "День платежа должен быть от 1 до 31.", parent=self)
                    return
                
                if min_payment_percent < 0 or min_payment_percent > 100:
                    messagebox.showerror("Ошибка", "Минимальный платеж должен быть от 0 до 100%.", parent=self)
                    return
        
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректное число: {e}", parent=self)
            return
        
        print(f"DEBUG: Checking for existing account with name '{name}'")
        existing_account = None
        
        all_accounts = self.db.get_accounts()
        for account in all_accounts:
            if account[1] == name and account[0] != self.editing_account_id:
                existing_account = account
                break
        
        if existing_account:
            print(f"DEBUG: Account name conflict - existing ID: {existing_account[0]}, editing ID: {self.editing_account_id}")
            messagebox.showerror("Ошибка", f"Счет с именем '{name}' уже существует.", parent=self)
            return
        
        print(f"DEBUG: Calling db.update_account...")
        
        current_account = None
        for account in self.accounts:
            if account[0] == self.editing_account_id:
                current_account = account
                break
        
        if not current_account:
            messagebox.showerror("Ошибка", "Не удалось найти данные текущего счета.", parent=self)
            return
        
        result = self.db.update_account(
            self.editing_account_id,
            name,
            acc_type,
            initial_balance,
            credit_limit,
            payment_due_day,
            min_payment_percent
        )
        
        print(f"DEBUG: db.update_account returned: {result}")
        
        if result:
            print(f"DEBUG: Update successful!")
            self.show_status_message(f"Счет '{name}' успешно обновлен")
            
            self.load_accounts_into_tree()
            self._reset_form_state()
            
            if hasattr(self.master, '_post_dialog_update'):
                self.master._post_dialog_update()
        else:
            print(f"DEBUG: Update failed!")
            messagebox.showerror("Ошибка", f"Не удалось обновить счет '{name}'.", parent=self)
        
        print(f"DEBUG: ===== _edit_account END =====")

    def _delete_selected_account(self):
        """Удаляет выбранные счета с проверкой операций"""
        selected_items = self.accounts_tree.selection()
        if not selected_items:
            messagebox.showinfo("Удаление", "Выберите счета для удаления.", parent=self)
            return
        
        success_count = 0
        failed_count = 0
        blocked_count = 0
        
        for item_id in selected_items:
            try:
                account_id = int(item_id)
                account_name = self.accounts_tree.item(item_id, 'values')[0]
                
                result = self.db.delete_account(account_id)
                
                if result is True:
                    success_count += 1
                    print(f"DEBUG: Successfully deleted account {account_name}")
                elif isinstance(result, dict) and not result["can_delete"]:
                    blocked_count += 1
                    self._show_cannot_delete_message(result)
                else:
                    failed_count += 1
                    print(f"DEBUG: Failed to delete account {account_name}")
                    
            except ValueError:
                failed_count += 1
        
        self._show_delete_result(success_count, failed_count, blocked_count)
        self.load_accounts_into_tree()

    def _show_cannot_delete_message(self, result_info):
        """Показывает сообщение о невозможности удаления счета"""
        operations_details = []
        if result_info["transactions_count"] > 0:
            operations_details.append(f"• Транзакций: {result_info['transactions_count']}")
        if result_info["transfers_from_count"] > 0:
            operations_details.append(f"• Исходящих переводов: {result_info['transfers_from_count']}")
        if result_info["transfers_to_count"] > 0:
            operations_details.append(f"• Входящих переводов: {result_info['transfers_to_count']}")
        if result_info["loans_count"] > 0:
            operations_details.append(f"• Связанных займов: {result_info['loans_count']}")
        
        operations_text = "\n".join(operations_details)
        
        messagebox.showwarning(
            "Нельзя удалить счет", 
            f"❌ Счет '{result_info['account_name']}' нельзя удалить.\n\n"
            f"На счете зафиксированы финансовые операции:\n"
            f"{operations_text}\n\n"
            f"📊 Всего операций: {result_info['total_operations']}\n\n"
            f"Для удаления счета необходимо сначала удалить все связанные операции "
            f"или перенести их на другие счета.",
            parent=self
        )

    def _show_delete_result(self, success_count, failed_count, blocked_count):
        """Показывает итоговый результат удаления"""
        messages = []
        if success_count > 0:
            messages.append(f"✅ Успешно удалено: {success_count}")
        if blocked_count > 0:
            messages.append(f"🚫 Нельзя удалить (есть операции): {blocked_count}")
        if failed_count > 0:
            messages.append(f"❌ Ошибка удаления: {failed_count}")
        
        if messages:
            messagebox.showinfo("Результат удаления", "\n".join(messages), parent=self)

    def _reset_form_state(self):
        """Сбрасывает поля формы и состояние кнопок."""
        self.name_input.delete(0, tk.END)
        self.type_combo.set("Bank Account")
        self.initial_balance_input.delete(0, tk.END)
        self.initial_balance_input.insert(0, "0.0")
        self.initial_balance_input.config(state="normal")
        self.editing_account_id = None
        self.edit_button.config(state="disabled")
        self.add_button.config(state="normal")
     
    def _show_account_stats(self):
        """Показывает подробную статистику по выбранному счету"""
        selected_item = self.accounts_tree.selection()
        if not selected_item:
            messagebox.showinfo("Статистика", "Выберите счет для просмотра статистики.", parent=self)
            return
        
        account_id = int(selected_item[0])
        account_name = self.accounts_tree.item(selected_item[0], 'values')[0]
        
        stats = self._calculate_account_statistics(account_id)
        stats_text = self._format_account_stats_message(account_name, stats)
        self._show_stats_dialog(account_name, stats_text)

    def _calculate_account_statistics(self, account_id):
        """Вычисляет статистику по счету с обработкой ошибок"""
        stats = {
            'current_balance': 0,
            'total_income': 0,
            'total_expense': 0,
            'transaction_count': 0,
            'transfers_in_count': 0,
            'transfers_out_count': 0,
            'recent_activity': [],
            'top_categories': [],
            'account_name': 'Неизвестно'
        }
        
        try:
            account = self.db.get_account_by_id(account_id)
            if account:
                stats['current_balance'] = float(account[4]) if account[4] is not None else 0.0
                stats['account_name'] = account[1]
            
            transactions = self.db.get_transactions(account_id=account_id)
            stats['transaction_count'] = len(transactions) if transactions else 0
            
            if transactions:
                for transaction in transactions:
                    try:
                        amount_str = transaction[2]
                        amount = float(amount_str) if amount_str is not None else 0.0
                        
                        if amount > 0:
                            stats['total_income'] += amount
                        else:
                            stats['total_expense'] += abs(amount)
                    except (ValueError, TypeError, IndexError) as e:
                        print(f"DEBUG: Error processing transaction {transaction}: {e}")
                        continue
                
                try:
                    recent_transactions = sorted(transactions, key=lambda x: x[1] if x[1] else "", reverse=True)[:5]
                    stats['recent_activity'] = recent_transactions
                except Exception as e:
                    print(f"DEBUG: Error sorting recent transactions: {e}")
                    stats['recent_activity'] = transactions[:5]
            
            if transactions and stats['total_expense'] > 0:
                try:
                    expense_categories = {}
                    for transaction in transactions:
                        try:
                            amount_str = transaction[2]
                            amount = float(amount_str) if amount_str is not None else 0.0
                            category = transaction[4] or "Без категории"
                            
                            if amount < 0:
                                expense_categories[category] = expense_categories.get(category, 0) + abs(amount)
                        except (ValueError, TypeError, IndexError) as e:
                            print(f"DEBUG: Error processing category for transaction {transaction}: {e}")
                            continue
                    
                    if expense_categories:
                        stats['top_categories'] = sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)[:5]
                except Exception as e:
                    print(f"DEBUG: Error calculating top categories: {e}")
            
            try:
                transfers = self.db.get_transfers(account_id=account_id)
                if transfers:
                    for transfer in transfers:
                        try:
                            transfer_id, date, amount, from_acc, to_acc, description = transfer
                            
                            if to_acc == stats['account_name']:
                                stats['transfers_in_count'] += 1
                            elif from_acc == stats['account_name']:
                                stats['transfers_out_count'] += 1
                        except (ValueError, TypeError, IndexError) as e:
                            print(f"DEBUG: Error processing transfer {transfer}: {e}")
                            continue
            except Exception as e:
                print(f"DEBUG: Error getting transfers: {e}")
                
        except Exception as e:
            print(f"DEBUG: Major error in account statistics: {e}")
        
        return stats

    def _format_account_stats_message(self, account_name, stats):
        """Форматирует сообщение со статистикой"""
        message = f"📊 Статистика счета: {account_name}\n\n"
        message += f"💰 Текущий баланс: {stats['current_balance']:.2f} ₽\n"
        message += f"📈 Всего доходов: {stats['total_income']:.2f} ₽\n"
        message += f"📉 Всего расходов: {stats['total_expense']:.2f} ₽\n"
        message += f"🔄 Чистый поток: {stats['total_income'] - stats['total_expense']:.2f} ₽\n\n"
        
        message += f"📋 Количество операций:\n"
        message += f"   • Транзакций: {stats['transaction_count']}\n"
        message += f"   • Входящих переводов: {stats['transfers_in_count']}\n"
        message += f"   • Исходящих переводов: {stats['transfers_out_count']}\n"
        message += f"   • Всего: {stats['transaction_count'] + stats['transfers_in_count'] + stats['transfers_out_count']}\n\n"
        
        if stats['top_categories']:
            message += "🏆 Топ категорий расходов:\n"
            for category, amount in stats['top_categories']:
                percentage = (amount / stats['total_expense'] * 100) if stats['total_expense'] > 0 else 0
                message += f"   • {category}: {amount:.2f} ₽ ({percentage:.1f}%)\n"
            message += "\n"
        
        if stats['recent_activity']:
            message += "🕒 Последние операции:\n"
            for trans in stats['recent_activity'][:3]:
                if len(trans) >= 9:
                    trans_id, date, amount, trans_type, category, description, acc_name, acc_id, quantity = trans
                elif len(trans) == 8:
                    trans_id, date, amount, trans_type, category, description, acc_name, acc_id = trans
                    quantity = 1.0
                
                amount_str = f"+{amount:.2f}" if float(amount) > 0 else f"{amount:.2f}"
                qty_info = f" ({quantity} ед)" if quantity != 1.0 else ""
                message += f"   • {date}: {amount_str} ₽ ({category or 'Без категории'}){qty_info}\n"
        
        return message

    def _show_stats_dialog(self, account_name, stats_text):
        """Показывает статистику в диалоговом окне с прокруткой"""
        stats_window = tk.Toplevel(self)
        stats_window.title(f"Статистика счета: {account_name}")
        stats_window.geometry("500x400")        
        stats_window.transient(self)
        stats_window.grab_set()
        
        text_frame = ttk.Frame(stats_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 10))
        text_widget.insert("1.0", stats_text)
        text_widget.config(state="disabled")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Button(stats_window, text="Закрыть", command=stats_window.destroy).pack(pady=10)
        
        from widgets.window_utils import center_window_relative
        center_window_relative(stats_window, self)
        stats_window.focus_set()

    def _refresh_account_balance(self):
        """Обновляет баланс выбранного счета"""
        selected_item = self.accounts_tree.selection()
        if not selected_item:
            messagebox.showinfo("Обновление", "Выберите счет для обновления.", parent=self)
            return
        
        account_id = int(selected_item[0])
        account_name = self.accounts_tree.item(selected_item[0], 'values')[0]
        
        fresh_account_data = self.db.get_account_by_id(account_id)
        if not fresh_account_data:
            messagebox.showerror("Ошибка", f"Не удалось загрузить данные счета '{account_name}'.", parent=self)
            return
        
        fresh_initial_balance = float(fresh_account_data[3])
        fresh_current_balance = float(fresh_account_data[4])
        
        print(f"DEBUG: Fresh data for {account_name}: initial={fresh_initial_balance}, current={fresh_current_balance}")
        
        self.load_accounts_into_tree()
        
        messagebox.showinfo(
            "Баланс обновлен", 
            f"Счет: {account_name}\n"
            f"Начальный баланс: {fresh_initial_balance:.2f} ₽\n"
            f"Текущий баланс: {fresh_current_balance:.2f} ₽",
            parent=self
        )

    def _show_account_chart(self):
        """Показывает график операций по счету"""
        messagebox.showinfo("В разработке", "График операций по счету в разработке", parent=self)
    
    def show_status_message(self, message, duration_ms=3000):
        """Показывает сообщение в статусе родительского окна"""
        if hasattr(self.master, 'show_status_message'):
            self.master.show_status_message(message, duration_ms)
        else:
            print(f"STATUS: {message}")