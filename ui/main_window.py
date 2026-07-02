# ui/main_window.py - Основная логика GUI
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta
import calendar
import threading
import queue
import os
import shutil

from core.database import DatabaseManager
from ui.dashboard import SimpleDashboard
from ui.dialogs.loan_dialog import LoanManagementWindow
from ui.dialogs.account_dialog import AccountManagementDialog
from ui.dialogs.category_dialog import CategoryManagementDialog
from ui.dialogs.transfer_dialog import TransferDialog
from ui.dialogs.reconciliation_dialog import ReconciliationDialog
from ui.dialogs.credit_cards_window import CreditCardsWindow
from ui.dialogs.edit_transaction_dialog import EditTransactionDialog
from ui.dialogs.date_range_dialog import DateRangeDialog
from ui.widgets.calendar_widgets import TtkDateEntry
from ui.widgets.async_manager import async_manager
from ui.widgets.window_utils import center_window_relative
# Добавляем импорт нового диалога
from ui.dialogs.operations_dialog import OperationsDialog
from ui.widgets.pie_chart_widget import PieChartWidget
from ui.widgets.income_expense_chart import IncomeExpenseChart
from ui.widgets.loading_indicator import LoadingIndicator
import threading


class MainWindow(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.parent = parent  # ссылка на BudgetApp
        self.db = db
        
        self.accounts_data = {}
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

        # 1. Создаем статус бар ОДИН РАЗ
        self.status_bar = ttk.Label(self.parent, text="⏳ Загрузка данных...", 
                                    relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(side="bottom", fill="x")
        
       
        
        # 3. не Создаем ОСНОВНОЙ UI сразу, 
        self._create_menu()
        
        # 4. Запускаем загрузку данных в отдельном потоке
        self.parent.after(100, self._start_loading_sequence)

    def _start_loading_sequence(self):
        """Запускает последовательность загрузки."""
        # Создаем и показываем индикатор
        self.loading_indicator = LoadingIndicator(self.parent, "Загрузка данных...")
        self.loading_indicator.start()
        
        # Запускаем загрузку данных
        self._start_async_loading()
    
    def _init_empty_ui(self):
        """Создает минимальный UI, пока загружаются данные."""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Просто заголовок, остальное будет добавлено позже
        welcome_label = ttk.Label(main_frame, 
                                 text="⏳ Загрузка данных...",
                                 font=("TkDefaultFont", 12),
                                 foreground="gray")
        welcome_label.pack(pady=50)
        
        self.status_bar = ttk.Label(self.parent, text="Загрузка...", relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

    def _initial_load(self):
        """Начальная загрузка данных с индикатором."""
        try:
            self._load_all_data()
            self._update_display()
        except Exception as e:
            print(f"DEBUG: Error in initial load: {e}")
            # Показываем сообщение об ошибке
            if messagebox.askretrycancel("Ошибка загрузки", 
                                       f"Не удалось загрузить данные:\n{str(e)}\n\nПопробовать снова?"):
                self._initial_load()
        finally:
            # Всегда скрываем индикатор, даже если произошла ошибка
            self.hide_loading()

    def _start_async_loading(self):
        """Запускает асинхронную загрузку данных."""
        import threading
        
        def load_data_thread():
            try:
                # Загружаем данные
                self._load_all_data()
                
                # Обновляем UI в основном потоке
                self.parent.after(0, self._finish_loading_and_create_ui)
            except Exception as e:
                print(f"DEBUG: Error loading data: {e}")
                self.parent.after(0, lambda: self._handle_loading_error(e))
        
        thread = threading.Thread(target=load_data_thread, daemon=True)
        thread.start()
        
    def _finish_ui_setup(self):
        """Завершает настройку UI после загрузки данных."""
        try:
            # Скрываем индикатор
            self.hide_loading()
            
            # Наполняем UI данными
            self._populate_ui_after_loading()
            
            # Обновляем статус бар
            self.status_bar.config(text="✅ Данные успешно загружены")
            
            # Через 2 секунды возвращаем стандартный статус
            self.parent.after(2000, self._reset_status_to_ready)
            
        except Exception as e:
            print(f"DEBUG: Error finishing UI setup: {e}")
            self._handle_loading_error(e)
            
    def _reset_status_to_ready(self):
        """Сбрасывает статус бар к стандартному состоянию."""
        if hasattr(self, 'status_bar'):
            self.status_bar.config(
                text="Готово.",
                foreground="black",
                font=("TkDefaultFont", 9),
                relief=tk.SUNKEN
            )

    def _handle_loading_error(self, error):
        """Обрабатывает ошибку загрузки."""
        # UI уже создан в _finish_loading_and_create_ui
        # Просто обновляем статус
        
        print(f"DEBUG: Loading error: {error}")
        self.status_bar.config(text="❌ Ошибка загрузки данных")
        
        # Показываем сообщение об ошибке
        error_window = tk.Toplevel(self.parent)
        error_window.title("Ошибка загрузки")
        error_window.geometry("400x200")
        
        ttk.Label(error_window, text="❌ Ошибка загрузки данных", 
                 font=("TkDefaultFont", 12, "bold")).pack(pady=20)
        
        error_text = tk.Text(error_window, height=6, width=50, wrap="word")
        error_text.insert("1.0", f"Не удалось загрузить некоторые данные:\n\n{str(error)}")
        error_text.config(state="disabled")
        error_text.pack(pady=10, padx=10)
        
        button_frame = ttk.Frame(error_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Повторить", 
                  command=lambda: self._retry_loading(error_window)).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Закрыть", 
                  command=error_window.destroy).pack(side="left", padx=5)
        
        center_window_relative(error_window, self.parent)
        
    def _retry_loading(self, error_window):
        """Повторяет загрузку."""
        error_window.destroy()
        
        # Показываем индикатор загрузки поверх текущего UI
        self.show_loading("Повторная загрузка данных...")
        
        # Запускаем повторную загрузку
        def retry_in_thread():
            try:
                self._load_all_data()
                self.parent.after(0, self._finish_retry)
            except Exception as e:
                self.parent.after(0, lambda: self._handle_loading_error(e))
        
        thread = threading.Thread(target=retry_in_thread, daemon=True)
        thread.start()

    def _finish_retry(self):
        """Завершает повторную загрузку."""
        self.hide_loading()
        self._update_display()
        
        if hasattr(self, 'pie_chart'):
            self.pie_chart.update_chart()
        if hasattr(self, 'line_chart'):
            self.line_chart.update_chart()
        
        self.status_bar.config(text="✅ Данные успешно загружены")
        self.parent.after(2000, self._reset_status_to_ready)

    def _finish_loading_and_create_ui(self):
        """Завершает загрузку и создает UI."""
        try:
            # Скрываем индикатор
            if hasattr(self, 'loading_indicator'):
                self.loading_indicator.stop()
                del self.loading_indicator
            
            # Создаем основной UI
            self._init_ui()
            self._update_display()
            
            # Обновляем статус бар
            self.status_bar.config(text="✅ Данные успешно загружены")
            
            # Через 2 секунды возвращаем стандартный статус
            self.parent.after(2000, self._reset_status_to_ready)
            
        except Exception as e:
            print(f"DEBUG: Error finishing UI setup: {e}")
            # Все равно создаем UI
            self._init_ui()
            self._handle_loading_error(e)
    
    
    def _bring_all_to_front(self, event=None):
        """Поднимает все открытые окна."""
        self.parent.lift()
        for window_type, window in self.parent.open_windows.items():
            if window and window.winfo_exists():
                window.lift()
    
    def _on_main_window_close(self):
        """Закрывает все дочерние окна перед закрытием главного."""
        for window_type, window in self.parent.open_windows.items():
            if window and window.winfo_exists():
                window.destroy()
    
    def _create_menu(self):
        """Создает главное меню приложения."""
        menubar = tk.Menu(self.parent)
        self.parent.config(menu=menubar)
        
        # Меню Файл (оставляем как есть)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Импорт CSV...", command=self._import_from_csv)
        file_menu.add_command(label="Экспорт в CSV...", command=self._export_to_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Создать резервную копию...", command=self._create_backup)
        file_menu.add_command(label="Восстановить...", command=self._restore_backup)
        file_menu.add_command(label="Информация о копиях", command=self._show_backup_info)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.parent.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)
        
        # Меню Операции (упрощаем)
        operations_menu = tk.Menu(menubar, tearoff=0)
        operations_menu.add_command(label="Добавить операцию...", command=self._open_operations_dialog)
        operations_menu.add_command(label="Посмотреть все транзакции", command=lambda: self._open_operations_dialog(show_filters=True))
        menubar.add_cascade(label="Операции", menu=operations_menu)
        
        # Меню Кредиты (оставляем)
        credit_menu = tk.Menu(menubar, tearoff=0)
        credit_menu.add_command(label="Управление кредитными картами", command=self._open_credit_cards)
        credit_menu.add_command(label="Управление займами", command=self._open_loan_management)
        credit_menu.add_command(label="Аналитика по кредитам", command=self._show_credit_analytics)
        menubar.add_cascade(label="Кредиты", menu=credit_menu)
        
        # Меню Отчеты (оставляем)
        reports_menu = tk.Menu(menubar, tearoff=0)
        reports_menu.add_command(label="Дашборд", command=self._open_dashboard)
        reports_menu.add_command(label="Месячный отчет", command=self._show_monthly_report)
        reports_menu.add_command(label="Отчет по категориям", command=self._show_category_report)
        reports_menu.add_command(label="Анализ расходов", command=self._show_expense_analysis)
        menubar.add_cascade(label="Отчеты", menu=reports_menu)
        
        # Меню Настройки (переносим сюда управление счетами и категориями)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Управление счетами", command=self._open_account_management)
        settings_menu.add_command(label="Управление категориями", command=self._open_category_management)
        settings_menu.add_separator()
        settings_menu.add_command(label="Внешний вид", command=self._open_appearance_settings)
        settings_menu.add_command(label="Язык", command=self._open_language_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Настройки уведомлений", command=self._open_notification_settings)
        settings_menu.add_command(label="Автоматизация", command=self._open_automation_settings)
        menubar.add_cascade(label="Настройки", menu=settings_menu)
        
        # Меню Помощь (оставляем)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Справка", command=self._show_help)
        help_menu.add_command(label="О программе", command=self._show_about)
        menubar.add_cascade(label="Помощь", menu=help_menu)

    # ------ Методы меню (заглушки) ------
    def _open_appearance_settings(self):
        messagebox.showinfo("В разработке", "Настройки внешнего вида в разработке", parent=self.parent)

    def _open_language_settings(self):
        messagebox.showinfo("В разработке", "Настройки языка в разработке", parent=self.parent)

    def _open_notification_settings(self):
        messagebox.showinfo("В разработке", "Настройки уведомлений в разработке", parent=self.parent)

    def _open_automation_settings(self):
        messagebox.showinfo("В разработке", "Настройки автоматизации в разработке", parent=self.parent)

    def _show_monthly_report(self):
        messagebox.showinfo("В разработке", "Месячный отчет в разработке", parent=self.parent)
    
    def _show_category_report(self):
        report_text = self.get_category_statistics_report()
        self._show_report_window("Отчет по категориям", report_text)
    
    def _show_expense_analysis(self):
        messagebox.showinfo("В разработке", "Анализ расходов в разработке", parent=self.parent)

    def _show_help(self):
        messagebox.showinfo("Справка", "Справка в разработке", parent=self.parent)

    def _show_about(self):
        about_text = (
            "Простой Бюджет (Tkinter) - SQLite\n"
            "Версия: 1.0\n"
            "© 2025\n\n"
            "Управление личными финансами\n"
            "Поддержка счетов, категорий, транзакций,\n"
            "переводов, кредитных карт и займов."
        )
        messagebox.showinfo("О программе", about_text, parent=self.parent)
    
    # ---- Универсальный метод для показа отчетов ----
    def _show_report_window(self, title, report_text):
        """Универсальный метод для показа отчетов."""
        report_window = tk.Toplevel(self.parent)
        report_window.title(title)
        report_window.geometry("700x600")
        
        # Текст с прокруткой
        text_frame = ttk.Frame(report_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap="word", font=("Consolas", 10))
        text_widget.insert("1.0", report_text)
        text_widget.config(state="disabled")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Кнопки
        button_frame = ttk.Frame(report_window)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Сохранить в файл",
                  command=lambda: self._save_report_to_file(report_text, title)).pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Закрыть",
                  command=report_window.destroy).pack(side="right", padx=5)
        
        center_window_relative(report_window, self.parent)
        
    # Сохранить отчет в файл
    def _save_report_to_file(self, report_text, title):
        import tkinter.filedialog as fd
        
        filename = fd.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title=f"Сохранить {title}",
            initialfile=f"{title.replace(' ', '_')}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                self.show_status_message(f"Отчет сохранен: {os.path.basename(filename)}", 3000)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}", parent=self.parent)
    
    # ------ Создание резервной копии БД ------
    def _create_backup(self):
        """Создает резервную копию базы данных с выбором пути."""
        try:
            import tkinter.filedialog as fd
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"budget_backup_{timestamp}.db"
            
            backup_path = fd.asksaveasfilename(
                defaultextension=".db",
                filetypes=[
                    ("Database files", "*.db"),
                    ("All files", "*.*")
                ],
                title="Сохранить резервную копию",
                initialfile=default_filename
            )
            
            if not backup_path:
                self.show_status_message("Создание резервной копии отменено", 2000)
                return
            
            shutil.copy2("budget.db", backup_path)
            
            abs_path = os.path.abspath(backup_path)
            
            info_text = (
                f"✅ Резервная копия успешно создана\n\n"
                f"📁 Путь: {abs_path}\n"
                f"📊 Размер: {os.path.getsize(abs_path) / 1024:.1f} КБ\n"
                f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            messagebox.showinfo("Резервное копирование", info_text, parent=self.parent)
            self.show_status_message(f"Резервная копия сохранена: {os.path.basename(abs_path)}", 5000)
            
            self._create_backup_link(abs_path)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать резервную копию:\n{str(e)}", parent=self.parent)

    def _create_backup_link(self, backup_path):
        """Создает ссылку на последнюю резервную копию в папке приложения."""
        try:
            links_dir = "last_backups"
            if not os.path.exists(links_dir):
                os.makedirs(links_dir)
            
            link_path = os.path.join(links_dir, "latest_backup.db")
            
            if os.path.exists(link_path):
                os.remove(link_path)
            
            if os.name == 'nt':
                shutil.copy2(backup_path, link_path)
            else:
                os.symlink(backup_path, link_path)
                
        except Exception as e:
            print(f"DEBUG: Не удалось создать ссылку на резервную копию: {e}")

    def _show_backup_info(self):
        """Показывает информацию о последних резервных копиях."""
        import glob
        
        backup_patterns = [
            "backups/budget_backup_*.db",
            "*.db.bak",
            "last_backups/*.db"
        ]
        
        backups = []
        for pattern in backup_patterns:
            backups.extend(glob.glob(pattern))
        
        if not backups:
            messagebox.showinfo("Резервные копии", "Резервные копии не найдены", parent=self.parent)
            return
        
        backups.sort(key=os.path.getmtime, reverse=True)
        
        info_text = "📁 Найденные резервные копии:\n\n"
        
        for i, backup in enumerate(backups[:10]):
            try:
                size = os.path.getsize(backup) / 1024
                mtime = datetime.fromtimestamp(os.path.getmtime(backup))
                info_text += f"{i+1}. {os.path.basename(backup)}\n"
                info_text += f"   📏 Размер: {size:.1f} КБ\n"
                info_text += f"   📅 Дата: {mtime.strftime('%Y-%m-%d %H:%M')}\n"
                info_text += f"   📍 Путь: {os.path.abspath(backup)}\n\n"
            except:
                continue
        
        info_window = tk.Toplevel(self.parent)
        info_window.title("Информация о резервных копиях")
        info_window.geometry("600x400")
        
        text_frame = ttk.Frame(info_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 9))
        text_widget.insert("1.0", info_text)
        text_widget.config(state="disabled")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        button_frame = ttk.Frame(info_window)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Создать новую копию", 
                  command=self._create_backup).pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Восстановить из копии", 
                  command=self._restore_backup).pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="Закрыть", 
                  command=info_window.destroy).pack(side="right", padx=5)
        
        center_window_relative(info_window, self.parent)

    # ---- Восстановление копии БД ----
    def _restore_backup(self):
        """Восстанавливает базу данных из резервной копии."""
        try:
            import tkinter.filedialog as fd
            
            # Создаем кастомное диалоговое окно
            class BackupRestoreDialog(tk.Toplevel):
                def __init__(self, parent):
                    super().__init__(parent)
                    self.parent_instance = parent
                    self.result = None
                    
                    self.title("Восстановление базы данных")
                    self.geometry("500x430")
                    
                    center_window_relative(self, parent)
                    self._create_ui()
                    
                def _create_ui(self):
                    main_frame = ttk.Frame(self, padding="20")
                    main_frame.pack(fill="both", expand=True)
                    
                    warning_frame = ttk.Frame(main_frame)
                    warning_frame.pack(fill="x", pady=(0, 15))
                    
                    ttk.Label(warning_frame, text="⚠️", 
                             font=("TkDefaultFont", 24, "bold"),
                             foreground="orange").pack(side="left", padx=(0, 10))
                    
                    ttk.Label(warning_frame, text="ВОССТАНОВЛЕНИЕ БАЗЫ ДАННЫХ",
                             font=("TkDefaultFont", 14, "bold")).pack(side="left")
                    
                    info_text = (
                        "Вы собираетесь восстановить базу данных из резервной копии.\n\n"
                        "⚠️ ВНИМАНИЕ!\n\n"
                        "• Текущая база данных будет заменена\n"
                        "• Все текущие данные будут утеряны\n"
                        "• Рекомендуется создать резервную копию перед восстановлением\n\n"
                        "Выберите действие:"
                    )
                    
                    info_label = ttk.Label(main_frame, text=info_text,
                                          font=("TkDefaultFont", 10),
                                          justify="left",
                                          wraplength=450)
                    info_label.pack(fill="x", pady=10)
                    
                    button_frame = ttk.Frame(main_frame)
                    button_frame.pack(fill="x", pady=5)
                    
                    ttk.Button(button_frame, text="📁 Создать резервную копию",
                              command=self._create_backup,
                              width=32).pack(pady=5)
                    
                    ttk.Button(button_frame, text="🔄 Продолжить восстановление",
                              command=lambda: self._set_result("continue"),
                              width=32).pack(pady=5)
                    
                    ttk.Button(button_frame, text="❌ Отмена",
                              command=lambda: self._set_result("cancel"),
                              width=13).pack(pady=5)
                   
                    ttk.Button(main_frame, text="ℹ️ Показать информацию о существующих копиях",
                              command=self._show_backup_info).pack(pady=5)
                
                def _create_backup(self):
                    self.destroy()
                    self.parent_instance._create_backup()
                    if messagebox.askyesno("Резервная копия создана",
                                          "Резервная копия успешно создана.\n\n"
                                          "Продолжить восстановление из другой копии?",
                                          parent=self.parent_instance.parent):
                        self.parent_instance._restore_backup()
                
                def _show_backup_info(self):
                    self.parent_instance._show_backup_info()
                
                def _set_result(self, result):
                    self.result = result
                    self.destroy()
                
                def show(self):
                    self.wait_window()
                    return self.result
            
            dialog = BackupRestoreDialog(self)
            result = dialog.show()
            
            if result == "cancel":
                self.show_status_message("Восстановление отменено", 2000)
                return
            elif result != "continue":
                return
            
            backup_path = fd.askopenfilename(
                filetypes=[
                    ("Database files", "*.db"),
                    ("Backup files", "*.bak"),
                    ("All files", "*.*")
                ],
                title="Выберите файл для восстановления"
            )
            
            if not backup_path:
                self.show_status_message("Восстановление отменено", 2000)
                return
            
            if not os.path.exists(backup_path):
                messagebox.showerror("Ошибка", "Файл не найден", parent=self.parent)
                return
            
            file_size = os.path.getsize(backup_path)
            if file_size < 1024:
                if not messagebox.askyesno(
                    "Предупреждение",
                    f"Файл очень маленький ({file_size} байт).\n"
                    "Возможно, это не корректная база данных.\n\n"
                    "Продолжить восстановление?",
                    parent=self.parent
                ):
                    return
            
            if not messagebox.askyesno(
                "Финальное подтверждение",
                f"Вы уверены, что хотите восстановить базу данных из файла:\n\n"
                f"📁 {os.path.basename(backup_path)}\n"
                f"📏 Размер: {file_size / 1024:.1f} КБ\n\n"
                f"Это действие необратимо!",
                parent=self.parent
            ):
                self.show_status_message("Восстановление отменено", 2000)
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_backup = f"temp_backup_before_restore_{timestamp}.db"
            try:
                shutil.copy2("budget.db", temp_backup)
                print(f"DEBUG: Создана временная резервная копия: {temp_backup}")
            except Exception as copy_error:
                print(f"DEBUG: Не удалось создать временную резервную копию: {copy_error}")
                if not messagebox.askyesno(
                    "Предупреждение",
                    f"Не удалось создать временную резервную копию:\n{copy_error}\n\n"
                    "Продолжить восстановление без резервной копии?",
                    parent=self.parent
                ):
                    return
            
            try:
                shutil.copy2(backup_path, "budget.db")
            except Exception as restore_error:
                messagebox.showerror(
                    "Ошибка восстановления",
                    f"Не удалось восстановить базу данных:\n{restore_error}",
                    parent=self.parent
                )
                return
            
            info_text = (
                f"✅ База данных восстановлена\n\n"
                f"📁 Из файла: {os.path.basename(backup_path)}\n"
                f"📏 Размер: {file_size / 1024:.1f} КБ\n"
                f"🔄 Автоматическая резервная копия создана: {temp_backup}\n\n"
                f"Программа будет перезапущена для применения изменений."
            )
            
            messagebox.showinfo("Восстановление завершено", info_text, parent=self.parent)
            self._restart_application()
            
        except Exception as e:
            try:
                messagebox.showerror("Ошибка", f"Не удалось восстановить базу данных:\n{str(e)}", parent=self.parent)
            except:
                print(f"ERROR: Failed to restore backup: {e}")

    def _restart_application(self):
        """Перезапускает приложение."""
        import sys
        
        try:
            restart_file = ".restart_flag"
            with open(restart_file, "w") as f:
                f.write("1")
            
            messagebox.showinfo(
                "Перезапуск", 
                "База данных восстановлена.\n\n"
                "Пожалуйста, перезапустите приложение вручную для применения изменений.",
                parent=self.parent
            )
            
            self.parent.destroy()
            
        except Exception as e:
            try:
                messagebox.showerror(
                    "Ошибка перезапуска", 
                    f"Произошла ошибка при перезапуске:\n{str(e)}",
                    parent=self.parent
                )
            except:
                print(f"ERROR: Failed to restart application: {e}")
    
    # ----- Сообщение в строке статуса -----
    def show_status_message(self, message, duration_ms=3000, message_type="info", icon=""):
        """Показывает сообщение в строке статуса."""
        if hasattr(self, '_status_message_timer'):
            try:
                self.parent.after_cancel(self._status_message_timer)
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
        
        self._status_message_timer = self.parent.after(
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
    
    # ---- Создаем интерфейс (обновленный) ----
    def _init_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        
        
        # Подсказка для нового пользователя
        if not self.db.get_accounts():
            welcome_label = ttk.Label(main_frame, 
                                     text="👋 Добро пожаловать! Начните с создания счетов и категорий в меню 'Настройки'",
                                     font=("TkDefaultFont", 10, "bold"),
                                     foreground="blue")
            welcome_label.pack(pady=5)

        # Кнопка для быстрого доступа к операциям
        quick_access_frame = ttk.Frame(main_frame)
        quick_access_frame.pack(fill="x", pady=5)
        
        ttk.Button(quick_access_frame, text="📝 Добавить операции", 
                  command=self._open_operations_dialog,
                  width=25).pack(side="left", padx=5)
        
        ttk.Button(quick_access_frame, text="📊 Дашборд", 
                  command=self._open_dashboard,
                  width=20).pack(side="left", padx=5)
        
        ttk.Button(quick_access_frame, text="💳 Кредитные карты", 
                  command=self._open_credit_cards,
                  width=20).pack(side="right", padx=5)
                  
        ttk.Button(quick_access_frame, text="Обновить данные", 
                  command=self._post_dialog_update,
                  width=20).pack(side="right", padx=5)

        # --- Балансы (оставляем только это) ---
        balance_frame = ttk.LabelFrame(main_frame, text="Балансы счетов")
        balance_frame.pack(fill="x", pady=10, padx=5)
        
        # Общий баланс
        self.total_balance_label = ttk.Label(balance_frame, text="Общий Баланс: 0.00 ₽", 
                                           font=("TkDefaultFont", 18, "bold"), 
                                           anchor="center")
        self.total_balance_label.pack(fill="x", pady=(10, 5))
        
        # Разделитель
        separator = ttk.Separator(balance_frame, orient="horizontal")
        separator.pack(fill="x", padx=20, pady=5)
        
        # Индивидуальные балансы
        self.individual_balances_frame = ttk.Frame(balance_frame)
        self.individual_balances_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        # --- Фрейм для двух диаграмм (рядом) ---
        charts_frame = ttk.Frame(main_frame)
        charts_frame.pack(fill="both", expand=True, pady=10, padx=5)
        
        # Круговая диаграмма расходов (СЛЕВА)
        pie_chart_frame = ttk.LabelFrame(charts_frame, text="Анализ расходов")
        pie_chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self.pie_chart = PieChartWidget(pie_chart_frame, self.db)
        self.pie_chart.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Линейный график доходов/расходов (СПРАВА)
        line_chart_frame = ttk.LabelFrame(charts_frame, text="Динамика доходов/расходов")
        line_chart_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.line_chart = IncomeExpenseChart(line_chart_frame, self.db)
        self.line_chart.pack(fill="both", expand=True, padx=5, pady=5)
        
                
        
        # Информационная панель
        # info_frame = ttk.LabelFrame(main_frame, text="Быстрый доступ")
        # info_frame.pack(fill="x", pady=10, padx=5)
        
        # info_text = "• Настройки → Управление счетами и категориями\n"
        # info_text += "• Операции → Добавление и просмотр транзакций\n"
        # info_text += "• Кредиты → Управление кредитными картами и займами\n"
        # info_text += "• Отчеты → Дашборд и аналитика"
        
        # self.info_label = ttk.Label(info_frame, 
                                   # text=info_text,
                                   # font=("TkDefaultFont", 9),
                                   # justify="left",
                                   # foreground="gray")
        # self.info_label.pack(pady=10, padx=10)
        
        
        # self.status_bar = ttk.Label(self.parent, text="Готово.", relief=tk.SUNKEN, anchor="w")
        # self.status_bar.pack(side="bottom", fill="x")
     
    
    # --- Обновление окон/данных ---
    # индиктор загрузки 
    def show_loading(self, text="Загрузка..."):
        """Показывает индикатор загрузки."""
        if not hasattr(self, 'loading_indicator') or self.loading_indicator is None:
            self.loading_indicator = LoadingIndicator(self.parent)
        
        # Используем метод start() нового класса
        self.loading_indicator.start(text)

    def hide_loading(self):
        """Скрывает индикатор загрузки."""
        if hasattr(self, 'loading_indicator') and self.loading_indicator is not None:
            self.loading_indicator.stop()
            self.loading_indicator = None
        
    def _post_dialog_update(self):
        """Обновляет данные и отображение после закрытия диалога."""
        # Показываем индикатор
        self.show_loading("Обновление данных...")
        
        # Обновляем статус бар
        self.status_bar.config(text="⏳ Обновление данных...")
        
        # Запускаем обновление в отдельном потоке
        def update_in_thread():
            try:
                self._load_all_data()
                self.parent.after(0, self._finish_update_ui)
            except Exception as e:
                print(f"DEBUG: Error in update thread: {e}")
                self.parent.after(0, lambda: self._handle_update_error(e))
        
        thread = threading.Thread(target=update_in_thread, daemon=True)
        thread.start()

    def _finish_update_ui(self):
        """Завершает обновление UI."""
        try:
            self._update_display()
            
            # Обновляем графики
            if hasattr(self, 'pie_chart'):
                self.pie_chart.update_chart()
            if hasattr(self, 'line_chart'):
                self.line_chart.update_chart()
            
            # Получаем window_manager из приложения
            # Предполагается, что window_manager доступен как атрибут главного приложения
            if hasattr(self.parent, 'window_manager'):
                window_manager = self.parent.window_manager
                
                # Обновляем все открытые окна через window_manager
                open_windows = window_manager.get_open_windows()
                
                for window_id, window in open_windows.items():
                    if window and window.winfo_exists():
                        try:
                            # Проверяем наличие метода обновления у самого окна
                            if hasattr(window, '_post_dialog_update'):
                                window._post_dialog_update()
                            elif hasattr(window, '_update_dashboard_period'):
                                window._update_dashboard_period()
                            elif hasattr(window, 'load_accounts_into_tree'):
                                window.load_accounts_into_tree()
                            elif hasattr(window, 'load_categories_into_tree'):
                                window.load_categories_into_tree()
                            elif hasattr(window, '_update_display'):
                                window._update_display()
                            
                            # Также пробуем обновить frame instance внутри окон (если есть)
                            elif hasattr(window, '_frame_instance'):
                                frame_instance = window._frame_instance
                                if hasattr(frame_instance, 'refresh'):
                                    frame_instance.refresh()
                                elif hasattr(frame_instance, 'update_data'):
                                    frame_instance.update_data()
                        except Exception as e:
                            print(f"DEBUG: Error updating {window_id} window: {e}")
            
        except Exception as e:
            print(f"DEBUG: Error in _finish_update_ui: {e}")
        finally:
            # Всегда скрываем индикатор
            self.hide_loading()
            
            # Обновляем статус бар
            self.status_bar.config(text="✅ Данные обновлены")
            
            # Возвращаем стандартный статус через 2 секунды
            self.parent.after(2000, self._reset_status_to_ready)
        
    def _handle_update_error(self, error):
        """Обрабатывает ошибку обновления."""
        self.hide_loading()
        
        # Обновляем статус бар
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text="❌ Ошибка обновления данных")
        
        print(f"DEBUG: Error updating data: {error}")
        
        # Возвращаем стандартный статус через 3 секунды
        self.parent.after(3000, self._reset_status_to_ready)
    
    # ---- Открытие диалогов (добавляем новый метод) ----
    def _open_operations_dialog(self, show_filters=False):
        return self.parent.window_manager.open_window('operations', self.db)
           
    def _open_account_management(self):
        return self.parent.window_manager.open_window('accounts', self.db)
    
    def _open_category_management(self):
        return self.parent.window_manager.open_window('categories', self.db)
    
    def _open_credit_cards(self):
        return self.parent.window_manager.open_window('credit_cards', self.db)
    
    def _open_loan_management(self):
        return self.parent.window_manager.open_window('loans', self.db)
    
    def _open_dashboard(self):
        """Особая логика для дашборда - он не Toplevel"""
        from ui.dashboard import SimpleDashboard
        
        # Проверяем открыт ли уже дашборд
        if hasattr(self, 'dashboard_window') and self.dashboard_window:
            if self.dashboard_window.winfo_exists():
                self.dashboard_window.lift()
                self.dashboard_window.focus_set()
                return self.dashboard_window
            else:
                # Окно было закрыто
                self.dashboard_window = None
        
        # Создаем новый дашборд
        self.dashboard_window = SimpleDashboard(self.parent, self.db)
        
        # Настраиваем закрытие
        def on_close():
            if hasattr(self, 'dashboard_window'):
                self.dashboard_window = None
        
        self.dashboard_window.protocol("WM_DELETE_WINDOW", on_close)
        return self.dashboard_window
    
    
    
                
    def update_with_loading(self):
        """Обновляет данные с индикатором загрузки."""
        def update_task():
            try:
                # Показываем индикатор
                self.parent.after(0, lambda: self.show_loading("Обновление данных..."))
                
                # Обновляем данные
                self._load_all_data()
                self._update_display()
                
                # Обновляем графики
                if hasattr(self, 'pie_chart'):
                    self.pie_chart.update_chart()
                if hasattr(self, 'line_chart'):
                    self.line_chart.update_chart()
                
            except Exception as e:
                print(f"DEBUG: Error in update_with_loading: {e}")
            finally:
                # Скрываем индикатор
                self.parent.after(0, self.hide_loading)
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=update_task, daemon=True)
        thread.start()
        
    # --- Обновление окон/данных ---    
    def _load_all_data(self):
        """Загружает все данные из БД (вызывается из отдельного потока)."""
        try:
            # Загружаем данные счетов
            accounts = self.db.get_accounts()
            if accounts:
                self.accounts_data = {acc[0]: {"name": acc[1], "type": acc[2], "balance": acc[4]} 
                                     for acc in accounts}
            
            # Загружаем все категории
            all_categories = self.db.get_categories(include_subcategories=True)
            
            if all_categories:
                # Сохраняем данные категорий для быстрого доступа
                self.all_categories_data = {cat[0]: cat for cat in all_categories}
                self.categories_by_name = {cat[1]: cat[0] for cat in all_categories}
            
            # Загружаем категории доходов и расходов отдельно
            categories_income = self.db.get_categories(type='income', include_subcategories=True)
            if categories_income:
                self.categories_income = {cat[0]: cat[1] for cat in categories_income}
            
            categories_expense = self.db.get_categories(type='expense', include_subcategories=True)
            if categories_expense:
                self.categories_expense = {cat[0]: cat[1] for cat in categories_expense}
            
            return True
            
        except Exception as e:
            print(f"DEBUG: Error in _load_all_data: {e}")
            return False

    def _update_category_and_account_combos(self, event=None):
        """Обновляет списки категорий с учетом иерархии (оставляем для совместимости)."""
        if not hasattr(self, 'type_combo_var'):
            return
            
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
        
        categories_by_id = {}
        for cat_id, name, cat_type, budget, parent_id, level, path in categories:
            categories_by_id[cat_id] = {
                'name': name,
                'type': cat_type,
                'parent_id': parent_id,
                'level': level
            }
        
        for cat_id, name, cat_type, budget, parent_id, level, path in categories:
            if level == 0:
                display_name = name
                display_names.append(display_name)
                self.category_id_by_display_name[display_name] = cat_id
        
        for cat_id, name, cat_type, budget, parent_id, level, path in categories:
            if level > 0:
                indent = "    " * level
                display_name = f"{indent}{name}"
                display_names.append(display_name)
                self.category_id_by_display_name[display_name] = cat_id
        
        if hasattr(self, 'category_combo'):
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
        
        if hasattr(self, 'account_combo'):
            account_names = [acc_info['name'] for acc_info in self.accounts_data.values()]
            self.account_combo['values'] = account_names
            
            if current_account in account_names:
                self.account_combo_var.set(current_account)
            elif account_names:
                self.account_combo_var.set(account_names[0])
            else:
                self.account_combo_var.set("")
        
        if hasattr(self, 'type_combo_var'):
            if current_type in ["Доход", "Расход"]:
                self.type_combo_var.set(current_type)
            else:
                self.type_combo_var.set("Расход")

    # --- Обновление отображения (упрощенное) ---
    def _update_display(self):
        """Обновляет все элементы отображения."""
        self._update_total_balance_label()
        self._update_individual_balances()
        
        # Обновляем круговую диаграмму
        if hasattr(self, 'pie_chart'):
            try:
                self.pie_chart.update_chart()
            except Exception as e:
                print(f"DEBUG: Error updating pie chart in _update_display: {e}")
        
        # Обновляем линейный график
        if hasattr(self, 'line_chart'):
            try:
                self.line_chart.update_chart()
            except Exception as e:
                print(f"DEBUG: Error updating line chart in _update_display: {e}")
        
        if not self.accounts_data:
            self.show_status_message("Создайте свой первый счет для начала работы", 5000)
        
    def _update_total_balance_label(self):
        """Обновляет метку общего баланса."""
        total_balance = sum(acc_info['balance'] for acc_info in self.accounts_data.values())
        self.total_balance_label.config(text=f"Общий Баланс: {total_balance:.2f} ₽")

    def _update_individual_balances(self):
        """Обновляет метки с балансами по каждому счету (теперь включая кредитные)"""
        for widget in self.individual_balances_frame.winfo_children():
            widget.destroy()
        
        if not self.accounts_data:
            ttk.Label(self.individual_balances_frame, 
                     text="Счетов пока нет. Создайте первый счет через 'Управление Счетами'",
                     font=("TkDefaultFont", 9, "italic"),
                     foreground="gray").pack(pady=10)
            return
        
        regular_accounts = []
        credit_accounts = []
        
        for account_id, acc_info in self.accounts_data.items():
            if "Контрагент:" in acc_info['name']:
                continue
            
            if acc_info['type'] == 'Credit Card':
                credit_accounts.append((account_id, acc_info))
            else:
                regular_accounts.append((account_id, acc_info))
        
        regular_accounts.sort(key=lambda x: x[1]['balance'])
        credit_accounts.sort(key=lambda x: x[1]['balance'])
        
        # Создаем таблицу балансов
        balances_grid = ttk.Frame(self.individual_balances_frame)
        balances_grid.pack(fill="x", expand=True)
        
        # Обычные счета
        if regular_accounts:
            regular_frame = ttk.LabelFrame(balances_grid, text="💳 Обычные счета")
            regular_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
            
            for account_id, acc_info in regular_accounts:
                balance_frame = ttk.Frame(regular_frame)
                balance_frame.pack(fill="x", pady=2, padx=5)
                
                ttk.Label(balance_frame, text=acc_info['name'], 
                         font=("TkDefaultFont", 9),
                         width=20, anchor="w").pack(side="left")
                
                balance_text = f"{acc_info['balance']:,.2f} ₽"
                balance_label = ttk.Label(balance_frame, text=balance_text,
                                         font=("TkDefaultFont", 9, "bold"),
                                         width=15, anchor="e")
                balance_label.pack(side="right")
                
                if acc_info['balance'] < 0:
                    balance_label.config(foreground="orange")
                else:
                    balance_label.config(foreground="green")
        else:
            ttk.Label(balances_grid, text="Нет обычных счетов",
                     font=("TkDefaultFont", 9, "italic"),
                     foreground="gray").pack(side="left", padx=20, pady=10)
        
        # Кредитные карты
        if credit_accounts:
            credit_frame = ttk.LabelFrame(balances_grid, text="💳 Кредитные карты")
            credit_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
            
            for account_id, acc_info in credit_accounts:
                account_data = self.db.get_account_by_id(account_id)
                if account_data:
                    credit_limit = float(account_data[5])
                    available = credit_limit + acc_info['balance']
                    utilization = (abs(acc_info['balance']) / credit_limit * 100) if credit_limit > 0 else 0
                    
                    balance_frame = ttk.Frame(credit_frame)
                    balance_frame.pack(fill="x", pady=2, padx=5)
                    
                    # Название карты
                    ttk.Label(balance_frame, text=acc_info['name'], 
                             font=("TkDefaultFont", 9),
                             width=20, anchor="w").pack(side="left")
                    
                    # Долг
                    debt_text = f"Долг: {abs(acc_info['balance']):,.2f} ₽"
                    debt_label = ttk.Label(balance_frame, text=debt_text,
                                          font=("TkDefaultFont", 9),
                                          width=15, anchor="e")
                    debt_label.pack(side="right")
                    
                    if utilization > 80:
                        debt_label.config(foreground="red")
                    elif utilization > 50:
                        debt_label.config(foreground="orange")
                    else:
                        debt_label.config(foreground="green")
                    
                    # Доступно
                    available_frame = ttk.Frame(credit_frame)
                    available_frame.pack(fill="x", pady=(0, 5), padx=5)
                    
                    ttk.Label(available_frame, text="Доступно:", 
                             font=("TkDefaultFont", 8),
                             foreground="gray").pack(side="left")
                    
                    available_text = f"{available:,.2f} ₽ / {credit_limit:,.2f} ₽"
                    available_label = ttk.Label(available_frame, text=available_text,
                                               font=("TkDefaultFont", 8),
                                               anchor="e")
                    available_label.pack(side="right")
                    
                    if available < credit_limit * 0.2:
                        available_label.config(foreground="red")
                    elif available < credit_limit * 0.5:
                        available_label.config(foreground="orange")
                    else:
                        available_label.config(foreground="green")
        else:
            ttk.Label(balances_grid, text="Нет кредитных карт",
                     font=("TkDefaultFont", 9, "italic"),
                     foreground="gray").pack(side="right", padx=20, pady=10)
    
    # --- Удалены методы для операций и транзакций (перенесены в OperationsDialog) ---
    # _add_transaction, _delete_selected_transactions, _show_transaction_details,
    # _copy_transaction, _edit_transaction, _get_transaction_by_id, _clear_input_fields,
    # _create_filter_menus, _update_filter_menus_content, _show_type_filter_menu,
    # _show_category_filter_menu, _show_account_filter_menu, _show_date_filter_menu,
    # _open_date_range_dialog, _apply_column_filter, _reset_all_filters, 
    # _update_transactions_tree
    
    def refresh_accounts_data(self):
        """Принудительно обновляет данные счетов из БД"""
        self.accounts_data = {acc[0]: {"name": acc[1], "type": acc[2], "balance": acc[4]} 
                         for acc in self.db.get_accounts()}
    
    # --- Экспорт/Импорт ---
    def _export_to_csv(self):
        """Экспортирует транзакции в CSV файл."""
        try:
            import tkinter.filedialog as fd
            
            result = messagebox.askyesnocancel(
                "Экспорт транзакций", 
                "Экспортировать все транзакции?\n\n"
                "Да - все транзакции\n"
                "Нет - только за выбранный период\n"
                "Отмена - отменить экспорт"
            )
            
            date_from = None
            date_to = None
            
            if result is None:
                return
            elif not result:
                dialog = DateRangeDialog(self.parent)
                if not dialog.result:
                    return
                date_from, date_to = dialog.result
            
            filename = fd.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Сохранить транзакции как CSV"
            )
            
            if not filename:
                return
            
            if self.db.export_transactions_to_csv(filename, date_from, date_to):
                self.show_status_message(f"Транзакции экспортированы в {filename}", 5000)
                messagebox.showinfo("Экспорт завершен", f"Транзакции успешно экспортированы в:\n{filename}")
            else:
                messagebox.showerror("Ошибка", "Не удалось экспортировать транзакции")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте: {e}")

    def _import_from_csv(self):
        """Импортирует транзакции из CSV файла с прогресс-баром."""
        try:
            import tkinter.filedialog as fd
            
            if not messagebox.askyesno(
                "Импорт транзакций", 
                "Внимание! При импорте:\n\n"
                "• Будут созданы новые транзакции\n"
                "• Балансы счетов будут обновлены\n"
                "• Несуществующие счета и категории будут созданы автоматически\n\n"
                "Импорт может занять несколько секунд.\nПродолжить?",
                parent=self.parent
            ):
                return
            
            filename = fd.askopenfilename(
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Выберите CSV файл для импорта"
            )
            
            if not filename:
                return
            
            progress_window = tk.Toplevel(self.parent)
            progress_window.title("Импорт данных")
            progress_window.geometry("400x150")
            
            progress_window.transient(self.parent)
            progress_window.grab_set()
            
            ttk.Label(progress_window, text="Подготовка к импорту...", 
                     font=("TkDefaultFont", 10, "bold")).pack(pady=10)
            
            self.progress_status = ttk.Label(progress_window, text="", 
                                           font=("TkDefaultFont", 9))
            self.progress_status.pack(pady=5)
            
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(progress_window, variable=progress_var, 
                                         maximum=100, length=350)
            progress_bar.pack(fill="x", padx=20, pady=10)
            
            def run_import():
                try:
                    def update_progress(status, percent):
                        if progress_window.winfo_exists():
                            progress_window.after(0, lambda: update_ui(status, percent))
                    
                    def update_ui(status, percent):
                        self.progress_status.config(text=status)
                        progress_var.set(percent)
                        progress_window.update()
                    
                    imported_count = self.db.import_transactions_from_csv(filename, update_progress)
                    
                    progress_window.after(0, lambda: finish_import(imported_count))
                    
                except Exception as e:
                    progress_window.after(0, lambda: finish_import(0, str(e)))
            
            def finish_import(count, error=None):
                progress_window.destroy()
                
                if error:
                    messagebox.showerror(
                        "Ошибка импорта", 
                        f"Произошла ошибка при импорте:\n{error}",
                        parent=self.parent
                    )
                elif count > 0:
                    self.show_status_message(f"Успешно импортировано {count} транзакций", 5000)
                    self._load_all_data()
                    self._update_display()
                    
                    messagebox.showinfo(
                        "Импорт завершен", 
                        f"✅ Успешно импортировано {count} транзакций\n\n"
                        "Все счета и категории были автоматически созданы при необходимости.",
                        parent=self.parent
                    )
                else:
                    messagebox.showwarning(
                        "Импорт", 
                        "Не удалось импортировать транзакции.\n"
                        "Возможные причины:\n"
                        "• Неверный формат CSV файла\n"
                        "• Файл пустой\n"
                        "• Все транзакции уже существуют",
                        parent=self.parent
                    )
            
            import_thread = threading.Thread(target=run_import, daemon=True)
            import_thread.start()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при импорте: {e}")
    
    # ---- Универсальные методы (оставляем, они используются в других диалогах) ----
    def setup_treeview_management(self, parent, treeview, delete_callback, edit_callback=None, additional_commands=None):
        """
        Универсальная настройка управления Treeview для всех диалогов
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
        
        print(f"DEBUG: Treeview management setup complete for {treeview}")
        
    def delete_selected_items_universal(self, treeview, item_type, delete_callback, refresh_callback=None, parent=None, additional_refresh_callbacks=None):
        """
        Универсальный метод для удаления выбранных элементов из любого Treeview
        """
        selected_items = treeview.selection()
        if not selected_items:
            messagebox.showinfo("Удаление", f"Выберите {item_type} для удаления.", parent=parent or self.parent)
            return False
        
        if not messagebox.askyesno("Подтверждение удаления", 
                                  f"Вы уверены, что хотите удалить {len(selected_items)} выбранных {item_type}?",
                                  parent=parent or self.parent):
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
            messagebox.showinfo("Результат", message_text, parent=parent or self.parent)
            
            if refresh_callback:
                refresh_callback()
            
            if additional_refresh_callbacks:
                for callback in additional_refresh_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        print(f"DEBUG: Error in additional refresh callback: {e}")
            
            self._universal_refresh_after_delete(item_type)
            
            return True
        else:
            messagebox.showerror("Ошибка", f"Не удалось удалить выбранные {item_type}.", parent=parent or self.parent)
            return False

    def _universal_refresh_after_delete(self, item_type):
        """Универсальное обновление всех окон после удаления"""
        print(f"DEBUG: Universal refresh after deleting {item_type}")
        
        try:
            self._load_all_data()
            self._update_display()
            print("DEBUG: Main window refreshed")
        except Exception as e:
            print(f"DEBUG: Error refreshing main window: {e}")
        
        try:
            if hasattr(self.parent, 'dashboard_window') and self.parent.dashboard_window and self.parent.dashboard_window.winfo_exists():
                self.parent.dashboard_window._update_dashboard_period()
                print("DEBUG: Dashboard refreshed")
        except Exception as e:
            print(f"DEBUG: Error refreshing dashboard: {e}")
        
        try:
            if hasattr(self.parent, 'loan_management_window') and self.parent.loan_management_window and self.parent.loan_management_window.winfo_exists():
                if hasattr(self.parent.loan_management_window, 'load_loans'):
                    self.parent.loan_management_window.load_loans()
                    print("DEBUG: Loans window refreshed")
        except Exception as e:
            print(f"DEBUG: Error refreshing loans window: {e}")
        
        try:
            # Обновляем окно операций, если оно открыто
            if self.parent.open_windows.get('operations') and self.parent.open_windows['operations'].winfo_exists():
                self.parent.open_windows['operations']._update_display()
                print("DEBUG: Operations dialog refreshed")
        except Exception as e:
            print(f"DEBUG: Error refreshing operations dialog: {e}")
        
        print("DEBUG: Universal refresh completed")
        
    # --- Методы для _create_menu ---
    def get_category_statistics_report(self):
        """Генерирует отчет по категориям с учетом иерархии."""
        try:
            stats = self.db.get_category_statistics(include_subcategories=True)
            
            if not stats:
                return "📭 Нет данных для формирования отчета по категориям."
            
            report_text = "📊 ОТЧЕТ ПО КАТЕГОРИЯМ\n"
            report_text += "=" * 50 + "\n\n"
            
            main_categories = {}
            total_expense_all = 0
            total_income_all = 0
            
            for cat_id, name, cat_type, budget, parent_id, total_expense, total_income, count, avg_amount in stats:
                if parent_id is None:
                    main_categories[name] = {
                        'id': cat_id,
                        'type': cat_type,
                        'budget': budget,
                        'expense': total_expense,
                        'income': total_income,
                        'transaction_count': count,
                        'avg_amount': avg_amount,
                        'subcategories': []
                    }
                    total_expense_all += total_expense
                    total_income_all += total_income
                else:
                    parent_name = None
                    for cat in stats:
                        if cat[0] == parent_id:
                            parent_name = cat[1]
                            break
                    
                    if parent_name and parent_name in main_categories:
                        main_categories[parent_name]['subcategories'].append({
                            'id': cat_id,
                            'name': name,
                            'type': cat_type,
                            'budget': budget,
                            'expense': total_expense,
                            'income': total_income,
                            'transaction_count': count,
                            'avg_amount': avg_amount
                        })
            
            if not main_categories:
                return "📭 Нет данных по категориям для формирования отчета."
            
            sorted_categories = sorted(
                main_categories.items(),
                key=lambda x: x[1]['expense'],
                reverse=True
            )
            
            for main_cat, data in sorted_categories:
                category_type = "💸 РАСХОД" if data['type'] == 'expense' else "💰 ДОХОД"
                
                report_text += f"{category_type}: {main_cat}\n"
                report_text += f"├─ Всего расходов: {data['expense']:,.2f} ₽\n"
                report_text += f"├─ Всего доходов: {data['income']:,.2f} ₽\n"
                
                if data['budget'] > 0 and data['type'] == 'expense':
                    budget_usage = (data['expense'] / data['budget'] * 100) if data['budget'] > 0 else 0
                    report_text += f"├─ Плановый бюджет: {data['budget']:,.2f} ₽ (использовано: {budget_usage:.1f}%)\n"
                
                if data['transaction_count'] > 0:
                    report_text += f"├─ Количество операций: {data['transaction_count']}\n"
                    if data['avg_amount'] and data['avg_amount'] > 0:
                        report_text += f"├─ Средняя сумма: {data['avg_amount']:,.2f} ₽\n"
                
                if data['expense'] > 0 and total_expense_all > 0:
                    expense_percent = (data['expense'] / total_expense_all * 100)
                    report_text += f"├─ % от общих расходов: {expense_percent:.1f}%\n"
                
                if data['subcategories']:
                    report_text += "└─ 📋 Подкатегории:\n"
                    
                    sorted_subcats = sorted(
                        data['subcategories'],
                        key=lambda x: x['expense'],
                        reverse=True
                    )
                    
                    for i, subcat in enumerate(sorted_subcats):
                        connector = "├─" if i < len(sorted_subcats) - 1 else "└─"
                        report_text += f"   {connector} {subcat['name']}:\n"
                        report_text += f"      💸 {subcat['expense']:,.2f} ₽ | 💰 {subcat['income']:,.2f} ₽\n"
                        if subcat['transaction_count'] > 0:
                            report_text += f"      📊 Операций: {subcat['transaction_count']}\n"
                
                report_text += "\n"
            
            report_text += "=" * 50 + "\n"
            report_text += "📈 ИТОГО:\n"
            report_text += f"💸 Общие расходы: {total_expense_all:,.2f} ₽\n"
            report_text += f"💰 Общие доходы: {total_income_all:,.2f} ₽\n"
            
            if total_income_all > 0 and total_expense_all > 0:
                savings = total_income_all - total_expense_all
                savings_percent = (savings / total_income_all * 100) if total_income_all > 0 else 0
                
                report_text += f"📊 Чистые сбережения: {savings:+,.2f} ₽ ({savings_percent:+.1f}% от доходов)\n"
            
            report_text += f"\n📋 Всего основных категорий: {len(main_categories)}\n"
            
            total_subcategories = sum(len(data['subcategories']) for data in main_categories.values())
            report_text += f"📋 Всего подкатегорий: {total_subcategories}\n"
            report_text += f"📋 Всего категорий (включая подкатегории): {len(main_categories) + total_subcategories}\n"
            
            return report_text
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"DEBUG: Error generating category report: {e}")
            print(f"DEBUG: Traceback:\n{error_details}")
            return f"❌ Ошибка при формировании отчета:\n{str(e)}\n\nПодробности в консоли."
            
    # -- Заглушки --      
    def _show_credit_analytics(self):
        """Аналитика по кредитам (заглушка)."""
        messagebox.showinfo("В разработке", "Аналитика по кредитам в разработке", parent=self.parent)