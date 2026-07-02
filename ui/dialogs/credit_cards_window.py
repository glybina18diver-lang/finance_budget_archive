import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative
from ui.widgets.calendar_widgets import TtkDateEntry  # если используете


class CreditCardsWindow(tk.Toplevel):
    """Окно управления кредитными картами."""
    
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager
        
        self.title("Кредитные карты")
        self.geometry("900x600")
        
        center_window_relative(self, parent)
        
        self._create_ui()
        self._load_data()
        
    def _create_ui(self):
        """Создает интерфейс."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        summary_frame = ttk.LabelFrame(main_frame, text="Общая сводка", padding="10")
        summary_frame.pack(fill="x", pady=(0, 10))
        
        self.summary_label = ttk.Label(summary_frame, text="", font=("Arial", 10))
        self.summary_label.pack()
        
        table_frame = ttk.LabelFrame(main_frame, text="Кредитные карты", padding="10")
        table_frame.pack(fill="both", expand=True)
        
        columns = ("Название", "Баланс", "Лимит", "Доступно", "Использование", "День платежа", "Мин. платеж")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        
        self.tree.heading("Название", text="Название")
        self.tree.heading("Баланс", text="Баланс")
        self.tree.heading("Лимит", text="Лимит")
        self.tree.heading("Доступно", text="Доступно")
        self.tree.heading("Использование", text="Использование")
        self.tree.heading("День платежа", text="День платежа")
        self.tree.heading("Мин. платеж", text="Мин. платеж")
        
        self.tree.column("Название", width=150)
        self.tree.column("Баланс", width=100)
        self.tree.column("Лимит", width=100)
        self.tree.column("Доступно", width=100)
        self.tree.column("Использование", width=100)
        self.tree.column("День платежа", width=100)
        self.tree.column("Мин. платеж", width=120)
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Добавить платеж", 
                  command=self._add_payment).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Обновить", 
                  command=self._load_data).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Проверить просрочки", 
                  command=self._check_overdue).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Закрыть", 
                  command=self.destroy).pack(side="right", padx=5)
    
    def _load_data(self):
        """Загружает данные кредитных карт."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        summary = self._get_all_credit_cards_summary()
        
        summary_text = (
            f"Общий долг: {summary['total_debt']:,.2f} ₽ | "
            f"Общий лимит: {summary['total_credit_limit']:,.2f} ₽ | "
            f"Доступно: {summary['total_available_credit']:,.2f} ₽ | "
            f"Использование: {summary['total_utilization']:.1f}%"
        )
        self.summary_label.config(text=summary_text)
        
        for card in summary['cards']:
            utilization = f"{card['utilization_percent']:.1f}%"
            min_payment = f"{card['min_payment_amount']:.2f} ₽ ({card['min_payment_percent']}%)"
            
            self.tree.insert("", "end", values=(
                card['name'],
                f"{card['current_balance']:,.2f} ₽",
                f"{card['credit_limit']:,.2f} ₽",
                f"{card['available_credit']:,.2f} ₽",
                utilization,
                f"{card['payment_due_day']} число",
                min_payment
            ))
    
    def _get_credit_card_summary(self, account_id):
        """Получает сводку по кредитной карте."""
        account = self.db.get_account_by_id(account_id)
        if not account or account[2] != 'Credit Card':
            return None
        
        balance = float(account[4])
        credit_limit = float(account[5])
        payment_due_day = account[6]
        min_payment_percent = account[7]
        
        return {
            'id': account[0],
            'name': account[1],
            'current_balance': balance,
            'credit_limit': credit_limit,
            'available_credit': credit_limit + balance,
            'utilization_percent': (abs(balance) / credit_limit * 100) if credit_limit > 0 else 0,
            'payment_due_day': payment_due_day,
            'min_payment_amount': abs(balance) * (min_payment_percent / 100),
            'min_payment_percent': min_payment_percent,
            'last_payment_date': account[8] if len(account) > 8 else None
        }
    
    def _get_all_credit_cards_summary(self):
        """Получает сводку по всем кредитным картам через get_accounts()."""
        accounts = self.db.get_accounts()
        summaries = []
        total_debt = 0
        total_credit_limit = 0
        
        for account in accounts:
            try:
                if len(account) < 8:
                    continue
                    
                acc_type = account[2]
                if acc_type != 'Credit Card':
                    continue
                
                account_id = account[0]
                name = account[1]
                current_balance = float(account[4]) if account[4] is not None else 0.0
                credit_limit = float(account[5]) if account[5] is not None else 0.0
                payment_due_day = account[6] if len(account) > 6 else 1
                min_payment_percent = account[7] if len(account) > 7 else 5.0
                last_payment_date = account[8] if len(account) > 8 else None
                
                available_credit = credit_limit + current_balance
                utilization_percent = (abs(current_balance) / credit_limit * 100) if credit_limit > 0 else 0
                min_payment_amount = abs(current_balance) * (min_payment_percent / 100)
                
                summary = {
                    'id': account_id,
                    'name': name,
                    'current_balance': current_balance,
                    'credit_limit': credit_limit,
                    'available_credit': available_credit,
                    'utilization_percent': utilization_percent,
                    'payment_due_day': payment_due_day,
                    'min_payment_amount': min_payment_amount,
                    'min_payment_percent': min_payment_percent,
                    'last_payment_date': last_payment_date
                }
                
                summaries.append(summary)
                total_debt += abs(current_balance)
                total_credit_limit += credit_limit
                
            except (ValueError, TypeError, IndexError) as e:
                print(f"DEBUG: Error processing account {account}: {e}")
                continue
        
        total_utilization = (total_debt / total_credit_limit * 100) if total_credit_limit > 0 else 0
        
        return {
            'cards': summaries,
            'total_debt': total_debt,
            'total_credit_limit': total_credit_limit,
            'total_utilization': total_utilization,
            'total_available_credit': total_credit_limit - total_debt
        }
        
    def _add_payment(self):
        """Добавляет платеж по кредитной карте."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Платеж", "Выберите кредитную карту для внесения платежа.", parent=self)
            return
        
        item = self.tree.item(selected[0])
        card_name = item['values'][0]
        
        accounts = self.db.get_accounts()
        card_id = None
        for account in accounts:
            if len(account) >= 8 and account[2] == 'Credit Card' and account[1] == card_name:
                card_id = account[0]
                break
        
        if not card_id:
            messagebox.showerror("Ошибка", "Не удалось найти кредитную карту.", parent=self)
            return

        payment_dialog = tk.Toplevel(self)
        payment_dialog.title(f"Платеж по карте {card_name}")
        payment_dialog.geometry("300x200")
        payment_dialog.transient(self)
        payment_dialog.grab_set()
        
        from widgets.window_utils import center_window_relative
        center_window_relative(payment_dialog, self)
        
        ttk.Label(payment_dialog, text=f"Карта: {card_name}", font=("Arial", 10, "bold")).pack(pady=10)
        
        ttk.Label(payment_dialog, text="Сумма платежа:").pack()
        amount_var = tk.StringVar(value="0.0")
        amount_entry = ttk.Entry(payment_dialog, textvariable=amount_var)
        amount_entry.pack(pady=5)
        amount_entry.focus_set()
        
        ttk.Label(payment_dialog, text="Дата платежа (ГГГГ-ММ-ДД):").pack()
        date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(payment_dialog, textvariable=date_var).pack(pady=5)
        
        def process_payment():
            try:
                amount = float(amount_var.get().replace(',', '.'))
                if amount <= 0:
                    messagebox.showerror("Ошибка", "Сумма платежа должна быть положительной.", parent=payment_dialog)
                    return
                
                datetime.strptime(date_var.get(), "%Y-%m-%d")
                
                if self._record_payment(card_id, amount, date_var.get()):
                    messagebox.showinfo("Успех", f"Платеж на сумму {amount:,.2f} ₽ записан.", parent=payment_dialog)
                    payment_dialog.destroy()
                    self._load_data()
                else:
                    messagebox.showerror("Ошибка", "Не удалось записать платеж.", parent=payment_dialog)
                    
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Некорректные данные: {e}", parent=payment_dialog)
        
        ttk.Button(payment_dialog, text="Внести платеж", command=process_payment).pack(pady=20)
    
    def _record_payment(self, account_id, amount, payment_date=None):
        """Записывает платеж по кредитной карте."""
        from datetime import datetime
        
        account = self.db.get_account_by_id(account_id)
        if not account or account[2] != 'Credit Card':
            return False
        
        new_balance = float(account[4]) + amount
        
        try:
            self.db.execute(
                "UPDATE accounts SET current_balance = ?, last_payment_date = ? WHERE id = ?",
                (new_balance, payment_date or datetime.now().strftime("%Y-%m-%d"), account_id)
            )
            
            category_id = self._get_payment_category_id()
            
            self.db.execute('''
                INSERT INTO transactions 
                (date, amount, type, category_id, account_id, description)
                VALUES (?, ?, 'income', ?, ?, ?)
            ''', (
                payment_date or datetime.now().strftime("%Y-%m-%d"),
                amount,
                category_id,
                account_id,
                f"Платеж по кредитной карте {account[1]}"
            ))
            
            self.db.connection.commit()
            return True
        except Exception as e:
            print(f"DEBUG: Error recording payment: {e}")
            return False
    
    def _get_payment_category_id(self):
        """Получает или создает категорию для платежей по кредитным картам."""
        result = self.db.execute(
            "SELECT id FROM categories WHERE name = 'Кредитные платежи'"
        )
        category = result.fetchone()
        
        if category:
            return category[0]
        else:
            self.db.execute(
                "INSERT INTO categories (name, type) VALUES (?, 'expense')",
                ("Кредитные платежи",)
            )
            self.db.connection.commit()
            return self.db.cursor.lastrowid
    
    def _check_overdue(self):
        """Проверяет просроченные платежи по кредитным картам."""
        from datetime import datetime, timedelta
        
        today = datetime.now()
        accounts = self.db.get_accounts()
        overdue_cards = []
        
        for account in accounts:
            if len(account) < 8:
                continue
                
            account_id, name, acc_type, initial_balance, current_balance, credit_limit, due_day, min_percent = account[:8]
            
            if acc_type != 'Credit Card' or current_balance >= 0:
                continue
            
            last_payment = account[8] if len(account) > 8 else None
            
            next_payment_date = self._calculate_next_payment_date(due_day, last_payment)
            
            if today.date() > next_payment_date:
                min_payment = abs(current_balance) * (min_percent / 100)
                overdue_days = (today.date() - next_payment_date).days
                
                overdue_cards.append({
                    'name': name,
                    'overdue_days': overdue_days,
                    'min_payment': min_payment,
                    'total_debt': abs(current_balance),
                    'next_payment_date': next_payment_date.strftime("%Y-%m-%d")
                })
        
        if not overdue_cards:
            messagebox.showinfo("Проверка", "Нет просроченных платежей по кредитным картам.", parent=self)
            return
        
        overdue_text = "📅 Просроченные платежи:\n\n"
        for card in overdue_cards:
            overdue_text += (
                f"💳 {card['name']}:\n"
                f"   Просрочено: {card['overdue_days']} дней\n"
                f"   Минимальный платеж: {card['min_payment']:.2f} ₽\n"
                f"   Общий долг: {card['total_debt']:.2f} ₽\n"
                f"   Дата платежа: {card['next_payment_date']}\n\n"
            )
        
        overdue_window = tk.Toplevel(self)
        overdue_window.title("Просроченные платежи")
        overdue_window.geometry("500x400")
        overdue_window.transient(self)
        
        from widgets.window_utils import center_window_relative
        center_window_relative(overdue_window, self)
        
        text_frame = ttk.Frame(overdue_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap="word", font=("Arial", 10))
        text_widget.insert("1.0", overdue_text)
        text_widget.config(state="disabled")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Button(overdue_window, text="Закрыть", command=overdue_window.destroy).pack(pady=10)
    
    def _calculate_next_payment_date(self, due_day, last_payment_date):
        """Рассчитывает дату следующего платежа."""
        from datetime import datetime, timedelta
        
        today = datetime.now()
        
        if last_payment_date:
            try:
                last_payment = datetime.strptime(last_payment_date, "%Y-%m-%d")
                if last_payment.month == today.month and last_payment.year == today.year:
                    if today.day > due_day:
                        next_date = today.replace(day=1) + timedelta(days=32)
                        next_date = next_date.replace(day=min(due_day, 28))
                    else:
                        try:
                            next_date = today.replace(day=due_day)
                        except ValueError:
                            next_date = today.replace(day=1) + timedelta(days=32)
                            next_date = next_date.replace(day=min(due_day, 28))
                    return next_date.date()
            except ValueError:
                pass
        
        if today.day > due_day:
            next_date = today.replace(day=1) + timedelta(days=32)
            try:
                next_date = next_date.replace(day=due_day)
            except ValueError:
                next_date = next_date.replace(day=min(due_day, 28))
        else:
            try:
                next_date = today.replace(day=due_day)
            except ValueError:
                next_date = today.replace(day=1) + timedelta(days=32)
                next_date = next_date.replace(day=min(due_day, 28))
        
        return next_date.date()