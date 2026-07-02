import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative
from ui.widgets.calendar_widgets import TtkDateEntry  # если используете


class ReconciliationDialog(tk.Toplevel):
    """Диалог для массовой сверки балансов всех счетов."""
    
    def __init__(self, parent, db_manager, accounts_data):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager
        self.accounts_data = accounts_data
        self.account_entries = {}
        self.calculated_balances = {}
        self.difference_labels = {}
        self.total_difference_label = None
        
        self.title("Сверка Балансов")
        self.geometry("650x500")
        
        center_window_relative(self, self.parent)
        
        self.transient(parent)
        self.grab_set()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self._create_ui()
        
        self.wait_window()
    
    def _create_ui(self):
        """Создание интерфейса диалога."""
        instruction_label = ttk.Label(self, 
            text="Введите фактические балансы для всех счетов:",
            font=("TkDefaultFont", 10), justify="center")
        instruction_label.pack(pady=10)

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        header_frame = ttk.Frame(table_frame)
        header_frame.pack(fill="x")
        
        ttk.Label(header_frame, text="Счет", font=("TkDefaultFont", 10, "bold"), width=25).pack(side="left", padx=5, pady=2)
        ttk.Label(header_frame, text="Расчетный", font=("TkDefaultFont", 10, "bold"), width=12).pack(side="left", padx=5, pady=2)
        ttk.Label(header_frame, text="Фактический", font=("TkDefaultFont", 10, "bold"), width=12).pack(side="left", padx=5, pady=2)
        ttk.Label(header_frame, text="Разница", font=("TkDefaultFont", 10, "bold"), width=12).pack(side="left", padx=5, pady=2)

        ttk.Separator(table_frame, orient="horizontal").pack(fill="x", pady=2)

        canvas = tk.Canvas(table_frame, height=300)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._create_accounts_table()

        self.total_difference_label = ttk.Label(self, text="Общая разница: 0.00 ₽", 
                                               font=("TkDefaultFont", 11, "bold"))
        self.total_difference_label.pack(pady=5)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=10)

        self.reconcile_button = ttk.Button(button_frame, text="Выполнить сверку", 
                                          command=self._perform_reconciliation,
                                          state="disabled")
        self.reconcile_button.pack(side="left", padx=5)

        ttk.Button(button_frame, text="Отмена", command=self.on_close).pack(side="right", padx=5)
    
    def on_close(self):
        """Закрывает диалоговое окно."""
        self.grab_release()
        self.destroy()

    def _create_accounts_table(self):
        """Создает таблицу с полями ввода для каждого счета."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.account_entries = {}
        self.calculated_balances = {}
        self.difference_labels = {}

        sorted_accounts = sorted(self.accounts_data.items(), 
                               key=lambda x: x[1]['name'])

        for account_id, acc_info in sorted_accounts:
            row_frame = ttk.Frame(self.scrollable_frame)
            row_frame.pack(fill="x", pady=2)

            account_label = ttk.Label(row_frame, text=acc_info['name'], width=25)
            account_label.pack(side="left", padx=5)

            calculated_balance = acc_info['balance']
            self.calculated_balances[account_id] = calculated_balance
            calc_label = ttk.Label(row_frame, text=f"{calculated_balance:.2f} ₽", 
                                  width=12)
            calc_label.pack(side="left", padx=5)

            actual_var = tk.StringVar(value=f"{calculated_balance:.2f}")
            actual_entry = ttk.Entry(row_frame, textvariable=actual_var, width=12)
            actual_entry.pack(side="left", padx=5)
            
            actual_entry.bind('<KeyRelease>', lambda event, acc_id=account_id: self._on_balance_change(acc_id))
            actual_entry.bind('<FocusOut>', lambda event, acc_id=account_id: self._on_balance_change(acc_id))
            
            diff_label = ttk.Label(row_frame, text="0.00 ₽", width=12, foreground="black")
            diff_label.pack(side="left", padx=5)

            self.account_entries[account_id] = actual_entry
            self.difference_labels[account_id] = diff_label

    def _on_balance_change(self, account_id):
        """Обрабатывает изменение баланса."""
        self.after(50, lambda: self._update_balance(account_id))

    def _update_balance(self, account_id):
        """Обновляет разницу для конкретного счета."""
        try:
            actual_text = self.account_entries[account_id].get().replace(',', '.').strip()
            print(f"DEBUG: Account {account_id} - Input: '{actual_text}'")
            
            if actual_text:
                actual_balance = float(actual_text)
                calculated_balance = self.calculated_balances[account_id]
                difference = actual_balance - calculated_balance
                
                print(f"DEBUG: Account {account_id} - Actual: {actual_balance}, Calculated: {calculated_balance}, Diff: {difference}")
                
                diff_text = f"{difference:+.2f} ₽"
                if difference > 0:
                    self.difference_labels[account_id].config(text=diff_text, foreground="green")
                elif difference < 0:
                    self.difference_labels[account_id].config(text=diff_text, foreground="red")
                else:
                    self.difference_labels[account_id].config(text=diff_text, foreground="black")
            else:
                self.difference_labels[account_id].config(text="0.00 ₽", foreground="black")
                
        except (ValueError, TypeError) as e:
            print(f"DEBUG: Error processing account {account_id}: {e}")
            self.difference_labels[account_id].config(text="Ошибка", foreground="orange")

        self._update_total_difference()

    def _update_total_difference(self):
        """Обновляет общую разницу и состояние кнопки."""
        if not hasattr(self, 'total_difference_label') or not self.total_difference_label:
            return
        
        total_diff = 0.0
        has_changes = False
        
        for account_id in self.account_entries:
            try:
                actual_text = self.account_entries[account_id].get().replace(',', '.').strip()
                if not actual_text:
                    continue
                    
                actual_balance = float(actual_text)
                calculated_balance = self.calculated_balances[account_id]
                difference = actual_balance - calculated_balance
                
                total_diff += difference
                
                if difference != 0:
                    has_changes = True
                    print(f"DEBUG: Found change in account {account_id}: {difference}")
                    
            except (ValueError, TypeError):
                has_changes = True

        print(f"DEBUG: Total difference: {total_diff}, Has changes: {has_changes}")

        total_text = f"Общая разница: {total_diff:+.2f} ₽"
        if total_diff > 0:
            self.total_difference_label.config(text=total_text, foreground="green")
        elif total_diff < 0:
            self.total_difference_label.config(text=total_text, foreground="red")
        else:
            self.total_difference_label.config(text=total_text, foreground="black")

        self.reconcile_button.config(state="normal" if has_changes else "disabled")
        print(f"DEBUG: Button state: {'normal' if has_changes else 'disabled'}")

    def _perform_reconciliation(self):
        """Выполняет сверку для всех счетов с изменениями."""
        reconciliations = []
        
        for account_id in self.account_entries:
            try:
                actual_text = self.account_entries[account_id].get().replace(',', '.').strip()
                if not actual_text:
                    continue
                    
                actual_balance = float(actual_text)
                calculated_balance = self.calculated_balances[account_id]
                difference = actual_balance - calculated_balance
                
                if difference == 0:
                    continue
                
                if self._create_reconciliation_transaction(account_id, difference):
                    account_name = self.accounts_data[account_id]['name']
                    reconciliations.append({
                        'account': account_name,
                        'difference': difference
                    })
                    print(f"DEBUG: Reconciled account {account_name}: diff = {difference:.2f}")
                    
            except (ValueError, TypeError) as e:
                print(f"DEBUG: Error reconciling account {account_id}: {e}")
                continue

        if reconciliations:
            result_text = "Сверка выполнена для счетов:\n\n"
            for rec in reconciliations:
                sign = "+" if rec['difference'] > 0 else ""
                result_text += f"• {rec['account']}: {sign}{rec['difference']:.2f} ₽\n"
            
            result_text += f"\nВсего обработано: {len(reconciliations)} счетов"
            messagebox.showinfo("Сверка завершена", result_text, parent=self)
            self.result = True
            
            if hasattr(self.master, '_post_dialog_update'):
                self.master._post_dialog_update()
                
        else:
            messagebox.showinfo("Сверка", "Нет изменений для сверки", parent=self)
            self.result = False

    def _create_reconciliation_transaction(self, account_id, difference):
        """Создает корректирующую операцию для сверки баланса."""
        try:
            reconcile_category = self.db.get_category_by_name("Сверка Баланса")
            if not reconcile_category:
                print("ERROR: Reconciliation category not found")
                return False
                
            category_id = reconcile_category[0]
            
            today = datetime.now().strftime('%Y-%m-%d')
            trans_type = "корректировка"
            amount = difference
            
            description = f"Корректировка баланса. Разница: {difference:+.2f} ₽"
            
            result = self._add_correction_transaction(
                today, amount, category_id, description, account_id
            )
            
            if result:
                print(f"DEBUG: Successfully created reconciliation transaction for account {account_id}, difference: {difference:.2f}")
            else:
                print(f"DEBUG: Failed to add reconciliation transaction for account {account_id}")
                
            return result
            
        except Exception as e:
            print(f"Error in _create_reconciliation_transaction: {e}")
            return False

    def _add_correction_transaction(self, date, amount, category_id, description, account_id):
        """Добавляет корректирующую транзакцию."""
        try:
            amount = float(amount)
            
            print(f"DEBUG: Adding CORRECTION transaction: Date={date}, Amount={amount}, CatID={category_id}, Desc={description}, AccID={account_id}")
            
            result = self.db.add_transaction(
                date, amount, "корректировка", category_id, description, account_id
            )
            
            return result
            
        except Exception as e:
            print(f"Error in _add_correction_transaction: {e}")
            return False

    def apply(self):
        """Вызывается при нажатии OK - ничего не делаем, т.к. сверка уже выполнена."""
        pass

    def buttonbox(self):
        """Переопределяем кнопки - убираем стандартные OK/Cancel."""
        pass