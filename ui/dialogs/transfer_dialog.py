import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative
from ui.widgets.calendar_widgets import TtkDateEntry  # если используете

class TransferDialog(tk.Toplevel):
    def __init__(self, parent, db_manager, accounts_data):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager
        self.accounts_data = accounts_data
        self.current_account_id = None
        self.last_selected_date = getattr(parent, 'last_selected_date', date.today().strftime('%Y-%m-%d'))
        
        self.current_filters = {
            "account_id": None,
            "counterparty": None,
            "date_from": None,
            "date_to": None
        }
                
        self.title("Управление Переводами")
        self.geometry("950x500")
        
        center_window_relative(self, self.parent)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._create_ui()
        
    def _create_ui(self):
        """Создание всех виджетов диалога."""
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        add_frame = ttk.Frame(notebook)
        notebook.add(add_frame, text="Добавить перевод")
        self._create_add_transfer_tab(add_frame)
        
        view_frame = ttk.Frame(notebook)
        notebook.add(view_frame, text="Все переводы")
        self._create_view_transfers_tab(view_frame)

    def _create_add_transfer_tab(self, master):
        """Создает вкладку для добавления переводов"""
        self.transfer_type = tk.StringVar(value="internal")
        
        type_frame = ttk.LabelFrame(master, text="Тип перевода")
        type_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        ttk.Radiobutton(type_frame, text="Между моими счетами", 
                       variable=self.transfer_type, value="internal",
                       command=self._update_transfer_type).pack(side="left", padx=10)
        ttk.Radiobutton(type_frame, text="Внешний перевод", 
                       variable=self.transfer_type, value="external",
                       command=self._update_transfer_type).pack(side="left", padx=10)

        ttk.Label(master, text="Дата:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.date_input = TtkDateEntry(master)
        self.date_input.var.set(self.last_selected_date)
        self.date_input.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(master, text="Сумма:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.amount_input = ttk.Entry(master)
        self.amount_input.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        
        self.internal_frame = ttk.Frame(master)
        self.internal_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        
        ttk.Label(self.internal_frame, text="Со счета:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.from_account_var = tk.StringVar(master)
        self.from_account_combo = ttk.Combobox(self.internal_frame, textvariable=self.from_account_var, state="readonly")
        self.from_account_combo.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        
        ttk.Label(self.internal_frame, text="На счет:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.to_account_var = tk.StringVar(master)
        self.to_account_combo = ttk.Combobox(self.internal_frame, textvariable=self.to_account_var, state="readonly")
        self.to_account_combo.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        self.external_frame = ttk.Frame(master)
        self.external_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="ew")
        
        ttk.Label(self.external_frame, text="Направление:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.direction_var = tk.StringVar(value="incoming")
        direction_frame = ttk.Frame(self.external_frame)
        direction_frame.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Radiobutton(direction_frame, text="Мне перевели", 
                       variable=self.direction_var, value="incoming").pack(side="left")
        ttk.Radiobutton(direction_frame, text="Я перевел", 
                       variable=self.direction_var, value="outgoing").pack(side="left")
        
        ttk.Label(self.external_frame, text="Счет:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.external_account_var = tk.StringVar(master)
        self.external_account_combo = ttk.Combobox(self.external_frame, textvariable=self.external_account_var, state="readonly")
        self.external_account_combo.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        ttk.Label(self.external_frame, text="Контрагент:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.counterparty_input = ttk.Entry(self.external_frame)
        self.counterparty_input.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(master, text="Описание:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.description_input = ttk.Entry(master)
        self.description_input.grid(row=4, column=1, padx=5, pady=2, sticky="ew")

        account_names = [acc_info['name'] for acc_id, acc_info in self.accounts_data.items()]
        self.from_account_combo['values'] = account_names
        self.to_account_combo['values'] = account_names
        self.external_account_combo['values'] = account_names
        
        if account_names:
            self.from_account_combo.set(account_names[0])
            if len(account_names) > 1: 
                 self.to_account_combo.set(account_names[1])
            else: 
                 self.to_account_combo.set(account_names[0])
            self.external_account_combo.set(account_names[0])

        self._update_transfer_type()

        button_frame = ttk.Frame(master)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.add_close_button = ttk.Button(button_frame, text="Добавить и закрыть", command=self._add_and_close)
        self.add_close_button.pack(side="left", padx=5)
        
        self.add_more_button = ttk.Button(button_frame, text="Добавить еще", command=self._add_more)
        self.add_more_button.pack(side="left", padx=5)
        
        self.cancel_button = ttk.Button(button_frame, text="Отмена", command=self.on_close)
        self.cancel_button.pack(side="left", padx=5)

        master.grid_columnconfigure(1, weight=1)

    def _create_view_transfers_tab(self, master):
        """Создает вкладку для просмотра и управления переводами"""
        filter_frame = ttk.LabelFrame(master, text="Фильтры")
        filter_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Счет:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.filter_account_var = tk.StringVar()
        self.filter_account_combo = ttk.Combobox(filter_frame, textvariable=self.filter_account_var, state="readonly")
        self.filter_account_combo['values'] = ["Все"] + [acc_info['name'] for acc_id, acc_info in self.accounts_data.items()]
        self.filter_account_combo.set("Все")
        self.filter_account_combo.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.filter_account_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        
        ttk.Label(filter_frame, text="Контрагент:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.filter_counterparty_var = tk.StringVar()
        self.filter_counterparty_combo = ttk.Combobox(filter_frame, textvariable=self.filter_counterparty_var, state="readonly")
        self.filter_counterparty_combo.grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        self.filter_counterparty_combo.bind("<<ComboboxSelected>>", self._apply_filters)

        self._update_counterparties_list()
        
        ttk.Label(filter_frame, text="Дата от:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.filter_date_from = TtkDateEntry(filter_frame)
        self.filter_date_from.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        self.filter_date_from.entry.bind("<KeyRelease>", self._apply_filters)
        
        ttk.Label(filter_frame, text="Дата до:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.filter_date_to = TtkDateEntry(filter_frame)
        self.filter_date_to.grid(row=1, column=3, padx=5, pady=2, sticky="ew")
        self.filter_date_to.entry.bind("<KeyRelease>", self._apply_filters)
        
        ttk.Button(filter_frame, text="Сбросить фильтры", command=self._reset_filters).grid(row=1, column=4, padx=5, pady=2)
        
        filter_frame.grid_columnconfigure(1, weight=1)
        filter_frame.grid_columnconfigure(3, weight=1)
        
        tree_frame = ttk.Frame(master)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.transfers_tree = ttk.Treeview(tree_frame, columns=("Дата", "Тип", "Сумма", "Откуда", "Куда", "Контрагент", "Описание"), show="headings")
        
        if hasattr(self.parent, 'setup_treeview_management'):
            self.parent.setup_treeview_management(
                self,
                self.transfers_tree,
                self._delete_selected_transfer,
                edit_callback=None,
                additional_commands=None
            )
        
        columns_config = {
            "Дата": 100, "Тип": 80, "Сумма": 100, 
            "Откуда": 120, "Куда": 120, "Контрагент": 120, "Описание": 200
        }
        
        for col, width in columns_config.items():
            self.transfers_tree.heading(col, text=col)
            self.transfers_tree.column(col, width=width)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.transfers_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.transfers_tree.configure(yscrollcommand=scrollbar.set)
        self.transfers_tree.pack(side="left", fill="both", expand=True)
        
        delete_button = ttk.Button(master, text="Удалить выбранные переводы", command=self._delete_selected_transfer)
        delete_button.pack(pady=5)
        
        self._load_transfers_data()

    def on_close(self):
        """Закрывает диалоговое окно."""
        self.grab_release()
        self.destroy()

    def _update_counterparties_list(self):
        """Обновляет список контрагентов из базы данных"""
        try:
            if not self.winfo_exists() or not self.filter_counterparty_combo.winfo_exists():
                print("DEBUG: TransferDialog closed, skipping counterparty update")
                return
                
            all_accounts = self.db.get_accounts()
            counterparties = []
            
            for account in all_accounts:
                if len(account) >= 2:
                    account_id = account[0]
                    name = account[1]
                    if "Контрагент:" in name:
                        counterparty_name = name.replace("Контрагент:", "").strip()
                        if counterparty_name and counterparty_name not in counterparties:
                            counterparties.append(counterparty_name)
                
            counterparties.sort()
            
            if self.winfo_exists() and self.filter_counterparty_combo.winfo_exists():
                self.filter_counterparty_combo['values'] = ["Все"] + counterparties
                self.filter_counterparty_combo.set("Все")
                
                print(f"DEBUG: Loaded {len(counterparties)} counterparties")
            
        except Exception as e:
            print(f"Error updating counterparties list: {e}")
    
    def _load_transfers_data(self, account_id=None, counterparty=None, date_from=None, date_to=None):
        """Загружает данные в таблицу переводов с учетом фильтров"""
        for item in self.transfers_tree.get_children():
            self.transfers_tree.delete(item)
        
        transfers = self.db.get_transfers()
        
        for transfer in transfers:
            transfer_id, date, amount, from_acc, to_acc, description = transfer
            
            if "Контрагент:" in from_acc and "Контрагент:" in to_acc:
                continue
            
            transfer_type = "Внутренний"
            counterparty_name = ""
            
            if "Контрагент:" in from_acc or "Контрагент:" in to_acc:
                transfer_type = "Внешний"
                
                if "Контрагент:" in from_acc:
                    counterparty_name = from_acc.replace("Контрагент:", "").strip()
                else:
                    counterparty_name = to_acc.replace("Контрагент:", "").strip()
            else:
                counterparty_name = ""
            
            if account_id:
                account_name = None
                for acc_id, acc_info in self.accounts_data.items():
                    if acc_id == account_id:
                        account_name = acc_info['name']
                        break
                
                if account_name and account_name not in [from_acc, to_acc]:
                    continue
            
            if counterparty and counterparty.lower() not in counterparty_name.lower():
                continue
                
            if date_from and date < date_from:
                continue
                
            if date_to and date > date_to:
                continue
            
            display_from = from_acc
            display_to = to_acc
            
            self.transfers_tree.insert("", "end", iid=transfer_id, 
                                     values=(date, transfer_type, f"{amount:.2f} ₽", 
                                             display_from, display_to, counterparty_name, description))
        
        item_count = len(self.transfers_tree.get_children())
        print(f"DEBUG: Loaded {item_count} transfers with filters")

    def _apply_filters(self, event=None):
        """Применяет фильтры к таблице переводов"""
        account_filter = self.filter_account_var.get()
        account_id = None
        if account_filter != "Все":
            for acc_id, acc_info in self.accounts_data.items():
                if acc_info['name'] == account_filter:
                    account_id = acc_id
                    break
        
        counterparty_filter = self.filter_counterparty_var.get()
        counterparty = counterparty_filter if counterparty_filter != "Все" else None
        
        date_from = self.filter_date_from.get_date() if self.filter_date_from.get_date() else None
        date_to = self.filter_date_to.get_date() if self.filter_date_to.get_date() else None
        
        self._load_transfers_data(account_id, counterparty, date_from, date_to)

    def _reset_filters(self):
        """Сбрасывает все фильтры"""
        self.filter_account_var.set("Все")
        self.filter_counterparty_var.set("Все")
        self.filter_date_from.var.set("")
        self.filter_date_to.var.set("")
        self._load_transfers_data()

    def _delete_selected_transfer(self):
        self.master.delete_selected_items_universal(
            self.transfers_tree,
            "переводы",
            lambda transfer_id: self.db.delete_transfer(transfer_id),
            refresh_callback=self._load_transfers_data,
            parent=self
        )

    def _update_transfer_type(self):
        """Обновляет видимость полей в зависимости от типа перевода"""
        if self.transfer_type.get() == "internal":
            self.internal_frame.grid()
            self.external_frame.grid_remove()
            self.title("Добавить Перевод Между Счетами")
        else:
            self.internal_frame.grid_remove()
            self.external_frame.grid()
            self.title("Добавить Внешний Перевод")

    def _add_transfer(self):
        """Добавляет перевод и возвращает True при успехе"""
        date_str = self.date_input.get_date()
        amount_str = self.amount_input.get().strip()
        description = self.description_input.get().strip()

        if not amount_str:
            messagebox.showerror("Ошибка ввода", "Пожалуйста, введите сумму.", parent=self)
            return False
            
        amount_str = amount_str.replace(',', '.')

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Сумма перевода должна быть положительной.")
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", f"Некорректная сумма: {e}", parent=self)
            return False

        print(f"DEBUG TransferDialog: transfer_type={self.transfer_type.get()}, amount={amount}")

        if self.transfer_type.get() == "internal":
            print("DEBUG: Creating INTERNAL transfer")
            from_account_name = self.from_account_var.get()
            to_account_name = self.to_account_var.get()
            
            from_account_id = None
            to_account_id = None
            for acc_id, acc_info in self.accounts_data.items():
                if acc_info['name'] == from_account_name:
                    from_account_id = acc_id
                if acc_info['name'] == to_account_name:
                    to_account_id = acc_id
            
            if from_account_id is None or to_account_id is None:
                messagebox.showerror("Ошибка ввода", "Пожалуйста, выберите оба счета.", parent=self)
                return False
                
            if from_account_id == to_account_id:
                messagebox.showerror("Ошибка ввода", "Счета 'Откуда' и 'Куда' не могут быть одинаковыми.", parent=self)
                return False

            print(f"DEBUG: Internal transfer from {from_account_id} to {to_account_id}")
            if self.db.add_transfer(date_str, amount, from_account_id, to_account_id, description):
                self.master.last_selected_date = date_str
                return True
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить перевод.", parent=self)
                return False
        else:
            print("DEBUG: Creating EXTERNAL transfer")
            account_name = self.external_account_var.get()
            counterparty = self.counterparty_input.get().strip()
            direction = self.direction_var.get()
            
            if not counterparty:
                messagebox.showerror("Ошибка ввода", "Введите имя контрагента.", parent=self)
                return False
                
            account_id = None
            for acc_id, acc_info in self.accounts_data.items():
                if acc_info['name'] == account_name:
                    account_id = acc_id
                    break
            
            if account_id is None:
                messagebox.showerror("Ошибка ввода", "Пожалуйста, выберите счет.", parent=self)
                return False

            full_description = f"Внешний перевод: {description}" if description else "Внешний перевод"
            
            print(f"DEBUG: External transfer - account: {account_id}, direction: {direction}, counterparty: {counterparty}")
            
            counterparty_account_name = f"Контрагент: {counterparty}"

            counterparty_account = self.db.get_account_by_name(counterparty_account_name)

            if not counterparty_account:
                if self.db.add_account(counterparty_account_name, "Counterparty", 0.0):
                    counterparty_account = self.db.get_account_by_name(counterparty_account_name)
                    print(f"DEBUG: Created counterparty account: {counterparty_account_name}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось создать счет контрагента.", parent=self)
                    return False
            else:
                print(f"DEBUG: Found existing counterparty account: {counterparty_account_name}")

            counterparty_account_id = counterparty_account[0]
            
            if direction == "incoming":
                result = self.db.add_transfer(date_str, amount, counterparty_account_id, account_id, full_description)
            else:
                result = self.db.add_transfer(date_str, amount, account_id, counterparty_account_id, full_description)
            
            if result:
                self.master.last_selected_date = date_str
                return True
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить внешний перевод.", parent=self)
                return False

    def _add_and_close(self):
        """Добавляет перевод и закрывает окно."""
        if self._add_transfer():            
            self._update_counterparties_list()
            self.on_close()
            
    def _add_more(self):
        """Добавляет перевод и очищает поля для следующего ввода"""
        if self._add_transfer():
            self._update_counterparties_list()
            self._already_processed = True
            self.amount_input.delete(0, tk.END)
            self.description_input.delete(0, tk.END)
            self.amount_input.focus_set()
            
    def _setup_transfers_delete_binding(self):
        """Настраивает обработку Delete для таблицы переводов"""
        def on_delete(event):
            self._delete_selected_transfer()
        
        def on_key_press(event):
            if event.keysym == 'Delete':
                selected_items = self.transfers_tree.selection()
                if selected_items:
                    self._delete_selected_transfer()
                    return "break"
        
        self.transfers_tree.bind('<Delete>', on_key_press)
        self.transfers_tree.bind('<Button-3>', lambda e: self.transfers_tree.focus())