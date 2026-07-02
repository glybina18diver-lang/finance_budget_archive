import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from core.database import DatabaseManager
from ui.widgets.window_utils import center_window_relative
from ui.widgets.calendar_widgets import TtkDateEntry  # если используете

class CategoryManagementDialog(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db = db_manager
        
        self.title("Управление Категориями с Подкатегориями")
        self.geometry("600x550")
        
        center_window_relative(self, self.parent)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.always_on_top = False
        self._create_pin_button()
        self._create_ui()
        
    def _create_pin_button(self):
        """Создает кнопку для закрепления окна поверх всех."""
        pin_button = ttk.Button(self, text="📌", width=3, 
                               command=self._toggle_pin)
    
    def _toggle_pin(self):
        """Включает/выключает режим 'всегда поверх'."""
        self.always_on_top = not self.always_on_top
        self.attributes('-topmost', self.always_on_top)
        
    
    def _create_ui(self):
        """Создание интерфейса с поддержкой иерархии."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        tree_frame = ttk.LabelFrame(main_frame, text="Дерево категорий")
        tree_frame.pack(fill="both", expand=True, pady=5)
        
        self.categories_tree = ttk.Treeview(tree_frame, 
                                          columns=("Тип", "Плановый бюджет"), 
                                          show="tree headings")
        
        self.categories_tree.heading("#0", text="Название категории")
        self.categories_tree.heading("Тип", text="Тип")
        self.categories_tree.heading("Плановый бюджет", text="Плановый бюджет")
        
        self.categories_tree.column("#0", width=250, stretch=tk.YES)
        self.categories_tree.column("Тип", width=80, anchor="center")
        self.categories_tree.column("Плановый бюджет", width=120, anchor="e")
        
        yscrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.categories_tree.yview)
        yscrollbar.pack(side="right", fill="y")
        self.categories_tree.config(yscrollcommand=yscrollbar.set)
        self.categories_tree.pack(side="left", fill="both", expand=True)
        
        self.categories_tree.bind("<<TreeviewSelect>>", self._on_category_select)
        
        self._setup_tree_context_menu()
        self._create_form(main_frame)
        self._create_buttons(main_frame)
        
        self.load_categories_into_tree()
    
    def _setup_tree_context_menu(self):
        """Настраивает контекстное меню для дерева категорий."""
        self.tree_context_menu = tk.Menu(self, tearoff=0)
        self.tree_context_menu.add_command(label="✏️ Редактировать", command=self._edit_category)
        self.tree_context_menu.add_command(label="➕ Добавить подкатегорию", 
                                          command=self._add_subcategory)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="🗑️ Удалить категорию", 
                                          command=self._delete_selected_category)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="📊 Статистика категории", 
                                          command=self._analyze_category)
        
        self.categories_tree.bind("<Button-3>", self._show_tree_context_menu)
    
    def _show_tree_context_menu(self, event):
        """Показывает контекстное меню для дерева."""
        item = self.categories_tree.identify_row(event.y)
        if item:
            self.categories_tree.selection_set(item)
            self.tree_context_menu.tk_popup(event.x_root, event.y_root)
    
    def _create_form(self, master):
        """Создает форму для добавления/редактирования категории."""
        form_frame = ttk.LabelFrame(master, text="Добавить/Редактировать категорию")
        form_frame.pack(fill="x", pady=5)
        
        form_grid = ttk.Frame(form_frame)
        form_grid.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(form_grid, text="Название:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.name_input = ttk.Entry(form_grid)
        self.name_input.grid(row=0, column=1, padx=5, pady=2, sticky="ew", columnspan=2)
        
        ttk.Label(form_grid, text="Тип:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.type_combo_var = tk.StringVar()
        self.type_combo = ttk.Combobox(form_grid, textvariable=self.type_combo_var, 
                                      values=["income", "expense"], state="readonly")
        self.type_combo.set("expense")
        self.type_combo.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        ttk.Label(form_grid, text="Родительская категория:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.parent_combo_var = tk.StringVar()
        self.parent_combo = ttk.Combobox(form_grid, textvariable=self.parent_combo_var, 
                                        state="readonly")
        self.parent_combo.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(form_grid, text="Очистить", width=8,
                  command=lambda: self.parent_combo_var.set("")).grid(row=2, column=2, padx=5)
        
        ttk.Label(form_grid, text="Плановый бюджет (мес.):").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.budget_input = ttk.Entry(form_grid)
        self.budget_input.insert(0, "0.0")
        self.budget_input.grid(row=3, column=1, padx=5, pady=2, sticky="ew", columnspan=2)
        
        form_grid.grid_columnconfigure(1, weight=1)
    
    def _create_buttons(self, master):
        """Создает кнопки управления."""
        button_frame = ttk.Frame(master)
        button_frame.pack(fill="x", pady=10)
        
        self.add_button = ttk.Button(button_frame, text="Добавить", command=self._add_category)
        self.add_button.pack(side="left", padx=5)
        
        self.edit_button = ttk.Button(button_frame, text="Сохранить изменения", 
                                     command=self._edit_category, state="disabled")
        self.edit_button.pack(side="left", padx=5)
        
        self.delete_button = ttk.Button(button_frame, text="Удалить выбранную", 
                                       command=self._delete_selected_category, state="disabled")
        self.delete_button.pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Закрыть", command=self.on_close).pack(side="right", padx=5)
        
        self.editing_category_id = None
        self.current_parent_id = None
    
    def _add_subcategory(self):
        """Добавляет подкатегорию для выбранной категории."""
        selected_item = self.categories_tree.selection()
        if not selected_item:
            if hasattr(self.parent, 'show_status_message'):
                self.parent.show_status_message(
                    "⚠️ Выберите категорию для добавления подкатегории", 
                    message_type="warning"
                )
            else:
                messagebox.showinfo("Добавление подкатегории", 
                                  "Выберите категорию для добавления подкатегории.", 
                                  parent=self)
            return
        
        item_id = selected_item[0]
        values = self.categories_tree.item(item_id)
        parent_name = values['text']
        
        self.current_parent_id = int(item_id)
        self.parent_combo_var.set(parent_name)
        
        self._reset_form_state()
        self.name_input.focus_set()
        
        if hasattr(self.parent, 'show_status_message'):
            self.parent.show_status_message(
                f"➕ Готово к добавлению подкатегории для '{parent_name}'",
                message_type="info",
                icon="➕"
            )
        else:
            messagebox.showinfo("Добавление подкатегории", 
                              f"Форма готова для добавления подкатегории к '{parent_name}'", 
                              parent=self)
    
    def on_close(self):
        """Закрывает диалоговое окно."""
        self.grab_release()
        self.destroy() 

    def _on_category_select(self, event):
        """Обработчик выбора категории в дереве."""
        selected_item = self.categories_tree.selection()
        
        if selected_item:
            self.edit_button.config(state="normal")
            self.delete_button.config(state="normal")
            
            item_id = selected_item[0]
            values = self.categories_tree.item(item_id, 'values')
            
            category_id = int(item_id)
            category_data = self.db.get_category_by_id(category_id)
            
            if category_data:
                self.name_input.delete(0, tk.END)
                self.name_input.insert(0, self.categories_tree.item(item_id, 'text'))
                
                self.type_combo_var.set(values[0])
                
                parent_id = category_data[4]
                if parent_id:
                    parent_data = self.db.get_category_by_id(parent_id)
                    if parent_data:
                        self.parent_combo_var.set(parent_data[1])
                    else:
                        self.parent_combo_var.set("")
                else:
                    self.parent_combo_var.set("")
                
                budget_str = values[1].replace(' ₽', '')
                self.budget_input.delete(0, tk.END)
                self.budget_input.insert(0, budget_str)
                
                self.editing_category_id = category_id
        else:
            self._reset_form_state()
            
    def load_categories_into_tree(self):
        """Загружает категории с иерархией в дерево."""
        for i in self.categories_tree.get_children():
            self.categories_tree.delete(i)
        
        categories = self.db.get_categories_with_hierarchy()
        
        tree_items = {}
        
        for cat_id, name, cat_type, budget, parent_id, level, path in categories:
            if level == 0:
                item_id = self.categories_tree.insert("", "end", iid=str(cat_id),
                                                     text=name,
                                                     values=(cat_type, f"{budget:.2f} ₽"))
                tree_items[cat_id] = item_id
            else:
                if parent_id in tree_items:
                    parent_item = tree_items[parent_id]
                    item_id = self.categories_tree.insert(parent_item, "end", 
                                                         iid=str(cat_id),
                                                         text=name,
                                                         values=(cat_type, f"{budget:.2f} ₽"))
                    tree_items[cat_id] = item_id
        
        for item in self.categories_tree.get_children():
            self.categories_tree.item(item, open=True)
        
        self._update_parent_combo()
        
        self.categories_tree.selection_remove(self.categories_tree.selection())
        self._on_category_select(None)

    def _update_parent_combo(self):
        """Обновляет список родительских категорий в комбобоксе."""
        main_categories = []
        for cat in self.db.get_categories():
            if cat[4] is None:
                main_categories.append(cat[1])
        
        main_categories.sort()
        self.parent_combo['values'] = [""] + main_categories
    
    def _add_category(self):
        """Добавляет новую категорию с поддержкой родителя."""
        name = self.name_input.get().strip()
        cat_type = self.type_combo_var.get()
        budget_str = self.budget_input.get().strip()
        parent_name = self.parent_combo_var.get()
        
        if not name:
            if hasattr(self.parent, 'show_status_message'):
                self.parent.show_status_message("⚠️ Введите название категории", message_type="warning")
            else:
                messagebox.showerror("Ошибка", "Введите название категории.", parent=self)
            return
        
        try:
            budget = float(budget_str)
        except ValueError:
            messagebox.showerror("Ошибка", "Плановый бюджет должен быть числом.", parent=self)
            return
        
        parent_id = None
        if parent_name:
            parent_data = self.db.get_category_by_name(parent_name)
            if parent_data:
                parent_id = parent_data[0]
            else:
                messagebox.showerror("Ошибка", 
                                   f"Родительская категория '{parent_name}' не найдена.", 
                                   parent=self)
                return
        
        if parent_id:
            parent_category = self.db.get_category_by_id(parent_id)
            if parent_category and parent_category[2] != cat_type:
                messagebox.showerror("Ошибка", 
                                   f"Подкатегория типа '{cat_type}' не может быть добавлена "
                                   f"к родительской категории типа '{parent_category[2]}'.",
                                   parent=self)
                return
        
        if self.db.add_category(name, cat_type, budget, parent_id):
            if hasattr(self.parent, 'show_status_message'):
                if parent_id:
                    self.parent.show_status_message(
                        f"✅ Подкатегория '{name}' добавлена", 
                        message_type="success",
                        icon="✅"
                    )
                else:
                    self.parent.show_status_message(
                        f"✅ Категория '{name}' добавлена", 
                        message_type="success",
                        icon="✅"
                    )
            else:
                messagebox.showinfo("Успех", f"Категория '{name}' добавлена.", parent=self)
            
            self.load_categories_into_tree()
            self._reset_form_state()
        else:
            if hasattr(self.parent, 'show_status_message'):
                self.parent.show_status_message(
                    f"❌ Не удалось добавить категорию '{name}'", 
                    message_type="error",
                    icon="❌"
                )
            else:
                messagebox.showerror("Ошибка", 
                                   "Не удалось добавить категорию. Возможно, категория с таким именем уже существует.",
                                   parent=self)

    def _edit_category(self):
        """Редактирует выбранную категорию."""
        if not self.editing_category_id:
            if hasattr(self.parent, 'show_status_message'):
                self.parent.show_status_message("⚠️ Выберите категорию для редактирования", message_type="warning")
            else:
                messagebox.showwarning("Редактирование", "Выберите категорию для редактирования.", parent=self)
            return
        
        name = self.name_input.get().strip()
        cat_type = self.type_combo_var.get()
        budget_str = self.budget_input.get().strip()
        parent_name = self.parent_combo_var.get()
        
        if not name:
            messagebox.showerror("Ошибка", "Введите название категории.", parent=self)
            return
        
        try:
            budget = float(budget_str)
        except ValueError:
            messagebox.showerror("Ошибка", "Плановый бюджет должен быть числом.", parent=self)
            return
        
        parent_id = None
        if parent_name:
            parent_data = self.db.get_category_by_name(parent_name)
            if parent_data:
                parent_id = parent_data[0]
            else:
                messagebox.showerror("Ошибка", 
                                   f"Родительская категория '{parent_name}' не найдена.",
                                   parent=self)
                return
        
        existing_category = self.db.get_category_by_name(name)
        if existing_category and existing_category[0] != self.editing_category_id:
            messagebox.showerror("Ошибка", f"Категория с именем '{name}' уже существует.", parent=self)
            return
        
        if self.db.update_category(self.editing_category_id, name, cat_type, budget, parent_id):
            if hasattr(self.parent, 'show_status_message'):
                self.parent.show_status_message(
                    f"✏️ Категория '{name}' обновлена", 
                    message_type="success",
                    icon="✏️"
                )
            else:
                messagebox.showinfo("Успех", f"Категория '{name}' обновлена.", parent=self)
            
            self.load_categories_into_tree()
            self._reset_form_state()
        else:
            if hasattr(self.parent, 'show_status_message'):
                self.parent.show_status_message(
                    f"❌ Не удалось обновить категорию '{name}'", 
                    message_type="error"
                )
            else:
                messagebox.showerror("Ошибка", f"Не удалось обновить категорию '{name}'.", parent=self)
            
    def _delete_selected_category(self):
        """Удаляет выбранную категорию с подкатегориями."""
        selected_items = self.categories_tree.selection()
        if not selected_items:
            messagebox.showinfo("Удаление", "Выберите категорию для удаления.", parent=self)
            return
        
        item_id = selected_items[0]
        category_name = self.categories_tree.item(item_id, 'text')
        category_id = int(item_id)
        
        confirm_msg = f"Вы уверены, что хотите удалить категорию '{category_name}'?"
        
        children = self.categories_tree.get_children(item_id)
        if children:
            confirm_msg += f"\n\n⚠️ Внимание! Будут также удалены {len(children)} подкатегорий."
        
        transactions = self.db.get_transactions(category_id=category_id)
        if transactions:
            confirm_msg += f"\n\n⚠️ В этой категории есть {len(transactions)} транзакций. "
            confirm_msg += "Они будут переведены в категорию 'Без категории'."
        
        if not messagebox.askyesno("Подтверждение удаления", confirm_msg, parent=self):
            return
        
        deleted_count = self.db.delete_category_with_children(category_id)
        
        if deleted_count > 0:
            self.show_status_message(f"Удалено {deleted_count} категорий")
            self.load_categories_into_tree()
            self._reset_form_state()
            
            if hasattr(self.parent, '_post_dialog_update'):
                self.parent._post_dialog_update()
        else:
            messagebox.showerror("Ошибка", "Не удалось удалить категорию.", parent=self)
            
    def _analyze_category(self):
        """Показывает статистику по выбранной категории."""
        selected_item = self.categories_tree.selection()
        if not selected_item:
            messagebox.showinfo("Статистика", "Выберите категорию для просмотра статистики.", parent=self)
            return
        
        category_id = int(selected_item[0])
        category_name = self.categories_tree.item(selected_item[0], 'text')
        
        transactions = self.db.get_transactions(category_id=category_id)
        
        if not transactions:
            messagebox.showinfo("Статистика", 
                              f"В категории '{category_name}' нет транзакций.", 
                              parent=self)
            return
        
        total_income = 0
        total_expense = 0
        transaction_count = len(transactions)
        
        for trans in transactions:
            amount = float(trans[2])
            trans_type = trans[3]
            
            if trans_type == 'income':
                total_income += amount
            else:
                total_expense += abs(amount)
        
        stats_text = f"📊 Статистика категории: {category_name}\n\n"
        stats_text += f"📋 Количество операций: {transaction_count}\n"
        stats_text += f"💰 Общий доход: {total_income:.2f} ₽\n"
        stats_text += f"💸 Общий расход: {total_expense:.2f} ₽\n"
        
        if total_income > 0 or total_expense > 0:
            stats_text += f"📈 Чистый поток: {total_income - total_expense:.2f} ₽\n"
        
        stats_window = tk.Toplevel(self)
        stats_window.title(f"Статистика: {category_name}")
        stats_window.geometry("400x250")
        
        text_widget = tk.Text(stats_window, wrap="word", font=("TkDefaultFont", 10))
        text_widget.insert("1.0", stats_text)
        text_widget.config(state="disabled")
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Button(stats_window, text="Закрыть", command=stats_window.destroy).pack(pady=10)
        
        from widgets.window_utils import center_window_relative
        center_window_relative(stats_window, self)

    def _set_category_budget(self):
        """Устанавливает бюджет для категории"""
        selected_item = self.categories_tree.selection()
        if selected_item:
            pass

    def show_status_message(self, message, duration_ms=3000):
        """Показывает сообщение в статусе родительского окна"""
        if hasattr(self.master, 'show_status_message'):
            self.master.show_status_message(message, duration_ms)
        else:
            print(f"STATUS: {message}")
            
    def _reset_form_state(self):
        """Сбрасывает поля формы и состояние кнопок"""
        self.name_input.delete(0, tk.END)
        self.type_combo.set("expense")
        self.budget_input.delete(0, tk.END)
        self.budget_input.insert(0, "0.0")
        self.editing_category_id = None
        self.edit_button.config(state="disabled")
        if hasattr(self, 'delete_button'):
            self.delete_button.config(state="disabled")

    def show_status_message(self, message, duration_ms=3000):
        """Показывает сообщение в статусе родительского окна."""
        if hasattr(self.parent, 'show_status_message'):
            self.parent.show_status_message(message, duration_ms)
        else:
            print(f"STATUS: {message}")