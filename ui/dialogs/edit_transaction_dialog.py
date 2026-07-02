import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative
from ui.widgets.calendar_widgets import TtkDateEntry  # если используете

class EditTransactionDialog(tk.Toplevel):
    """Диалог редактирования транзакции."""
    
    def __init__(self, parent, db_manager, transaction_data):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager
        self.transaction_data = transaction_data
        
        self.category_id_by_display_name = {}
        
        self.title("Редактировать транзакцию")
        self.geometry("500x450")
        
        center_window_relative(self, parent)
        
        # self.transient(parent)
        # self.grab_set()
        
        self.transaction_id = transaction_data[0]
        
        self._create_ui()
        self._load_transaction_data()
        
        self.wait_window()
    
    def _create_ui(self):
        """Создает интерфейс диалога."""
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text=f"ID транзакции: {self.transaction_id}", 
                 font=("TkDefaultFont", 9, "italic")).pack(anchor="w", pady=(0, 10))
        
        form_frame = ttk.LabelFrame(main_frame, text="Редактировать данные")
        form_frame.pack(fill="x", pady=5)
        
        grid_frame = ttk.Frame(form_frame)
        grid_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(grid_frame, text="Дата:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.date_entry = TtkDateEntry(grid_frame)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(grid_frame, text="Тип:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(grid_frame, textvariable=self.type_var, 
                                      values=["Доход", "Расход", "Корректировка"], 
                                      state="readonly")
        self.type_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        
        ttk.Label(grid_frame, text="Сумма:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.amount_entry = ttk.Entry(grid_frame)
        self.amount_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(grid_frame, text="Количество:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.quantity_entry = ttk.Entry(grid_frame)
        self.quantity_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.quantity_entry.insert(0, "1.0")
        
        ttk.Label(grid_frame, text="Категория:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(grid_frame, textvariable=self.category_var, state="readonly")
        self.category_combo.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(grid_frame, text="Счет:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.account_var = tk.StringVar()
        self.account_combo = ttk.Combobox(grid_frame, textvariable=self.account_var, state="readonly")
        self.account_combo.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(grid_frame, text="Описание:").grid(row=6, column=0, padx=5, pady=5, sticky="w")
        self.description_entry = ttk.Entry(grid_frame)
        self.description_entry.grid(row=6, column=1, padx=5, pady=5, sticky="ew")
        
        grid_frame.grid_columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=15)
        
        ttk.Button(button_frame, text="Сохранить", command=self._save_changes).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.destroy).pack(side="right", padx=5)
        
        ttk.Button(main_frame, text="🗑️ Удалить эту транзакцию", 
                  command=self._delete_transaction,
                  style="Danger.TButton").pack(pady=10)
        
        style = ttk.Style()
        style.configure("Danger.TButton", foreground="white", background="#dc3545")
        
        info_frame = ttk.LabelFrame(main_frame, text="Дополнительная информация")
        info_frame.pack(fill="x", pady=10)
        
        self.info_label = ttk.Label(info_frame, text="", font=("TkDefaultFont", 9))
        self.info_label.pack(padx=10, pady=10, anchor="w")
    
    def _load_transaction_data(self):
        """Загружает данные транзакции в форму."""
        trans_id, date, amount, trans_type, category_name, description, account_name, account_id, quantity = self.transaction_data
        
        self.date_entry.var.set(date)
        
        type_mapping = {'income': 'Доход', 'expense': 'Расход', 'корректировка': 'Корректировка'}
        self.type_var.set(type_mapping.get(trans_type, trans_type.capitalize()))
        
        display_amount = amount
        
        if trans_type == 'expense':
            display_amount = -amount
        
        self.amount_entry.delete(0, tk.END)
        self.amount_entry.insert(0, f"{display_amount:.2f}")
        
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, f"{quantity:.1f}")
        
        self.description_entry.delete(0, tk.END)
        if description:
            self.description_entry.insert(0, description)
        
        self._update_category_combo()
        self._update_account_combo()
        
        if category_name:
            self.category_var.set(category_name)
        
        if account_name:
            self.account_var.set(account_name)
        
        self.original_type = trans_type
        self.original_amount = amount
        
        self._update_additional_info()
    
    def _update_category_combo(self):
        """Обновляет список категорий в зависимости от типа."""
        if not hasattr(self, 'category_id_by_display_name'):
            self.category_id_by_display_name = {}
        
        trans_type = self.type_var.get().lower()
        
        if trans_type == 'доход':
            categories = self.db.get_categories(type='income', include_subcategories=True)
        elif trans_type == 'расход':
            categories = self.db.get_categories(type='expense', include_subcategories=True)
        else:
            categories = self.db.get_categories(include_subcategories=True)
        
        display_names = []
        self.category_id_by_display_name.clear()
        
        for cat in categories:
            level = 0
            parent_id = cat[4]
            while parent_id:
                level += 1
                for c in categories:
                    if c[0] == parent_id:
                        parent_id = c[4]
                        break
                else:
                    break
            
            indent = "    " * level
            display_name = f"{indent}{cat[1]}"
            display_names.append(display_name)
            
            self.category_id_by_display_name[display_name] = cat[0]
        
        self.category_combo['values'] = display_names
    
    def _update_account_combo(self):
        """Обновляет список счетов."""
        accounts = self.db.get_accounts()
        account_names = [acc[1] for acc in accounts]
        self.account_combo['values'] = account_names
    
    def _on_type_change(self, event=None):
        """Обновляет список категорий при изменении типа."""
        self._update_category_combo()
    
    def _update_additional_info(self):
        """Обновляет дополнительную информацию."""
        trans_id, date, amount, trans_type, category_name, description, account_name, account_id, quantity = self.transaction_data
        
        ui_amount = amount
        if trans_type == 'expense':
            ui_amount = -amount
        
        info_text = f"• Дата создания: {date}\n"
        info_text += f"• Сумма в БД: {amount:.2f} ₽\n"
        info_text += f"• Сумма для редактирования: {ui_amount:.2f} ₽\n"
        
        if trans_type == 'expense':
            info_text += "• Формат отображения расходов:\n"
            info_text += "  - Положительное число = обычный расход\n"
            info_text += "  - Отрицательное число = возврат покупки\n"
        
        if quantity != 1.0:
            price_per_unit = ui_amount / quantity
            info_text += f"• Цена за единицу: {price_per_unit:.2f} ₽\n"
        
        info_text += f"• Счет: {account_name}\n"
        info_text += f"• Категория: {category_name}"
        
        self.info_label.config(text=info_text)
    
    def _save_changes(self):
        """Сохраняет изменения транзакции."""
        try:
            date_str = self.date_entry.get_date()
            if not date_str:
                messagebox.showerror("Ошибка", "Введите дату.", parent=self)
                return
            
            type_mapping = {
                'Доход': 'доход',
                'Расход': 'расход', 
                'Корректировка': 'корректировка'
            }
            trans_type = type_mapping.get(self.type_var.get(), self.type_var.get().lower())
            
            amount_str = self.amount_entry.get().strip().replace(',', '.')
            try:
                ui_amount = float(amount_str)
            except ValueError:
                messagebox.showerror("Ошибка", "Некорректная сумма.", parent=self)
                return
            
            if trans_type == 'расход':
                db_amount = -ui_amount
            else:
                db_amount = ui_amount
            
            quantity_str = self.quantity_entry.get().strip().replace(',', '.')
            try:
                quantity = float(quantity_str)
                if quantity <= 0:
                    raise ValueError("Количество должно быть положительным.")
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Некорректное количество: {e}", parent=self)
                return
            
            category_display = self.category_var.get()
            if not category_display:
                messagebox.showerror("Ошибка", "Выберите категорию.", parent=self)
                return
            
            category_name = category_display.strip()
            
            category_id = self.category_id_by_display_name.get(category_display)
            
            if category_id is None:
                for cat in self.db.get_categories():
                    if cat[1] == category_name:
                        category_id = cat[0]
                        break
            
            if category_id is None:
                messagebox.showerror("Ошибка", "Категория не найдена.", parent=self)
                return
            
            account_name = self.account_var.get()
            if not account_name:
                messagebox.showerror("Ошибка", "Выберите счет.", parent=self)
                return
            
            account_id = None
            for acc in self.db.get_accounts():
                if acc[1] == account_name:
                    account_id = acc[0]
                    break
            
            if not account_id:
                messagebox.showerror("Ошибка", "Счет не найден.", parent=self)
                return
            
            description = self.description_entry.get().strip()
            
            if self.db.update_transaction(
                transaction_id=self.transaction_id,
                date=date_str,
                amount=db_amount,
                trans_type=trans_type,
                category_id=category_id,
                description=description,
                account_id=account_id,
                quantity=quantity
            ):
                if trans_type == 'расход':
                    if ui_amount > 0:
                        msg = f"✅ Расход обновлен: {ui_amount:.2f} ₽"
                    else:
                        msg = f"✅ Возврат покупки обновлен: {abs(ui_amount):.2f} ₽"
                elif trans_type == 'доход':
                    msg = f"✅ Доход обновлен: {db_amount:.2f} ₽"
                else:
                    msg = f"✅ Корректировка обновлена: {db_amount:.2f} ₽"
                
                messagebox.showinfo("Успех", msg, parent=self)
                
                if hasattr(self.parent, '_post_dialog_update'):
                    self.parent._post_dialog_update()
                
                self.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось обновить транзакцию.", parent=self)
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка: {e}", parent=self)
            print(f"DEBUG: Error saving transaction: {e}")
    
    def _delete_transaction(self):
        """Удаляет текущую транзакцию."""
        if messagebox.askyesno(
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить эту транзакцию (ID: {self.transaction_id})?\n\n"
            f"Эта операция необратима.",
            parent=self
        ):
            if self.db.delete_transaction(self.transaction_id):
                messagebox.showinfo("Успех", "Транзакция удалена.", parent=self)
                
                if hasattr(self.parent, '_post_dialog_update'):
                    self.parent._post_dialog_update()
                
                self.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить транзакцию.", parent=self)