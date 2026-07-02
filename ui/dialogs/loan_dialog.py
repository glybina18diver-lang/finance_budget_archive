import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative
from ui.widgets.calendar_widgets import TtkDateEntry

def center_window_relative(window, parent=None):
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
    
class LoanManagementWindow(tk.Toplevel):
    def __init__(self, parent, dbmanager):
        super().__init__(parent)
        self.db = dbmanager
        self.parent = parent
        self.title("Управление Займами")
        self.geometry("1000x650")

        # Фильтры
        self.current_filters = {
            "loan_type": None,
            "contact_name": None, 
            "status": None,
            "date_from": None,
            "date_to": None
        }
        self.header_menus = {}
        
        self.init_ui()
        self.load_loans()
        
        center_window_relative(self, self.parent)


        
    
        

    def init_ui(self):
        # --- Фрейм для кнопок управления ---
        button_frame = ttk.Frame(self)
        button_frame.pack(side="top", fill="x", pady=5)

        # ОСТАВЛЯЕМ ТОЛЬКО кнопку добавления займа
        self.add_loan_btn = ttk.Button(button_frame, text="Добавить заём", command=self._add_loan)
        self.add_loan_btn.pack(side="left", padx=5)

        # --- Кнопка сброса фильтров ---
        self.reset_filters_btn = ttk.Button(button_frame, text="Сбросить фильтры", command=self._reset_all_filters)
        self.reset_filters_btn.pack(side="right", padx=5)
        
        # --- Таблица займов ---
        tree_frame = ttk.Frame(self)
        tree_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        self.loans_tree = ttk.Treeview(tree_frame, columns=("Кому", "Тип", "Сумма", "Остаток", "Статус", "Дата выдачи", "Дата погашения", "Описание"), show="headings")
        self.loans_tree.heading("Кому", text="Кому")
        self.loans_tree.heading("Тип", text="Тип")
        self.loans_tree.heading("Сумма", text="Сумма")
        self.loans_tree.heading("Остаток", text="Остаток")
        self.loans_tree.heading("Статус", text="Статус")
        self.loans_tree.heading("Дата выдачи", text="Дата выдачи")
        self.loans_tree.heading("Дата погашения", text="Дата погашения")
        self.loans_tree.heading("Описание", text="Описание")
        
        # --- Настройка ширины колонок ---
        self.loans_tree.column("Кому", width=120)
        self.loans_tree.column("Тип", width=80)
        self.loans_tree.column("Сумма", width=90)
        self.loans_tree.column("Остаток", width=90)
        self.loans_tree.column("Статус", width=80)
        self.loans_tree.column("Дата выдачи", width=100)
        self.loans_tree.column("Дата погашения", width=100)
        self.loans_tree.column("Описание", width=150)
        
        self.loans_tree.pack(side="left", fill="both", expand=True)
        
        # --- Добавляем скроллбар ---
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.loans_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.loans_tree.configure(yscrollcommand=scrollbar.set)
        
        # --- Привязка к событию выбора строки ---
        self.loans_tree.bind("<<TreeviewSelect>>", self._on_loan_select)
        
        # --- Универсальная настройка управления для таблицы займов ---
        self.parent.setup_treeview_management(
            parent=self,
            treeview=self.loans_tree,
            delete_callback=self._delete_selected_loan,
            edit_callback=self._edit_loan,
            additional_commands=[
                ("💳 Добавить платеж", self._add_payment),
                ("📋 Детали займа", self._view_details),
                ("📅 Напомнить о платеже", self._set_payment_reminder)
            ]
        )
        
        # --- Создаем меню фильтров ---
        self._create_filter_menus()
        
        # --- Строка статуса ВНИЗУ окна ---
        self.status_bar = ttk.Label(self, text="Готово.", relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

    
    
    def _create_filter_menus(self):
        """Создает контекстные меню для заголовков столбцов Treeview."""
        self.header_menus = {}
        
        filterable_columns_map = {
            "Тип": self._show_type_filter_menu,
            "Кому": self._show_contact_filter_menu,
            "Статус": self._show_status_filter_menu,
            "Дата выдачи": self._show_date_filter_menu
        }

        for col_name in self.loans_tree["columns"]:
            if col_name in filterable_columns_map:
                menu = tk.Menu(self, tearoff=0)
                self.header_menus[col_name] = menu
                self.loans_tree.heading(col_name, command=filterable_columns_map[col_name])

    def _update_filter_menus_content(self):
        """Обновляет содержимое выпадающих меню фильтров."""
        # --- Меню для "Тип" ---
        if "Тип" in self.header_menus:
            menu = self.header_menus["Тип"]
            menu.delete(0, tk.END)
            menu.add_command(label="Все", command=lambda: self._apply_column_filter("Тип", None))
            menu.add_separator()
            menu.add_command(label="Выданные", command=lambda: self._apply_column_filter("Тип", "выдан"))
            menu.add_command(label="Полученные", command=lambda: self._apply_column_filter("Тип", "получен"))

        # --- Меню для "Статус" ---
        if "Статус" in self.header_menus:
            menu = self.header_menus["Статус"]
            menu.delete(0, tk.END)
            menu.add_command(label="Все", command=lambda: self._apply_column_filter("Статус", None))
            menu.add_separator()
            menu.add_command(label="Активные", command=lambda: self._apply_column_filter("Статус", "активные"))
            menu.add_command(label="Закрытые", command=lambda: self._apply_column_filter("Статус", "закрытые"))

        # --- Меню для "Кому" ---
        if "Кому" in self.header_menus:
            menu = self.header_menus["Кому"]
            menu.delete(0, tk.END)
            menu.add_command(label="Все", command=lambda: self._apply_column_filter("Кому", None))
            menu.add_separator()
            # Получаем уникальные имена контрагентов
            loans = self.db.get_loans()
            contact_names = sorted(set(loan[2] for loan in loans))  # contact_name находится на позиции 2
            for name in contact_names:
                menu.add_command(label=name, command=lambda n=name: self._apply_column_filter("Кому", n))

        # --- Меню для "Дата выдачи" ---
        if "Дата выдачи" in self.header_menus:
            menu = self.header_menus["Дата выдачи"]
            menu.delete(0, tk.END)
            today = date.today()
            this_month_start = today.replace(day=1)
            this_year_start = today.replace(month=1, day=1)
            
            menu.add_command(label="Все", command=lambda: self._apply_column_filter("Дата выдачи", None, None))
            menu.add_separator()
            menu.add_command(label="Сегодня", command=lambda: self._apply_column_filter("Дата выдачи", today.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
            menu.add_command(label="Последние 7 дней", command=lambda: self._apply_column_filter("Дата выдачи", (today - timedelta(days=7)).strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
            menu.add_command(label="Этот месяц", command=lambda: self._apply_column_filter("Дата выдачи", this_month_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
            menu.add_command(label="Этот год", command=lambda: self._apply_column_filter("Дата выдачи", this_year_start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
            menu.add_separator()
            menu.add_command(label="Выбрать диапазон...", command=self._open_date_range_dialog)

    def _show_type_filter_menu(self):
        if "Тип" in self.header_menus:
            self.header_menus["Тип"].post(self.loans_tree.winfo_pointerx(), self.loans_tree.winfo_pointery())

    def _show_status_filter_menu(self):
        if "Статус" in self.header_menus:
            self.header_menus["Статус"].post(self.loans_tree.winfo_pointerx(), self.loans_tree.winfo_pointery())

    def _show_contact_filter_menu(self):
        if "Кому" in self.header_menus:
            self.header_menus["Кому"].post(self.loans_tree.winfo_pointerx(), self.loans_tree.winfo_pointery())
        
    def _show_date_filter_menu(self):
        if "Дата выдачи" in self.header_menus:
            self.header_menus["Дата выдачи"].post(self.loans_tree.winfo_pointerx(), self.loans_tree.winfo_pointery())

    def _open_date_range_dialog(self):
        """Открывает диалог для выбора диапазона дат."""
        dialog = DateRangeDialog(self)
        if dialog.result:
            date_from_str, date_to_str = dialog.result
            self._apply_column_filter("Дата выдачи", date_from_str, date_to_str)
        else:
            self.show_status_message("Выбор диапазона дат отменен.", 1500)

    def _apply_column_filter(self, column_name, value, date_to_value=None):
        """Применяет фильтр для конкретного столбца."""
        print(f"DEBUG: Applying filter for {column_name}: {value} (to: {date_to_value})")
        
        if column_name == "Тип":
            self.current_filters["loan_type"] = value
        elif column_name == "Кому":
            self.current_filters["contact_name"] = value
        elif column_name == "Статус":
            self.current_filters["status"] = value
        elif column_name == "Дата выдачи":
            self.current_filters["date_from"] = value
            self.current_filters["date_to"] = date_to_value
            
        self.load_loans()
        self.show_status_message(f"Фильтр по '{column_name}' применен.", 1500)

    def _reset_all_filters(self):
        """Сбрасывает все примененные фильтры."""
        self.current_filters = {
            "loan_type": None,
            "contact_name": None, 
            "status": None,
            "date_from": None,
            "date_to": None
        }
        self.load_loans()
        self.show_status_message("Все фильтры сброшены.", 1500)

    def show_status_message(self, message, duration_ms=3000):
        """Показывает сообщение в строке статуса на определенное время."""
        self.status_bar.config(text=message)
        self.after(duration_ms, lambda: self.status_bar.config(text="Готово."))

    def load_loans(self):
        """Загружает займы из БД с учетом фильтров и отображает в таблице."""
        # Clear existing items
        for item in self.loans_tree.get_children():
            self.loans_tree.delete(item)
        
        # Загружаем займы с фильтрами
        loans = self.db.get_loans_with_filters(
            loan_type=self.current_filters["loan_type"],
            contact_name=self.current_filters["contact_name"],
            status=self.current_filters["status"],
            date_from=self.current_filters["date_from"],
            date_to=self.current_filters["date_to"]
        )
        
        if loans is None:
            self.show_status_message("Не удалось загрузить данные о займах.", 3000)
            return

        if loans:
            for loan in loans:
                loanid, accountid, contactname, loantype, loanamount, outstandingamount, issuedate, duedate, description = loan
                
                # Определяем статус
                status = "Активный" if float(outstandingamount) > 0 else "Закрытый"
                
                self.loans_tree.insert("", "end", iid=loanid, values=(
                    contactname, 
                    loantype, 
                    f"{float(loanamount):.2f}",
                    f"{float(outstandingamount):.2f}",
                    status,
                    issuedate, 
                    duedate or "", 
                    description or ""
                ))
        
        # Обновляем меню фильтров
        self._update_filter_menus_content()
    
    def _on_loan_select(self, event):
        """Обработчик выбора займа в таблице."""
        # Теперь этот метод не делает ничего, так как кнопки убраны
        # Но оставляем его для возможного будущего использования
        pass
        '''selected_items = self.loans_tree.selection()
        
        if selected_items:
            # Если выбрана одна запись - активируем кнопки редактирования
            if len(selected_items) == 1:
                self.edit_loan_btn.config(state="normal")
                self.add_payment_btn.config(state="normal")
                self.view_details_btn.config(state="normal")
            else:
                # Если выбрано несколько записей - деактивируем кнопки, которые работают с одной записью
                self.edit_loan_btn.config(state="disabled")
                self.add_payment_btn.config(state="disabled")
                self.view_details_btn.config(state="disabled")
        else:
            # Если ничего не выбрано - деактивируем все кнопки
            self.edit_loan_btn.config(state="disabled")
            self.add_payment_btn.config(state="disabled")
            self.view_details_btn.config(state="disabled")'''
    
    def _add_loan(self):
        """Открывает диалог добавления займа."""
        dialog = AddLoanDialog(self, self.db)
        
        if hasattr(dialog, 'result') and dialog.result:
            self.show_status_message("Заём успешно добавлен.", 3000)
            self.load_loans()
            # Обновляем данные в родительском окне
            if hasattr(self.parent, 'refresh_accounts_data'):
                self.parent.refresh_accounts_data()
            if hasattr(self.parent, '_load_all_data'):
                self.parent._load_all_data()
            if hasattr(self.parent, '_update_display'):
                self.parent._update_display()
    
    def _edit_loan(self):
        """Открывает диалог редактирования займа."""
        selected_items = self.loans_tree.selection()
        if not selected_items:
            messagebox.showinfo("Редактирование", "Выберите заём для редактирования.", parent=self)
            return
        
        if len(selected_items) > 1:
            messagebox.showinfo("Редактирование", "Выберите только один заём для редактирования.", parent=self)
            return

        loan_id = int(selected_items[0])
        
        # Получаем полные данные займа из БД
        full_loan_data = self.db.get_loan_by_id(loan_id)
        if not full_loan_data:
            messagebox.showerror("Ошибка", "Не удалось получить данные займа.", parent=self)
            return
        
        # Получаем данные счетов из родительского окна
        accounts_data = getattr(self.parent, 'accounts_data', {})
        
        # Формируем данные для диалога
        loan_data_for_dialog = (
            full_loan_data[2],  # contact_name
            full_loan_data[3],  # loan_type
            full_loan_data[4],  # loan_amount
            full_loan_data[5],  # outstanding_amount
            full_loan_data[6],  # issue_date
            full_loan_data[7],  # due_date
            full_loan_data[8],  # description
            full_loan_data[1]   # loan_account_id
        )
        
        dialog = EditLoanDialog(self, self.db, loan_id, loan_data_for_dialog)
        
        if hasattr(dialog, 'result') and dialog.result:
            self.show_status_message("Заём успешно обновлен.", 3000)
            self.load_loans()
            # Обновляем данные в родительском окне
            if hasattr(self.parent, 'refresh_accounts_data'):
                self.parent.refresh_accounts_data()
            if hasattr(self.parent, '_load_all_data'):
                self.parent._load_all_data()
            if hasattr(self.parent, '_update_display'):
                self.parent._update_display()     # И наконец обновляем отображение
        
    def _add_payment(self):
        """Открывает диалог добавления платежа."""
        selected_items = self.loans_tree.selection()
        if not selected_items:
            messagebox.showinfo("Платёж", "Выберите заём для добавления платежа.", parent=self)
            return
        
        if len(selected_items) > 1:
            messagebox.showinfo("Платёж", "Выберите только один заём для добавления платежа.", parent=self)
            return

        loan_id = int(selected_items[0])
        
        # Получаем полные данные займа из БД
        full_loan_data = self.db.get_loan_by_id(loan_id)
        if not full_loan_data:
            messagebox.showerror("Ошибка", "Не удалось получить данные займа.", parent=self)
            return
        
        # Получаем данные счетов из родительского окна (ОБНОВЛЕННЫЕ)
        self.parent.refresh_accounts_data()  # <-- ДОБАВИТЬ ЭТУ СТРОКУ
        accounts_data = getattr(self.parent, 'accounts_data', {})
        
        if not accounts_data:
            messagebox.showerror("Ошибка", "Не удалось получить данные счетов.", parent=self)
            return
        
        # Формируем данные для диалога
        # full_loan_data: (id, account_id, contact_name, loan_type, loan_amount, outstanding_amount, issue_date, due_date, description, transaction_id)
        loan_data_for_dialog = (
            full_loan_data[2],  # contact_name
            full_loan_data[3],  # loan_type
            full_loan_data[4],  # loan_amount
            full_loan_data[5],  # outstanding_amount
            full_loan_data[6],  # issue_date
            full_loan_data[7],  # due_date
            full_loan_data[8],  # description
            full_loan_data[1]   # loan_account_id
        )
        
        dialog = AddPaymentDialog(self, self.db, loan_id, loan_data_for_dialog, accounts_data)
        
        if hasattr(dialog, 'result') and dialog.result:
            self.show_status_message("Платёж успешно добавлен.", 3000)
            self.load_loans()
            # Обновляем данные в родительском окне
            if hasattr(self.parent, 'refresh_accounts_data'):
                self.parent.refresh_accounts_data()
            if hasattr(self.parent, '_load_all_data'):
                self.parent._load_all_data()
            if hasattr(self.parent, '_update_display'):
                self.parent._update_display()

    def _view_details(self):
        """Открывает диалог просмотра деталей займа с историей платежей."""
        selected_item = self.loans_tree.selection()
        if not selected_item:
            messagebox.showinfo("Детали", "Выберите заём для просмотра деталей.", parent=self)
            return
        
        loan_id = int(selected_item[0])
        
        # Получаем данные из БД для гарантии правильных типов
        full_loan_data = self.db.get_loan_by_id(loan_id)
        if not full_loan_data:
            messagebox.showerror("Ошибка", "Не удалось получить данные займа.", parent=self)
            return
        
        contact_name, loan_type, loan_amount, outstanding_amount, issue_date, due_date, description, loan_account_id = (
            full_loan_data[2], full_loan_data[3], full_loan_data[4], full_loan_data[5], 
            full_loan_data[6], full_loan_data[7], full_loan_data[8], full_loan_data[1]
        )
        
        # Получаем имя счета займа
        accounts_data = getattr(self.parent, 'accounts_data', {})
        loan_account_name = next((info['name'] for acc_id, info in accounts_data.items() if acc_id == loan_account_id), "Неизвестный счет")
        
        # Создаем окно для деталей
        details_window = tk.Toplevel(self)
        details_window.title(f"Детали займа: {contact_name}")
        details_window.geometry("800x600")
        details_window.transient(self)
        details_window.grab_set()
        
        # Основная информация о займе
        info_frame = ttk.LabelFrame(details_window, text="Информация о займе")
        info_frame.pack(fill="x", padx=10, pady=5)
        
        info_text = f"""Контрагент: {contact_name}
    Тип займа: {loan_type}
    Счёт займа: {loan_account_name}
    Общая сумма: {loan_amount:.2f} ₽
    Остаток долга: {outstanding_amount:.2f} ₽
    Дата выдачи: {issue_date}"""
        
        if due_date:
            info_text += f"\nДата погашения: {due_date}"
        if description:
            info_text += f"\nОписание: {description}"
        
        ttk.Label(info_frame, text=info_text, justify="left").pack(anchor="w", padx=10, pady=10)
        
        # История платежей
        payments_frame = ttk.LabelFrame(details_window, text="История платежей")
        payments_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Таблица платежей
        payments_tree = ttk.Treeview(payments_frame, columns=("ID", "Дата", "Сумма", "Описание"), show="headings", height=10)
        payments_tree.heading("ID", text="ID")
        payments_tree.heading("Дата", text="Дата")
        payments_tree.heading("Сумма", text="Сумма")
        payments_tree.heading("Описание", text="Описание")
        
        payments_tree.column("ID", width=50)
        payments_tree.column("Дата", width=100)
        payments_tree.column("Сумма", width=100)
        payments_tree.column("Описание", width=400)
        
        payments_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Скроллбар для таблицы платежей
        scrollbar = ttk.Scrollbar(payments_frame, orient="vertical", command=payments_tree.yview)
        scrollbar.pack(side="right", fill="y")
        payments_tree.configure(yscrollcommand=scrollbar.set)
        
        # === ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ ПЛАТЕЖАМИ ===
        
        def refresh_payments():
            """Обновляет список платежей."""
            for item in payments_tree.get_children():
                payments_tree.delete(item)
            
            payments = self.db.get_loan_payments(loan_id)
            total_paid = 0.0
            
            if payments:
                for payment in payments:
                    payment_id, payment_date, payment_amount, payment_description = payment
                    payment_amount_float = float(payment_amount) if payment_amount is not None else 0.0
                    
                    payments_tree.insert("", "end", values=(
                        payment_id,
                        payment_date, 
                        f"{payment_amount_float:.2f} ₽",
                        payment_description or ""
                    ))
                    total_paid += payment_amount_float
            
            # Обновляем информацию об остатке
            new_outstanding = float(loan_amount) - total_paid
            outstanding_label.config(text=f"Остаток долга: {new_outstanding:.2f} ₽")
            total_paid_label.config(text=f"Всего выплачено: {total_paid:.2f} ₽")
        
        def delete_selected_payment():
            """Удаляет выбранный платеж."""
            selected_payment = payments_tree.selection()
            if not selected_payment:
                messagebox.showinfo("Удаление", "Выберите платеж для удаления.", parent=details_window)
                return
            
            payment_id = int(payments_tree.item(selected_payment[0], 'values')[0])
            payment_date = payments_tree.item(selected_payment[0], 'values')[1]
            payment_amount = float(payments_tree.item(selected_payment[0], 'values')[2].replace(' ₽', ''))
            
            if not messagebox.askyesno("Подтверждение удаления", 
                                       f"Вы уверены, что хотите удалить платеж от {payment_date} на сумму {payment_amount:.2f} ₽?\n"
                                       f"Балансы счетов будут восстановлены.",
                                       parent=details_window):
                return
            
            if self.db.delete_loan_payment(payment_id):
                messagebox.showinfo("Успех", "Платёж успешно удален.", parent=details_window)
                # Обновляем данные
                refresh_payments()
                if hasattr(self.parent, 'refresh_accounts_data'):
                    self.parent.refresh_accounts_data()
                if hasattr(self.parent, '_load_all_data'):
                    self.parent._load_all_data()
                if hasattr(self.parent, '_update_display'):
                    self.parent._update_display()
                self.load_loans()  # Обновляем список займов
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить платёж.", parent=details_window)
        
        def print_payment_receipt():
            """Печатает квитанцию об оплате"""
            selected_item = payments_tree.selection()
            if selected_item:
                payment_id = int(payments_tree.item(selected_item[0], 'values')[0])
                messagebox.showinfo("Печать", f"Печать квитанции для платежа {payment_id}", parent=details_window)
        
        # === УНИВЕРСАЛЬНАЯ НАСТРОЙКА УПРАВЛЕНИЯ ДЛЯ ТАБЛИЦЫ ПЛАТЕЖЕЙ ===
        self.parent.setup_treeview_management(
            parent=details_window,
            treeview=payments_tree,
            delete_callback=delete_selected_payment,
            edit_callback=None,  # Платежи обычно не редактируют
            additional_commands=[
                ("🖨️ Печать квитанции", print_payment_receipt)
            ]
        )
        
        # Итоговая информация
        total_frame = ttk.Frame(details_window)
        total_frame.pack(fill="x", padx=10, pady=5)
        
        total_paid_label = ttk.Label(total_frame, text="Всего выплачено: 0.00 ₽", 
                                    font=("TkDefaultFont", 10, "bold"))
        total_paid_label.pack(side="left")
        
        outstanding_label = ttk.Label(total_frame, text=f"Остаток: {outstanding_amount:.2f} ₽", 
                                     font=("TkDefaultFont", 10, "bold"))
        outstanding_label.pack(side="right")
        
        # Кнопка закрытия
        close_button = ttk.Button(details_window, text="Закрыть", command=details_window.destroy)
        close_button.pack(pady=10)
        
        # === ЗАГРУЖАЕМ ДАННЫЕ ===
        refresh_payments()
        payments_tree.focus_set()

    def _delete_selected_loan(self):
        """Удаляет выбранные займы используя универсальный метод"""
        self.parent.delete_selected_items_universal(
            self.loans_tree,                   # позиционный
            "займы",                           # позиционный
            lambda loan_id: self._delete_loan_by_id(loan_id),  # позиционный
            refresh_callback=self.load_loans,              # именованный
            additional_refresh_callbacks=[self._refresh_parent_data],  # именованный
            parent=self                         # именованный
        )
            
    def _delete_loan_by_id(self, loan_id):
        """Удаляет займ по ID и возвращает True при успехе"""
        try:
            # Получаем данные займа
            full_loan_data = self.db.get_loan_by_id(loan_id)
            if not full_loan_data:
                return False

            contact_name, loan_type, loan_amount, outstanding_amount = full_loan_data[2], full_loan_data[3], float(full_loan_data[4]), float(full_loan_data[5])
            account_id = full_loan_data[1]

            # НАХОДИМ СЧЕТ КОНТРАГЕНТА
            counterparty_account_name = f"Контрагент: {contact_name}"
            counterparty_account = self.db.get_account_by_name(counterparty_account_name)
            
            if not counterparty_account:
                print(f"DEBUG: Counterparty account not found: {counterparty_account_name}")
                return False
                
            counterparty_account_id = counterparty_account[0]

            print(f"DEBUG DELETE LOAN:")
            print(f"  - Loan amount: {loan_amount}")
            print(f"  - Outstanding amount: {outstanding_amount}")

            # 1. СНАЧАЛА УДАЛЯЕМ ВСЕ ПЛАТЕЖИ (они откатят свои балансы)
            payments = self.db.get_loan_payments(loan_id)
            print(f"DEBUG: Found {len(payments)} payments to delete")
            
            for payment in payments:
                payment_id = payment[0]
                print(f"DEBUG: Deleting payment {payment_id}")
                success = self.db.delete_loan_payment(payment_id)
                if not success:
                    print(f"DEBUG: Failed to delete payment {payment_id}")
                    return False

            # 2. ПОТОМ УДАЛЯЕМ ЗАЙМ (откатываем полную сумму)
            if loan_type == "получен":
                adjustment_my_account = -loan_amount      # Сбер: -7000 (полная сумма)
                adjustment_counterparty = loan_amount     # Наташа: +7000 (полная сумма)
            else:  # "выдан"
                adjustment_my_account = loan_amount       # Сбер: +7000 (полная сумма)
                adjustment_counterparty = -loan_amount    # Наташа: -7000 (полная сумма)
            
            print(f"DEBUG: Deleting loan - full amount: {loan_amount}")
            
            # Восстанавливаем балансы ОБОИХ счетов (полная сумма займа)
            success1 = self.db.update_account_balance(account_id, adjustment_my_account)
            success2 = self.db.update_account_balance(counterparty_account_id, adjustment_counterparty)
            
            if not (success1 and success2):
                print(f"DEBUG: Failed to restore balances")
                return False

            # 3. УДАЛЯЕМ ЗАЙМ ИЗ ТАБЛИЦЫ
            return self.db._execute_query("DELETE FROM loans WHERE id = ?", (loan_id,))
            
        except Exception as e:
            print(f"Error deleting loan {loan_id}: {e}")
            return False

    def _refresh_parent_data(self):
        """Обновляет данные в родительском окне"""
        if hasattr(self.parent, 'refresh_accounts_data'):
            self.parent.refresh_accounts_data()
        if hasattr(self.parent, '_load_all_data'):
            self.parent._load_all_data()
        if hasattr(self.parent, '_update_display'):
            self.parent._update_display()

    def _set_payment_reminder(self):
        """Устанавливает напоминание о платеже"""
        """Заглушка для будущей функции"""
        messagebox.showinfo("В разработке", "Данная функция в разработке", parent=self)

    def _print_payment_receipt(self, payments_tree):
        """Печатает квитанцию об оплате"""
        selected_item = payments_tree.selection()
        if selected_item:
            payment_id = int(payments_tree.item(selected_item[0], 'values')[0])
            messagebox.showinfo("Печать", f"Печать квитанции для платежа {payment_id}", parent=self)
    
    
 
class SimpleDateEntry(ttk.Frame):
    """Упрощенный виджет для ввода даты без циклического импорта."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.var = tk.StringVar(self)
        
        # Entry для отображения даты
        self.entry = ttk.Entry(self, textvariable=self.var, width=12)
        self.entry.pack(side="left", fill="x", expand=True)
        
        # Устанавливаем текущую дату по умолчанию
        self.var.set(date.today().strftime('%Y-%m-%d'))

    def get_date(self):
        return self.var.get()

    def set_date(self, date_str):
        self.var.set(date_str)
        
class AddLoanDialog:
    """Диалог для добавления нового займа."""
    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db = db_manager
        self.last_selected_date = getattr(parent, 'last_selected_date', date.today().strftime('%Y-%m-%d'))
        self.result = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Добавить заём")
        self.dialog.geometry("350x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Центрирование окна
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_reqheight()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        self.setup_bindings()
        
    def create_widgets(self):
        """Создает виджеты в диалоговом окне."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Счет
        ttk.Label(main_frame, text="Счёт:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Получаем счета из БД
        accounts = self.db.get_accounts()
        account_names = [account[1] for account in accounts]  # account[1] - имя счета
        
        self.account_var = tk.StringVar()
        self.account_combo = ttk.Combobox(main_frame, textvariable=self.account_var, 
                                          values=account_names, state="readonly")
        if account_names:
            self.account_combo.set(account_names[0])
        self.account_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Остальной код без изменений...
        # Контрагент
        ttk.Label(main_frame, text="Контрагент:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.contact_input = ttk.Entry(main_frame)
        self.contact_input.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Тип займа
        ttk.Label(main_frame, text="Тип займа:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.loan_type_var = tk.StringVar(value="выдан")
        self.loan_type_combo = ttk.Combobox(main_frame, textvariable=self.loan_type_var, 
                                           values=["выдан", "получен"], state="readonly")
        self.loan_type_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        # Сумма займа
        ttk.Label(main_frame, text="Сумма займа:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.amount_input = ttk.Entry(main_frame)
        self.amount_input.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        # Дата выдачи
        ttk.Label(main_frame, text="Дата выдачи:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.issue_date_input = SimpleDateEntry(main_frame)
        self.issue_date_input.set_date(self.last_selected_date)
        self.issue_date_input.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        
        # Дата погашения
        ttk.Label(main_frame, text="Дата погашения:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.due_date_input = SimpleDateEntry(main_frame)
        self.due_date_input.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        
        # Описание
        ttk.Label(main_frame, text="Описание:").grid(row=6, column=0, padx=5, pady=5, sticky="w")
        self.description_input = ttk.Entry(main_frame)
        self.description_input.grid(row=6, column=1, padx=5, pady=5, sticky="ew")
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=15)
        
        ttk.Button(button_frame, text="Добавить", command=self.on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        main_frame.grid_columnconfigure(1, weight=1)
    
    def setup_bindings(self):
        """Настройка привязок клавиш."""
        self.dialog.bind('<Return>', lambda e: self.on_add())
        self.dialog.bind('<Escape>', lambda e: self.on_cancel())
        
    def on_add(self):
        """Обработчик кнопки Добавить."""
        account_name = self.account_var.get()
        contact_name = self.contact_input.get().strip()
        loan_type = self.loan_type_combo.get()
        amount_str = self.amount_input.get().strip()
        issue_date = self.issue_date_input.get_date()
        due_date = self.due_date_input.get_date()
        description = self.description_input.get().strip()

        # Валидация данных
        if not all([account_name, contact_name, loan_type, amount_str, issue_date]):
            messagebox.showerror("Ошибка ввода", "Пожалуйста, заполните все обязательные поля.", parent=self.dialog)
            return
            
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Сумма займа должна быть положительной.")
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Некорректная сумма займа.", parent=self.dialog)
            return

        if due_date and issue_date:
            try:
                issue_date_dt = datetime.strptime(issue_date, '%Y-%m-%d').date()
                due_date_dt = datetime.strptime(due_date, '%Y-%m-%d').date()
                if issue_date_dt > due_date_dt:
                    messagebox.showerror("Ошибка ввода", "Дата погашения не может быть раньше даты выдачи.", parent=self.dialog)
                    return
            except ValueError:
                messagebox.showerror("Ошибка ввода", "Некорректный формат даты.", parent=self.dialog)
                return

        # Получаем ID счета по имени из БД
        account_id = None
        accounts = self.db.get_accounts()
        for account in accounts:
            if account[1] == account_name:  # account[1] - имя счета
                account_id = account[0]     # account[0] - ID счета
                break
                
        if account_id is None:
            messagebox.showerror("Ошибка", "Не выбран счет.", parent=self.dialog)
            return
            
        # Добавление займа в базу данных
        if self.db.add_loan(account_id, contact_name, loan_type, amount, issue_date, due_date, description):
            messagebox.showinfo("Успех", "Заём успешно добавлен", parent=self.dialog)
            self.result = True
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить заём.", parent=self.dialog)
        
    def on_cancel(self):
        """Обработчик кнопки Отмена."""
        self.dialog.destroy()


class AddPaymentDialog:
    """Диалог для добавления платежа по займу."""
    def __init__(self, parent, db, loan_id, loan_data, accounts_data):
        self.parent = parent
        self.db = db
        self.loan_id = loan_id
        self.loan_data = loan_data
        self.accounts_data = accounts_data
        self.last_selected_date = getattr(parent, 'last_selected_date', datetime.date.today().strftime('%Y-%m-%d'))
        self.result = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Добавить платёж по займу")
        self.dialog.geometry("450x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Центрирование окна
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_reqheight()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        self.setup_bindings()
        
    def create_widgets(self):
        """Создает виджеты в диалоговом окне."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Информация о займе
        info_frame = ttk.LabelFrame(main_frame, text="Информация о займе")
        info_frame.pack(fill="x", padx=5, pady=5)
        
        contact_name, loan_type, loan_amount, outstanding_amount, issue_date, due_date, description, loan_account_id = self.loan_data
        
        ttk.Label(info_frame, text=f"Контрагент: {contact_name}").pack(anchor="w", padx=5, pady=2)
        ttk.Label(info_frame, text=f"Тип: {loan_type}").pack(anchor="w", padx=5, pady=2)
        ttk.Label(info_frame, text=f"Сумма займа: {loan_amount:.2f} ₽").pack(anchor="w", padx=5, pady=2)
        ttk.Label(info_frame, text=f"Остаток долга: {outstanding_amount:.2f} ₽", 
                 font=("TkDefaultFont", 9, "bold")).pack(anchor="w", padx=5, pady=2)

        # Поля для ввода платежа
        form_frame = ttk.LabelFrame(main_frame, text="Данные платежа")
        form_frame.pack(fill="x", padx=5, pady=5)

        account_names = [acc_info['name'] for acc_id, acc_info in self.accounts_data.items()]
        contact_name, loan_type, loan_amount, outstanding_amount, issue_date, due_date, description, loan_account_id = self.loan_data
        
        if loan_type == "выдан":
            # Для ВЫДАННЫХ займов
            ttk.Label(form_frame, text="От кого (контрагент):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
            ttk.Label(form_frame, text=contact_name, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=1, padx=5, pady=2, sticky="w")
            
            ttk.Label(form_frame, text="На наш счёт:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
            loan_account_name = next((info['name'] for acc_id, info in self.accounts_data.items() if acc_id == loan_account_id), "")
            self.to_account_var = tk.StringVar(value=loan_account_name)
            ttk.Label(form_frame, text=loan_account_name, font=("TkDefaultFont", 9, "bold")).grid(row=1, column=1, padx=5, pady=2, sticky="w")
            
            counterparty_account_name = f"Контрагент: {contact_name}"
            self.from_account_var = tk.StringVar(value=counterparty_account_name)
            
        else:  # "получен"
            # Для ПОЛУЧЕННЫХ займов
            ttk.Label(form_frame, text="С нашего счёта:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
            self.from_account_var = tk.StringVar()
            self.from_account_combo = ttk.Combobox(form_frame, textvariable=self.from_account_var, 
                                                  values=account_names, state="readonly")
            if account_names:
                self.from_account_combo.set(account_names[0])
            self.from_account_combo.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            
            ttk.Label(form_frame, text="Кому (контрагент):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
            ttk.Label(form_frame, text=contact_name, font=("TkDefaultFont", 9, "bold")).grid(row=1, column=1, padx=5, pady=2, sticky="w")
            
            counterparty_account_name = f"Контрагент: {contact_name}"
            self.to_account_var = tk.StringVar(value=counterparty_account_name)

        # Дата платежа
        ttk.Label(form_frame, text="Дата платежа:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.date_input = SimpleDateEntry(form_frame)
        self.date_input.set_date(self.last_selected_date)
        self.date_input.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        # Сумма платежа
        ttk.Label(form_frame, text="Сумма платежа:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.amount_input = ttk.Entry(form_frame)
        self.amount_input.grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        
        # Описание
        ttk.Label(form_frame, text="Описание:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.description_input = ttk.Entry(form_frame)
        self.description_input.grid(row=4, column=1, padx=5, pady=2, sticky="ew")

        # Подсказка
        if loan_type == "выдан":
            hint_text = "💡 ВЫДАННЫЙ заём: получаем возврат денег от заемщика"
        else:
            hint_text = "💡 ПОЛУЧЕННЫЙ заём: возвращаем деньги кредитору"
        
        ttk.Label(form_frame, text=hint_text, font=("TkDefaultFont", 8), foreground="blue").grid(
            row=5, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        form_frame.grid_columnconfigure(1, weight=1)
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Добавить", command=self.on_add).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
    def setup_bindings(self):
        """Настройка привязок клавиш."""
        self.dialog.bind('<Return>', lambda e: self.on_add())
        self.dialog.bind('<Escape>', lambda e: self.on_cancel())
        
    def validate(self):
        """Проверяет корректность введенных данных."""
        from_account_name = self.from_account_var.get()
        payment_date = self.date_input.get_date()
        amount_str = self.amount_input.get().strip()

        if not from_account_name or not payment_date or not amount_str:
            messagebox.showerror("Ошибка ввода", "Заполните все обязательные поля.", parent=self.dialog)
            return False

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Сумма должна быть положительной.")
            
            # Проверяем, что сумма платежа не превышает остаток долга
            outstanding_amount = self.loan_data[3]
            if amount > outstanding_amount:
                messagebox.showerror("Ошибка", 
                                   f"Сумма платежа ({amount:.2f} ₽) превышает остаток долга ({outstanding_amount:.2f} ₽).", 
                                   parent=self.dialog)
                return False
                
        except ValueError as e:
            messagebox.showerror("Ошибка ввода", f"Некорректная сумма: {e}", parent=self.dialog)
            return False

        return True
        
    def on_add(self):
        """Обработчик кнопки Добавить."""
        if not self.validate():
            return
            
        from_account_name = self.from_account_var.get()
        payment_date = self.date_input.get_date()
        amount_str = self.amount_input.get().strip()
        description = self.description_input.get().strip()

        try:
            amount = float(amount_str)
            
            # НАХОДИМ ID СЧЕТОВ
            contact_name, loan_type, loan_amount, outstanding_amount, issue_date, due_date, description_loan, loan_account_id = self.loan_data
            
            from_account_id = None
            to_account_id = None
            
            # ДЛЯ ПОЛУЧЕННОГО ЗАЙМА
            if loan_type == "получен":
                # Платеж: с моего счета → контрагенту
                for acc_id, acc_info in self.accounts_data.items():
                    if acc_info['name'] == from_account_name:
                        from_account_id = acc_id
                        break
                
                # Счет контрагента
                counterparty_account_name = f"Контрагент: {contact_name}"
                counterparty_account = self.db.get_account_by_name(counterparty_account_name)
                
                if not counterparty_account:
                    # Создаем виртуальный счет для контрагента если его нет
                    if self.db.add_account(counterparty_account_name, "Counterparty", 0.0):
                        counterparty_account = self.db.get_account_by_name(counterparty_account_name)
                
                if counterparty_account:
                    to_account_id = counterparty_account[0]
                else:
                    messagebox.showerror("Ошибка", f"Не удалось найти или создать счет для контрагента '{contact_name}'.", parent=self.dialog)
                    return
            
            # ДЛЯ ВЫДАННОГО ЗАЙМА  
            else:  # "выдан"
                # Платеж: с контрагента → на мой счет
                # Счет контрагента
                counterparty_account_name = f"Контрагент: {contact_name}"
                counterparty_account = self.db.get_account_by_name(counterparty_account_name)
                
                if not counterparty_account:
                    # Создаем виртуальный счет для контрагента если его нет
                    if self.db.add_account(counterparty_account_name, "Counterparty", 0.0):
                        counterparty_account = self.db.get_account_by_name(counterparty_account_name)
                
                if counterparty_account:
                    from_account_id = counterparty_account[0]
                else:
                    messagebox.showerror("Ошибка", f"Не удалось найти или создать счет для контрагента '{contact_name}'.", parent=self.dialog)
                    return
                
                # Мой счет (счет займа)
                to_account_id = loan_account_id
            
            if from_account_id is None or to_account_id is None:
                messagebox.showerror("Ошибка", "Не удалось определить счета для платежа.", parent=self.dialog)
                return
            
            if self.db.add_loan_payment(self.loan_id, from_account_id, to_account_id, payment_date, amount, description):
                messagebox.showinfo("Успех", "Платёж успешно добавлен", parent=self.dialog)
                self.result = True
                self.dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить платёж.", parent=self.dialog)
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при добавлении платежа: {e}", parent=self.dialog)
            
    def on_cancel(self):
        """Обработчик кнопки Отмена."""
        self.dialog.destroy()


class EditLoanDialog:
    """Диалог для редактирования займа."""
    def __init__(self, parent, db, loan_id, loan_data):
        self.parent = parent
        self.db = db
        self.loan_id = loan_id
        self.loan_data = loan_data
        self.result = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Редактировать заём")
        self.dialog.geometry("400x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Центрирование окна
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_reqheight()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        self.setup_bindings()
        
    def create_widgets(self):
        """Создает виджеты в диалоговом окне."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Информация о займе (только для чтения)
        info_frame = ttk.LabelFrame(main_frame, text="Информация о займе (не редактируется)")
        info_frame.pack(fill="x", padx=5, pady=5)
        
        contact_name, loan_type, loan_amount, outstanding_amount, issue_date, due_date, description, loan_account_id = self.loan_data
        
        ttk.Label(info_frame, text=f"Тип: {loan_type}").pack(anchor="w", padx=5, pady=2)
        ttk.Label(info_frame, text=f"Сумма: {loan_amount:.2f} ₽").pack(anchor="w", padx=5, pady=2)
        ttk.Label(info_frame, text=f"Остаток: {outstanding_amount:.2f} ₽").pack(anchor="w", padx=5, pady=2)
        ttk.Label(info_frame, text=f"Дата выдачи: {issue_date}").pack(anchor="w", padx=5, pady=2)

        # Поля для редактирования
        form_frame = ttk.LabelFrame(main_frame, text="Редактируемые поля")
        form_frame.pack(fill="x", padx=5, pady=5)

        # Контрагент
        ttk.Label(form_frame, text="Контрагент:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.contact_input = ttk.Entry(form_frame)
        self.contact_input.insert(0, contact_name)
        self.contact_input.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        
        # Дата погашения
        ttk.Label(form_frame, text="Дата погашения:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.due_date_input = SimpleDateEntry(form_frame)
        if due_date:
            self.due_date_input.set_date(due_date)
        self.due_date_input.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        # Описание
        ttk.Label(form_frame, text="Описание:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.description_input = ttk.Entry(form_frame)
        if description:
            self.description_input.insert(0, description)
        self.description_input.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        # Подсказка
        ttk.Label(form_frame, 
                 text="💡 Можно изменить только контрагента, дату погашения и описание",
                 font=("TkDefaultFont", 8), foreground="gray").grid(
                 row=3, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        form_frame.grid_columnconfigure(1, weight=1)
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Сохранить", command=self.on_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
    def setup_bindings(self):
        """Настройка привязок клавиш."""
        self.dialog.bind('<Return>', lambda e: self.on_save())
        self.dialog.bind('<Escape>', lambda e: self.on_cancel())
        
    def validate(self):
        """Проверяет корректность введенных данных."""
        contact_name = self.contact_input.get().strip()
        due_date = self.due_date_input.get_date()
        
        if not contact_name:
            messagebox.showerror("Ошибка ввода", "Введите имя контрагента.", parent=self.dialog)
            return False
        
        # Проверяем дату погашения (если указана)
        if due_date:
            issue_date = self.loan_data[4]
            try:
                due_date_dt = datetime.datetime.strptime(due_date, '%Y-%m-%d').date()
                issue_date_dt = datetime.datetime.strptime(issue_date, '%Y-%m-%d').date()
                if due_date_dt < issue_date_dt:
                    messagebox.showerror("Ошибка ввода", "Дата погашения не может быть раньше даты выдачи.", parent=self.dialog)
                    return False
            except ValueError:
                messagebox.showerror("Ошибка ввода", "Некорректный формат даты погашения.", parent=self.dialog)
                return False

        return True
        
    def on_save(self):
        """Обработчик кнопки Сохранить."""
        if not self.validate():
            return
            
        contact_name = self.contact_input.get().strip()
        due_date = self.due_date_input.get_date()
        description = self.description_input.get().strip()

        # Если дата погашения пустая, передаем None
        due_date_value = due_date if due_date else None
        # Если описание пустое, передаем None
        description_value = description if description else None

        if self.db.update_loan(self.loan_id, contact_name, due_date_value, description_value):
            messagebox.showinfo("Успех", "Заём успешно обновлен", parent=self.dialog)
            self.result = True
            self.dialog.destroy()
        else:
            messagebox.showerror("Ошибка", "Не удалось обновить заём.", parent=self.dialog)
            
    def on_cancel(self):
        """Обработчик кнопки Отмена."""
        self.dialog.destroy()


class DateRangeDialog:
    """Диалог для выбора диапазона дат с помощью TtkDateEntry."""
    def __init__(self, parent):
        self.parent = parent
        self.date_from_str = None
        self.date_to_str = None
        self.result = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Выбрать диапазон дат")
        self.dialog.geometry("300x150")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Центрирование окна
        self.dialog.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.dialog.winfo_reqwidth()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.dialog.winfo_reqheight()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        self.setup_bindings()
        
    def create_widgets(self):
        """Создает виджеты в диалоговом окне."""
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Дата от
        ttk.Label(main_frame, text="Дата от:").grid(row=0, column=0, padx=5, pady=8, sticky="w")
        self.date_from_entry = SimpleDateEntry(main_frame)
        self.date_from_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")
        
        # Дата до
        ttk.Label(main_frame, text="Дата до:").grid(row=1, column=0, padx=5, pady=8, sticky="w")
        self.date_to_entry = SimpleDateEntry(main_frame)
        self.date_to_entry.grid(row=1, column=1, padx=5, pady=8, sticky="ew")
        
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="ОК", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
    def setup_bindings(self):
        """Настройка привязок клавиш."""
        self.dialog.bind('<Return>', lambda e: self.on_ok())
        self.dialog.bind('<Escape>', lambda e: self.on_cancel())
        
    def on_ok(self):
        """Обработчик кнопки ОК."""
        self.date_from_str = self.date_from_entry.get_date() if self.date_from_entry.get_date() else None
        self.date_to_str = self.date_to_entry.get_date() if self.date_to_entry.get_date() else None

        if self.date_from_str and self.date_to_str:
            if self.date_from_str > self.date_to_str:
                messagebox.showerror("Ошибка ввода", "'Дата от' не может быть позже 'Дата до'.", parent=self.dialog)
                return
        
        self.result = (self.date_from_str, self.date_to_str)
        self.dialog.destroy()
        
    def on_cancel(self):
        """Обработчик кнопки Отмена."""
        self.dialog.destroy()# рр