# исходна весрия Tkinter (польность рабочая) 
import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
import threading



# Глобальная блокировка для синхронизации доступа к БД
db_lock = threading.Lock()

DATABASE_NAME = 'budget.db'

class DatabaseManager:
    def __init__(self, db_name=DATABASE_NAME):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self._create_tables()
        self._create_system_data()
        # self._add_credit_card_columns()
        self._add_missing_columns()
        # self._migrate_categories_table()  # <-- Добавить миграцию для категорий
        
    def _add_missing_columns(self):
        """Добавляет недостающие столбцы к таблицам."""
        columns_to_add = [
            ("accounts", "credit_limit", "REAL DEFAULT 0.0"),
            ("accounts", "payment_due_day", "INTEGER DEFAULT 1"),
            ("accounts", "min_payment_percent", "REAL DEFAULT 5.0"),
            ("accounts", "last_payment_date", "TEXT"),
            ("transactions", "quantity", "REAL DEFAULT 1.0"),
            ("categories", "parent_id", "INTEGER DEFAULT NULL")  # ← ДОБАВИТЬ ЭТО
        ]
        
        for table_name, column_name, column_type in columns_to_add:
            try:
                self.conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                print(f"DEBUG: Added column {column_name} to {table_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    pass  # Колонка уже существует
                elif "no such table" in str(e).lower():
                    pass  # Таблица еще не создана (будет создана позже)
                else:
                    print(f"INFO: Column {column_name} in {table_name}: {e}")
            except Exception as e:
                print(f"WARNING: Error adding column {column_name} to {table_name}: {e}")
        
        try:
            self.conn.commit()
        except:
            pass
        print("DEBUG: Database columns updated")
    
    # def _migrate_categories_table(self):
        # """Добавляет поле parent_id к существующей таблице categories."""
        # try:
            # # Проверяем, существует ли уже поле parent_id
            # self.conn.execute("SELECT parent_id FROM categories LIMIT 1")
            # print("DEBUG: Поле parent_id уже существует в таблице categories")
        # except sqlite3.OperationalError:
            # # Если поля нет - добавляем
            # try:
                # self.conn.execute("ALTER TABLE categories ADD COLUMN parent_id INTEGER DEFAULT NULL")
                # self.conn.commit()
                # print("DEBUG: Добавлено поле parent_id в таблицу categories")
            # except Exception as e:
                # print(f"DEBUG: Ошибка при добавлении parent_id: {e}")
    
    def _create_system_data(self):
        """Создает только системно необходимые данные."""
        # Проверяем существование категории без parent_id
        try:
            result = self._execute_query(
                "SELECT id, name FROM categories WHERE name = ?",
                ("Сверка Баланса",),
                fetch_one=True
            )
            if not result:
                # Добавляем категорию (пока без parent_id)
                self._execute_query(
                    "INSERT INTO categories (name, type, budget_amount_monthly) VALUES (?, ?, ?)",
                    ("Сверка Баланса", "expense", 0.0)
                )
                print("DEBUG: Created 'Сверка Баланса' category")
        except Exception as e:
            print(f"ERROR creating system data: {e}")
            # Если таблица еще не имеет всех колонок, создаем простым запросом
            try:
                self.conn.execute(
                    "INSERT OR IGNORE INTO categories (name, type, budget_amount_monthly) VALUES (?, ?, ?)",
                    ("Сверка Баланса", "expense", 0.0)
                )
                self.conn.commit()
            except:
                pass
            
    def get_loans(self):
        """Возвращает список всех займов"""
        try:
            # Сначала проверяем существование таблицы
            loans = self._execute_query(
                "SELECT id, account_id, contact_name, loan_type, loan_amount, outstanding_amount, issue_date, due_date, description FROM loans", 
                fetch_all=True
            )
            return loans
        except sqlite3.OperationalError as e:
            # Таблица может не существовать при первом запуске
            print(f"INFO: loans table doesn't exist yet: {e}")
            return []
            
    def _execute_query(self, query, params=(), fetch_all=False, fetch_one=False):
        """Выполняет запрос к БД с блокировкой для потокобезопасности"""
        with db_lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                if fetch_one:
                    return cursor.fetchone()
                if fetch_all:
                    return cursor.fetchall()
                return True
            except sqlite3.Error as e:
                print(f"Database error executing query: '{query}' with params: {params}. Error: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()

    def _create_tables(self):
        """Создает все таблицы базы данных."""
        print("DEBUG: Creating database tablesCreating database tables...")
        
        self._execute_query('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK(type IN ('Cash', 'Bank Account', 'Credit Card')),
                initial_balance REAL DEFAULT 0.0,
                current_balance REAL DEFAULT 0.0,
                credit_limit REAL DEFAULT 0.0,
                payment_due_day INTEGER DEFAULT 1,
                min_payment_percent REAL DEFAULT 5.0,
                last_payment_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self._execute_query('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                budget_amount_monthly REAL DEFAULT 0.0
            )
        ''')
        # Создаем внешний ключ отдельно (чтобы избежать проблем при создании таблицы)
        try:
            self._execute_query('''
                CREATE INDEX IF NOT EXISTS fk_categories_parent 
                ON categories(parent_id)
            ''')
        except:
            pass
        
        self._execute_query('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('доход', 'расход', 'корректировка')),
                category_id INTEGER,
                description TEXT,
                account_id INTEGER NOT NULL,
                quantity REAL DEFAULT 1.0,  -- ← НОВОЕ ПОЛЕ ДЛЯ КОЛИЧЕСТВА
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        ''')
        
        self._execute_query('''
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                from_account_id INTEGER NOT NULL,
                to_account_id INTEGER NOT NULL,
                description TEXT,
                FOREIGN KEY (from_account_id) REFERENCES accounts(id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(id)
            )
        ''')
        
        self._execute_query('''
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                contact_name TEXT NOT NULL,
                loan_type TEXT NOT NULL CHECK (loan_type IN ('выдан', 'получен')),
                loan_amount REAL NOT NULL,
                outstanding_amount REAL NOT NULL,
                issue_date TEXT NOT NULL,
                due_date TEXT,
                description TEXT,
                transaction_id INTEGER,
                FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
            )
        ''')
        
        self._execute_query('''
            CREATE TABLE IF NOT EXISTS loan_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL,
                payment_date TEXT NOT NULL,
                payment_amount REAL NOT NULL,
                description TEXT,
                transaction_id INTEGER,
                FOREIGN KEY (loan_id) REFERENCES loans (id) ON DELETE CASCADE,
                FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE
            )
        ''')
        
        
         # Создаем индексы
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id)",
            "CREATE INDEX IF NOT EXISTS idx_categories_type ON categories(type)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_category_id ON transactions(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
            "CREATE INDEX IF NOT EXISTS idx_loans_issue_date ON loans(issue_date)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_quantity ON transactions(quantity)"
        ]
        
        for index_query in indexes:
            self._execute_query(index_query)
        
        print("DEBUG: Database tables created")

    # def _add_credit_card_columns(self):
        # """Просто добавляем столбцы если их нет."""
        # columns_to_add = [
            # ("ALTER TABLE accounts ADD COLUMN credit_limit REAL DEFAULT 0.0"),
            # ("ALTER TABLE accounts ADD COLUMN payment_due_day INTEGER DEFAULT 1"),
            # ("ALTER TABLE accounts ADD COLUMN min_payment_percent REAL DEFAULT 5.0"),
            # ("ALTER TABLE accounts ADD COLUMN last_payment_date TEXT"),
            # ("ALTER TABLE transactions ADD COLUMN quantity REAL DEFAULT 1.0")  # Добавляем поле quantity
        # ]
        
        # for alter_query in columns_to_add:
            # try:
                # self.conn.execute(alter_query)
                # print(f"DEBUG: Executed: {alter_query}")
            # except sqlite3.OperationalError as e:
                # # Игнорируем ошибку "duplicate column name"
                # if "duplicate column" not in str(e).lower():
                    # print(f"INFO: Column already exists or error: {e}")
            # except Exception as e:
                # print(f"WARNING: Error executing {alter_query}: {e}")
        
        # try:
            # self.conn.commit()
        # except:
            # pass  # Игнорируем ошибки коммита
    
    # --- Функции для работы со счетами ---
    def add_account(self, name, acc_type, initial_balance=0.0, credit_limit=0.0, 
                    payment_due_day=1, min_payment_percent=5.0):
        """Добавляет новый счет."""
        try:
            # Исправлено: используем единый метод выполнения запросов
            result = self._execute_query('''
                INSERT INTO accounts 
                (name, type, initial_balance, current_balance, credit_limit, 
                 payment_due_day, min_payment_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, acc_type, initial_balance, initial_balance, 
                  credit_limit, payment_due_day, min_payment_percent))
            return result
        except Exception as e:
            print(f"Error adding account: {e}")
            return False

    def get_accounts(self):
        """Получает все счета с ВСЕМИ полями."""
        try:
            # Используем единый метод _execute_query
            accounts = self._execute_query("""
                SELECT id, name, type, initial_balance, current_balance,
                       COALESCE(credit_limit, 0.0) as credit_limit,
                       COALESCE(payment_due_day, 1) as payment_due_day,
                       COALESCE(min_payment_percent, 5.0) as min_payment_percent,
                       last_payment_date
                FROM accounts 
                ORDER BY name
            """, fetch_all=True)
            
            # Отладочная информация
            print(f"DEBUG: get_accounts returned {len(accounts) if accounts else 0} accounts")
            if accounts:
                for account in accounts:
                    if account[2] == 'Credit Card':  # type
                        print(f"DEBUG: Credit Card {account[1]}: {len(account)} fields: {account}")
            
            return accounts
        except Exception as e:
            print(f"ERROR in get_accounts: {e}")
            import traceback
            traceback.print_exc()
            return []
        
    def get_account_by_id(self, account_id):
        """Получает полную информацию о счете."""
        result = self._execute_query('''
            SELECT id, name, type, initial_balance, current_balance,
                   credit_limit, payment_due_day, min_payment_percent,
                   last_payment_date
            FROM accounts WHERE id = ?
        ''', (account_id,), fetch_one=True)
        return result
        
    def get_credit_cards(self):
        """Получает все кредитные карты."""
        try:
            return self._execute_query("""
                SELECT id, name, type, initial_balance, current_balance, 
                       credit_limit, payment_due_day, min_payment_percent, last_payment_date
                FROM accounts 
                WHERE type = 'Credit Card'
                ORDER BY name
            """, fetch_all=True)
        except Exception as e:
            print(f"ERROR in get_credit_cards: {e}")
            return []
    
    def update_account(self, account_id, name, acc_type, initial_balance, 
                       credit_limit=0.0, payment_due_day=1, min_payment_percent=5.0):
        """Обновляет данные счета."""
        print(f"DEBUG DatabaseManager.update_account called:")
        print(f"  account_id: {account_id}")
        print(f"  name: {name}")
        print(f"  type: {acc_type}")
        print(f"  initial_balance: {initial_balance}")
        
        if acc_type == "Credit Card":
            print(f"  credit_limit: {credit_limit}")
            print(f"  payment_due_day: {payment_due_day}")
            print(f"  min_payment_percent: {min_payment_percent}")
        
        try:
            # Убираем блокировку временно для тестирования
            # with db_lock:
            if acc_type == "Credit Card":
                # Для кредитной карты обновляем все поля
                success = self._execute_query("""
                    UPDATE accounts 
                    SET name = ?, type = ?, initial_balance = ?, 
                        credit_limit = ?, payment_due_day = ?, min_payment_percent = ?
                    WHERE id = ?
                """, (name, acc_type, initial_balance, 
                      credit_limit, payment_due_day, min_payment_percent, account_id))
            else:
                # Для обычного счета обновляем только основные поля
                success = self._execute_query("""
                    UPDATE accounts 
                    SET name = ?, type = ?, initial_balance = ?
                    WHERE id = ?
                """, (name, acc_type, initial_balance, account_id))
            
            print(f"DEBUG: Update success: {success}")
            
            # Проверяем, что изменения действительно записались
            if success:
                updated_account = self._execute_query(
                    "SELECT * FROM accounts WHERE id = ?", 
                    (account_id,), 
                    fetch_one=True
                )
                print(f"DEBUG: Updated account data: {updated_account}")
            
            return success
                
        except Exception as e:
            print(f"ERROR in update_account: {e}")
            import traceback
            traceback.print_exc()
            return False    
            
    def get_account_by_name(self, name):
        """Получает счет по имени."""
        account = self._execute_query(
            "SELECT id, name, type, current_balance FROM accounts WHERE name = ?", 
            (name,), 
            fetch_one=True
        )
        if account:
            return (account[0], account[1], account[2], float(account[3]) if account[3] is not None else 0.0)
        return None

    def update_account_balance(self, account_id, amount_change):
        """Обновляет баланс счета."""
        # amount_change должен быть float
        try:
            amount_change = float(amount_change)
        except (ValueError, TypeError):
            print(f"Error: amount_change {amount_change} is not a number for account {account_id}")
            return False

        # Проверка существования счета
        account = self.get_account_by_id(account_id)
        if not account:
            print(f"Error: Account with ID {account_id} not found for balance update.")
            return False

        print(f"DEBUG: Updating balance for account ID {account_id} by {amount_change}")
        return self._execute_query(
            "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
            (amount_change, account_id)
        )
        
    def update_account_info(self, account_id, name, acc_type):
        """Обновляет только имя и тип счета (без изменения баланса)."""
        existing_account = self.get_account_by_id(account_id)
        if not existing_account:
            print(f"Error: Account with ID {account_id} not found for update.")
            return False
        
        # Проверяем уникальность имени
        if existing_account[1] != name:  # Если имя меняется
            existing_with_new_name = self.get_account_by_name(name)
            if existing_with_new_name and existing_with_new_name[0] != account_id:
                print(f"Error: Account with name '{name}' already exists. Cannot update to duplicate name.")
                return False

        print(f"DEBUG: Updating account ID {account_id}: Name='{name}', Type='{acc_type}'")
        return self._execute_query(
            "UPDATE accounts SET name = ?, type = ? WHERE id = ?",
            (name, acc_type, account_id)
        )
        
    def update_account_initial_balance(self, account_id, new_initial_balance):
        """Обновляет начальный баланс счета и пересчитывает текущий баланс."""
        try:
            new_initial_balance = float(new_initial_balance)
        except (ValueError, TypeError):
            print(f"Error: new_initial_balance {new_initial_balance} is not a number")
            return False

        with db_lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            try:
                # Получаем текущие данные счета
                cursor.execute("SELECT initial_balance, current_balance FROM accounts WHERE id = ?", (account_id,))
                result = cursor.fetchone()
                if not result:
                    print(f"Error: Account with ID {account_id} not found")
                    return False
                    
                old_initial_balance, current_balance = result
                old_initial_balance = float(old_initial_balance) if old_initial_balance is not None else 0.0
                current_balance = float(current_balance) if current_balance is not None else 0.0
                
                print(f"DEBUG: Before update - Account {account_id}: old_initial={old_initial_balance}, current={current_balance}, new_initial={new_initial_balance}")
                
                # Вычисляем разницу в начальном балансе
                initial_balance_diff = new_initial_balance - old_initial_balance
                
                # Обновляем начальный и текущий баланс
                new_current_balance = current_balance + initial_balance_diff
                
                cursor.execute(
                    "UPDATE accounts SET initial_balance = ?, current_balance = ? WHERE id = ?",
                    (new_initial_balance, new_current_balance, account_id)
                )
                
                # Проверяем что обновилось
                cursor.execute("SELECT initial_balance, current_balance FROM accounts WHERE id = ?", (account_id,))
                after_update = cursor.fetchone()
                
                conn.commit()
                print(f"DEBUG: SUCCESS - Account {account_id} updated: initial={after_update[0]}, current={after_update[1]}")
                return True
                
            except sqlite3.Error as e:
                print(f"Database error updating initial balance: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()
        
    def delete_account(self, account_id):
        """
        Удаляет счет только если на нем нет операций.
        Возвращает:
        - True если удалено
        - False если ошибка
        - dict с информацией если есть операции
        """
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Проверяем существование счета
            cursor.execute("SELECT name FROM accounts WHERE id = ?", (account_id,))
            account = cursor.fetchone()
            if not account:
                print(f"Error: Account with ID {account_id} not found")
                return False
            
            account_name = account[0]
            
            # Проверяем наличие транзакций
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE account_id = ?", (account_id,))
            transactions_count = cursor.fetchone()[0]
            
            # Проверяем наличие переводов (как отправитель)
            cursor.execute("SELECT COUNT(*) FROM transfers WHERE from_account_id = ?", (account_id,))
            transfers_from_count = cursor.fetchone()[0]
            
            # Проверяем наличие переводов (как получатель)  
            cursor.execute("SELECT COUNT(*) FROM transfers WHERE to_account_id = ?", (account_id,))
            transfers_to_count = cursor.fetchone()[0]
            
            # Проверяем наличие займов
            cursor.execute("SELECT COUNT(*) FROM loans WHERE account_id = ?", (account_id,))
            loans_count = cursor.fetchone()[0]
            
            total_operations = transactions_count + transfers_from_count + transfers_to_count + loans_count
            
            if total_operations > 0:
                # Возвращаем детальную информацию о операциях
                return {
                    "can_delete": False,
                    "account_name": account_name,
                    "transactions_count": transactions_count,
                    "transfers_from_count": transfers_from_count,
                    "transfers_to_count": transfers_to_count,
                    "loans_count": loans_count,
                    "total_operations": total_operations
                }
            
            # Если операций нет - удаляем счет
            cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            conn.commit()
            print(f"DEBUG: Account '{account_name}' (ID: {account_id}) deleted successfully")
            return True
            
        except sqlite3.Error as e:
            print(f"Database error in delete_account: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    # --- Функции для работы с категориями ---
    def add_category(self, name, type, budget_amount_monthly=0.0, parent_id=None):
        """
        Добавляет новую категорию с поддержкой родительской категории.
        """
        # ЕСЛИ budget_amount_monthly - СТРОКА, ОБРАБАТЫВАЕМ ЗАПЯТЫЕ
        if isinstance(budget_amount_monthly, str):
            budget_amount_monthly = budget_amount_monthly.replace(',', '.')
        
        try:
            budget_amount_monthly = float(budget_amount_monthly)
        except (ValueError, TypeError):
            budget_amount_monthly = 0.0
            print(f"Warning: budget_amount_monthly for category {name} was not a number, set to 0.0")
        
        # Проверяем существование родительской категории
        if parent_id:
            parent_category = self.get_category_by_id(parent_id)
            if not parent_category:
                print(f"Error: Parent category with ID {parent_id} not found")
                return False
            
            # Проверяем, что типы совпадают
            if parent_category[2] != type:  # parent_category[2] - это тип категории
                print(f"Error: Subcategory type '{type}' must match parent category type '{parent_category[2]}'")
                return False
        
        return self._execute_query(
            "INSERT INTO categories (name, type, budget_amount_monthly, parent_id) VALUES (?, ?, ?, ?)",
            (name, type, budget_amount_monthly, parent_id)
        )
    
    def get_categories(self, type=None, include_subcategories=True):
        """
        Получает категории с опциональной фильтрацией.
        
        Args:
            type: 'income', 'expense' или None
            include_subcategories: включать ли подкатегории
        """
        try:
            if include_subcategories:
                # Используем метод с иерархией, который уже включает подкатегории
                hierarchy_categories = self.get_categories_with_hierarchy(type_filter=type)
                # Преобразуем в формат (id, name, type, budget_amount_monthly, parent_id)
                result = []
                for c in hierarchy_categories:
                    result.append((
                        c[0],  # id
                        c[1],  # name
                        c[2],  # type
                        float(c[3]) if c[3] is not None else 0.0,  # budget_amount_monthly
                        c[4]   # parent_id
                    ))
                return result
            else:
                # Старая логика (без подкатегорий)
                query = "SELECT id, name, type, budget_amount_monthly, parent_id FROM categories"
                params = []
                
                if type:
                    query += " WHERE type = ?"
                    params.append(type)
                
                query += " AND parent_id IS NULL ORDER BY name"
                
                categories = self._execute_query(query, params, fetch_all=True)
                
                if categories:
                    result = []
                    for cat in categories:
                        result.append((
                            cat[0],  # id
                            cat[1],  # name
                            cat[2],  # type
                            float(cat[3]) if cat[3] is not None else 0.0,  # budget_amount_monthly
                            cat[4]   # parent_id
                        ))
                    return result
                return []
        except sqlite3.OperationalError as e:
            if "no such column: parent_id" in str(e):
                # Старая структура - без parent_id
                query = "SELECT id, name, type, budget_amount_monthly FROM categories"
                params = []
                
                if type:
                    query += " WHERE type = ?"
                    params.append(type)
                
                query += " ORDER BY name"
                
                categories = self._execute_query(query, params, fetch_all=True)
                
                if categories:
                    result = []
                    for cat in categories:
                        result.append((
                            cat[0],  # id
                            cat[1],  # name
                            cat[2],  # type
                            float(cat[3]) if cat[3] is not None else 0.0,  # budget_amount_monthly
                            None     # parent_id
                        ))
                    return result
                return []
            else:
                raise
    
    def get_categories_with_hierarchy(self, type_filter=None):
        """
        Получает все категории с информацией об иерархии.
        
        Args:
            type_filter: 'income', 'expense' или None (все типы)
        
        Returns:
            Список кортежей: (id, name, type, budget_amount_monthly, parent_id, level, path)
            где level - уровень вложенности (0 для основных)
            path - полный путь
        """
        try:
            # Проверяем наличие parent_id
            query = '''
                WITH RECURSIVE category_tree AS (
                    -- Основные категории (у которых нет родителя)
                    SELECT 
                        id, 
                        name, 
                        type, 
                        budget_amount_monthly, 
                        parent_id,
                        0 as level,
                        name as path
                    FROM categories
                    WHERE parent_id IS NULL
                        AND (? IS NULL OR type = ?)
                    
                    UNION ALL
                    
                    -- Подкатегории (рекурсивно)
                    SELECT 
                        c.id,
                        c.name,
                        c.type,
                        c.budget_amount_monthly,
                        c.parent_id,
                        ct.level + 1 as level,
                        ct.path || ' > ' || c.name as path
                    FROM categories c
                    INNER JOIN category_tree ct ON c.parent_id = ct.id
                    WHERE (? IS NULL OR c.type = ?)
                )
                SELECT id, name, type, budget_amount_monthly, parent_id, level, path
                FROM category_tree
                WHERE (? IS NULL OR type = ?)
                ORDER BY path
            '''
            
            # Параметры для фильтра
            if type_filter:
                params = [type_filter, type_filter, type_filter, type_filter, type_filter, type_filter]
            else:
                params = [None, None, None, None, None, None]
            
            categories = self._execute_query(query, params, fetch_all=True)
            
            if categories:
                # Преобразуем budget_amount_monthly к float
                result = []
                for cat in categories:
                    result.append((
                        cat[0],  # id
                        cat[1],  # name
                        cat[2],  # type
                        float(cat[3]) if cat[3] is not None else 0.0,  # budget_amount_monthly
                        cat[4],  # parent_id
                        cat[5],  # level
                        cat[6]   # path
                    ))
                return result
            return []
            
        except sqlite3.OperationalError as e:
            if "no such column: parent_id" in str(e) or "no such column: budget_amount_monthly" in str(e):
                # Старая структура - рекурсивный запрос не работает
                query = "SELECT id, name, type, budget_amount_monthly FROM categories"
                params = []
                
                if type_filter:
                    query += " WHERE type = ?"
                    params.append(type_filter)
                
                query += " ORDER BY name"
                
                categories = self._execute_query(query, params, fetch_all=True)
                
                if categories:
                    result = []
                    for cat in categories:
                        result.append((
                            cat[0],  # id
                            cat[1],  # name
                            cat[2],  # type
                            float(cat[3]) if cat[3] is not None else 0.0,  # budget_amount_monthly
                            None,    # parent_id
                            0,       # level (все основные)
                            cat[1]   # path (только имя)
                        ))
                    return result
                return []
            else:
                raise

    def get_categories_for_display(self, type=None):
        """
        Получает категории для отображения в UI с отступами.
        Возвращает список в формате: [(id, display_name), ...]
        """
        categories = self.get_categories_with_hierarchy(type_filter=type)
        display_list = []
        
        for cat_id, name, cat_type, budget, parent_id, level, path in categories:
            # Создаем отступы для визуального представления иерархии
            indent = "    " * level
            display_name = f"{indent}{name}"
            display_list.append((cat_id, display_name))
        
        return display_list
    
    def get_category_by_id(self, category_id):
        """Получает категорию по ID."""
        category = self._execute_query(
            "SELECT id, name, type, budget_amount_monthly, parent_id FROM categories WHERE id = ?",
            (category_id,), 
            fetch_one=True
        )
        if category:
            return (category[0], category[1], category[2], float(category[3]) if category[3] is not None else 0.0, category[4])
        return None
    
    def get_category_by_name(self, name):
        """Находит категорию по имени."""
        category = self._execute_query(
            "SELECT id, name, type, budget_amount_monthly, parent_id FROM categories WHERE name = ?",
            (name,), 
            fetch_one=True
        )
        if category:
            return (category[0], category[1], category[2], float(category[3]) if category[3] is not None else 0.0, category[4])
        return None
    
    def update_category(self, category_id, name, type, budget_amount_monthly, parent_id=None):
        """Обновляет категорию с поддержкой родительской категории."""
        print(f"DEBUG DB: update_category called - id={category_id}, name='{name}', type='{type}', budget={budget_amount_monthly}, parent_id={parent_id}")
        
        try:
            budget_amount_monthly = float(budget_amount_monthly)
        except (ValueError, TypeError):
            budget_amount_monthly = 0.0
            print(f"Warning: budget_amount_monthly for category ID {category_id} was not a number, set to 0.0")
        
        # Проверяем, не пытаемся ли сделать категорию родителем самой себе
        if parent_id == category_id:
            print(f"Error: Category cannot be its own parent")
            return False
        
        # Проверяем существование родительской категории
        if parent_id:
            parent_category = self.get_category_by_id(parent_id)
            if not parent_category:
                print(f"Error: Parent category with ID {parent_id} not found")
                return False
            
            # Проверяем, что типы совпадают
            if parent_category[2] != type:
                print(f"Error: Category type '{type}' must match parent category type '{parent_category[2]}'")
                return False
            
            # Проверяем на циклические ссылки
            if self._check_category_cycle(category_id, parent_id):
                print(f"Error: Creating circular reference in category hierarchy")
                return False
        
        result = self._execute_query(
            "UPDATE categories SET name = ?, type = ?, budget_amount_monthly = ?, parent_id = ? WHERE id = ?",
            (name, type, budget_amount_monthly, parent_id, category_id)
        )
        print(f"DEBUG DB: update_category result = {result}")
        return result
    
    def delete_category(self, category_id):
        """
        Удаляет категорию.
        Если есть подкатегории, они становятся основными (parent_id = NULL).
        Транзакции с этой категорией получают category_id = NULL.
        """
        try:
            # Обновляем подкатегории - делаем их основными
            self._execute_query(
                "UPDATE categories SET parent_id = NULL WHERE parent_id = ?",
                (category_id,)
            )
            
            # Обновляем транзакции, привязанные к этой категории
            self._execute_query(
                "UPDATE transactions SET category_id = NULL WHERE category_id = ?",
                (category_id,)
            )
            
            # Удаляем саму категорию
            return self._execute_query(
                "DELETE FROM categories WHERE id = ?",
                (category_id,)
            )
        except Exception as e:
            print(f"Error deleting category: {e}")
            return False
            
    def delete_category_with_children(self, category_id):
        """
        Удаляет категорию и все её подкатегории.
        Возвращает количество удаленных категорий.
        """
        try:
            # Находим все ID категорий, которые нужно удалить (рекурсивно)
            query = '''
                WITH RECURSIVE category_tree AS (
                    SELECT id
                    FROM categories
                    WHERE id = ?
                    
                    UNION ALL
                    
                    SELECT c.id
                    FROM categories c
                    INNER JOIN category_tree ct ON c.parent_id = ct.id
                )
                SELECT id FROM category_tree
            '''
            
            category_ids = self._execute_query(query, (category_id,), fetch_all=True)
            
            if not category_ids:
                return 0
            
            # Преобразуем список кортежей в список ID
            ids_to_delete = [row[0] for row in category_ids]
            
            # Обновляем транзакции, связанные с этими категориями
            placeholders = ','.join(['?' for _ in ids_to_delete])
            self._execute_query(
                f"UPDATE transactions SET category_id = NULL WHERE category_id IN ({placeholders})",
                ids_to_delete
            )
            
            # Удаляем сами категории
            self._execute_query(
                f"DELETE FROM categories WHERE id IN ({placeholders})",
                ids_to_delete
            )
            
            print(f"DEBUG: Deleted {len(ids_to_delete)} categories")
            return len(ids_to_delete)
            
        except Exception as e:
            print(f"Error in delete_category_with_children: {e}")
            return 0
    
    def get_categories_with_hierarchy(self, type_filter=None):
        """
        Получает все категории с информацией об иерархии.
        Возвращает список категорий в формате:
        (id, name, type, budget_amount_monthly, parent_id, level, path)
        где level - уровень вложенности (0 для основных)
        """
        query = '''
            WITH RECURSIVE category_tree AS (
                -- Основные категории (у которых нет родителя)
                SELECT 
                    id, 
                    name, 
                    type, 
                    budget_amount_monthly, 
                    parent_id,
                    0 as level,
                    name as path
                FROM categories
                WHERE parent_id IS NULL
                
                UNION ALL
                
                -- Подкатегории (рекурсивно)
                SELECT 
                    c.id,
                    c.name,
                    c.type,
                    c.budget_amount_monthly,
                    c.parent_id,
                    ct.level + 1 as level,
                    ct.path || ' > ' || c.name as path
                FROM categories c
                INNER JOIN category_tree ct ON c.parent_id = ct.id
            )
            SELECT id, name, type, budget_amount_monthly, parent_id, level, path
            FROM category_tree
            WHERE 1=1
        '''
        
        params = []
        if type_filter:
            query += " AND type = ?"
            params.append(type_filter)
        
        query += " ORDER BY path"
        
        categories = self._execute_query(query, params, fetch_all=True)
        
        # Преобразуем бюджет к float
        if categories:
            return [
                (cat[0], cat[1], cat[2], float(cat[3]) if cat[3] is not None else 0.0, cat[4], cat[5], cat[6])
                for cat in categories
            ]
        return []
    
    def get_categories_display_list(self, type_filter=None):
        """
        Получает список категорий для отображения в выпадающем списке.
        Возвращает список в формате [(id, display_name), ...]
        где display_name включает отступы для подкатегорий
        """
        categories = self.get_categories_with_hierarchy(type_filter)
        display_list = []
        
        for cat_id, name, cat_type, budget, parent_id, level, path in categories:
            # Создаем отступы для визуального представления иерархии
            indent = "    " * level  # 4 пробела на каждый уровень
            display_name = f"{indent}{name}"
            display_list.append((cat_id, display_name))
        
        return display_list
    
    def _check_category_cycle(self, category_id, potential_parent_id):
        """
        Проверяет, не создает ли назначение родителя циклическую ссылку.
        Возвращает True если назначение создает цикл, False если безопасно
        """
        if potential_parent_id is None:
            return False  # Без родителя - циклов быть не может
        
        # Получаем всех предков потенциального родителя
        query = '''
            WITH RECURSIVE ancestors AS (
                SELECT id, parent_id
                FROM categories
                WHERE id = ?
                
                UNION ALL
                
                SELECT c.id, c.parent_id
                FROM categories c
                INNER JOIN ancestors a ON c.id = a.parent_id
            )
            SELECT id FROM ancestors
        '''
        
        ancestors_result = self._execute_query(query, (potential_parent_id,), fetch_all=True)
        
        if not ancestors_result:
            return False
        
        ancestors = [row[0] for row in ancestors_result]
        
        # Если category_id есть среди предков potential_parent_id - это цикл
        return category_id in ancestors
    
    def get_subcategories(self, parent_id):
        """Получает все подкатегории для заданной родительской категории."""
        return self.get_categories(parent_id=parent_id)
    
    def get_category_full_path(self, category_id):
        """Получает полный путь к категории (например, 'Продукты > Молочные > Сыр')."""
        query = '''
            WITH RECURSIVE category_path AS (
                SELECT id, name, parent_id, name as path
                FROM categories
                WHERE id = ?
                
                UNION ALL
                
                SELECT c.id, c.name, c.parent_id, cp.path || ' > ' || c.name
                FROM categories c
                INNER JOIN category_path cp ON c.id = cp.parent_id
            )
            SELECT path FROM category_path
            WHERE parent_id IS NULL
            ORDER BY id
        '''
        
        result = self._execute_query(query, (category_id,), fetch_one=True)
        if result:
            # Нужно развернуть путь в правильном порядке
            parts = result[0].split(' > ')
            return ' > '.join(reversed(parts))
        return None
    
    def get_total_budget_for_category_tree(self, category_id):
        """
        Получает общий бюджет для категории и всех её подкатегорий.
        """
        # Находим все ID категорий в дереве
        query = '''
            WITH RECURSIVE category_tree AS (
                SELECT id
                FROM categories
                WHERE id = ?
                
                UNION ALL
                
                SELECT c.id
                FROM categories c
                INNER JOIN category_tree ct ON c.parent_id = ct.id
            )
            SELECT COALESCE(SUM(budget_amount_monthly), 0) as total_budget
            FROM categories
            WHERE id IN (SELECT id FROM category_tree)
        '''
        
        result = self._execute_query(query, (category_id,), fetch_one=True)
        if result and result[0] is not None:
            return float(result[0])
        return 0.0
    
    # --- Функции для работы с транзакциями ---
    def add_transaction(self, date, amount, type, category_id, description, account_id, quantity=1.0):
        """
        Добавляет новую транзакцию с поддержкой количества.
        Логика:
        - доход: положительная сумма (+)
        - расход: 
            * положительная сумма: обычный расход (-) 
            * отрицательная сумма: возврат покупки (+)
        - корректировка: сумма как есть
        """
        # ЕСЛИ amount - СТРОКА, ОБРАБАТЫВАЕМ ЗАПЯТЫЕ
        if isinstance(amount, str):
            amount = amount.replace(',', '.')
        
        try:
            amount = float(amount)
            quantity = float(quantity)
        except (ValueError, TypeError):
            print(f"Error: Transaction amount {amount} or quantity {quantity} is not a number.")
            return False

        if not self.get_account_by_id(account_id):
            print(f"Error: Account with ID {account_id} not found for transaction")
            return False

        print(f"DEBUG: Adding transaction: Date={date}, Amount={amount}, Type={type}, "
              f"CatID={category_id}, Desc={description}, AccID={account_id}, Quantity={quantity}")
        
        # ИСПРАВЛЕННАЯ ЛОГИКА:
        if type == "корректировка":
            # Для корректировок используем сумму как есть
            db_amount = amount
            print(f"DEBUG: Корректировка: amount={db_amount}")
            
        elif type == "расход":
            if amount > 0:
                # Обычный расход: положительная сумма -> отрицательная в БД
                db_amount = -amount
                print(f"DEBUG: Обычный расход: {amount} -> {db_amount}")
            elif amount < 0:
                # Возврат покупки: отрицательная сумма -> положительная в БД (увеличивает баланс)
                db_amount = -amount  # Меняем знак: -100 → +100
                print(f"DEBUG: Возврат покупки: {amount} -> {db_amount} (баланс увеличивается)")
            else:
                # amount == 0
                db_amount = 0
                print(f"DEBUG: Нулевой расход")
                
        else:  # "доход"
            # Для доходов сумма всегда положительная
            db_amount = abs(amount)
            print(f"DEBUG: Доход: amount={db_amount}")
        
        # Используем единый метод выполнения запросов
        result = self._execute_query(
            "INSERT INTO transactions (date, amount, type, category_id, description, account_id, quantity) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date, db_amount, type, category_id, description, account_id, quantity)
        )
        
        if result:
            # Обновляем баланс счета
            print(f"DEBUG: Updating account {account_id} balance by {db_amount}")
            balance_updated = self.update_account_balance(account_id, db_amount)
            print(f"DEBUG: Balance update result: {balance_updated}")
            
            # Проверяем результат
            updated_account = self.get_account_by_id(account_id)
            if updated_account:
                print(f"DEBUG: New balance: {updated_account[4]}")
        
        return result
        
    def get_transactions(self, date_from=None, date_to=None, trans_type=None, 
                         category_id=None, account_id=None, description_text=None):
        """
        Получает все транзакции, опционально с фильтрами.
        Фильтры: date_from, date_to, trans_type ('доход' или 'расход'),
                 category_id, account_id, description_text (частичное совпадение).
        """
        query = """
            SELECT t.id, t.date, t.amount, t.type, c.name, t.description, 
                   a.name, t.account_id, COALESCE(t.quantity, 1.0) as quantity
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE 1=1
        """
        params = []

        if date_from:
            query += " AND t.date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND t.date <= ?"
            params.append(date_to)
        if trans_type:
            query += " AND t.type = ?"
            params.append(trans_type)
        if category_id:
            query += " AND t.category_id = ?"
            params.append(category_id)
        if account_id:
            query += " AND t.account_id = ?"
            params.append(account_id)
        if description_text:
            query += " AND t.description LIKE ?"
            params.append(f"%{description_text}%")

        query += " ORDER BY t.date DESC, t.id DESC"

        transactions = self._execute_query(query, params, fetch_all=True)
        
        # Преобразуем результат с учетом quantity
        if transactions:
            formatted_transactions = []
            for t in transactions:
                formatted_transactions.append((
                    t[0],  # id
                    t[1],  # date
                    float(t[2]) if t[2] is not None else 0.0,  # amount
                    t[3],  # type
                    t[4],  # category_name
                    t[5],  # description
                    t[6],  # account_name
                    t[7],  # account_id
                    float(t[8]) if t[8] is not None else 1.0  # quantity
                ))
            return formatted_transactions
        return []
        
    def delete_transaction(self, transaction_id):
        """Удаляет транзакцию и связанный займ (если есть)."""
        # Сначала удаляем связанный займ (если существует)
        self.delete_loan_by_transaction_id(transaction_id)
        
        # Получаем данные транзакции для отката баланса
        transaction_data = self._execute_query("SELECT amount, account_id FROM transactions WHERE id = ?", (transaction_id,), fetch_one=True)
        if transaction_data:
            amount_to_revert, account_id = transaction_data
            self.update_account_balance(account_id, -float(amount_to_revert))
        
        # Удаляем саму транзакцию
        return self._execute_query("DELETE FROM transactions WHERE id = ?", (transaction_id,))

    # --- Функции для работы с переводами ---
    def add_transfer(self, date, amount, from_account_id, to_account_id, description):
        print(f"DEBUG DB add_transfer: from={from_account_id}, to={to_account_id}, amount={amount}")
        
        # ЕСЛИ amount - СТРОКА, ОБРАБАТЫВАЕМ ЗАПЯТЫЕ
        if isinstance(amount, str):
            amount = amount.replace(',', '.')   
        
        if from_account_id == to_account_id:
            print("Ошибка: Нельзя переводить средства на тот же счет.")
            return False

        try:
            amount = float(amount) # Убедимся, что amount - это float
        except (ValueError, TypeError):
            print(f"Error: Transfer amount {amount} is not a number.")
            return False

        # ПРОВЕРКА СУЩЕСТВОВАНИЯ СЧЕТОВ
        from_account = self.get_account_by_id(from_account_id)
        to_account = self.get_account_by_id(to_account_id)
        
        if not from_account:
            print(f"Error: From account with ID {from_account_id} not found")
            return False
            
        if not to_account:
            print(f"Error: To account with ID {to_account_id} not found")
            return False

        print(f"DEBUG: Adding transfer: Date={date}, Amount={amount}, FromAccID={from_account_id}, ToAccID={to_account_id}")
        result_from = self.update_account_balance(from_account_id, -amount)
        result_to = self.update_account_balance(to_account_id, amount)

        if result_from and result_to:
            return self._execute_query(
                "INSERT INTO transfers (date, amount, from_account_id, to_account_id, description) VALUES (?, ?, ?, ?, ?)",
                (date, amount, from_account_id, to_account_id, description)
            )
        else:
            print("Ошибка при обновлении балансов счетов во время перевода.")
            return False

    def get_transfers(self, account_id=None):
        query = """
            SELECT tr.id, tr.date, tr.amount, fa.name AS from_account_name, ta.name AS to_account_name, tr.description
            FROM transfers tr
            JOIN accounts fa ON tr.from_account_id = fa.id
            JOIN accounts ta ON tr.to_account_id = ta.id
        """
        params = []
        if account_id:
            query += " WHERE from_account_id = ? OR to_account_id = ?"
            params = [account_id, account_id]
        query += " ORDER BY tr.date DESC"
        
        transfers = self._execute_query(query, tuple(params), fetch_all=True)
        if transfers:
            return [(t[0], t[1], float(t[2]), t[3], t[4], t[5]) for t in transfers]
        return []

    '''# --- Функции для сверки баланса ---
    def update_account(self, account_id, name, acc_type): # <-- ИЗМЕНЕНА СИГНАТУРА: БАЛАНСОВ НЕТ
        existing_account = self.get_account_by_id(account_id)
        if not existing_account:
            print(f"Error: Account with ID {account_id} not found for update.")
            return False
        
        # existing_account[1] это имя, existing_account[0] это id
        if existing_account[1] != name: # Если имя меняется
            existing_with_new_name = self.get_account_by_name(name)
            if existing_with_new_name and existing_with_new_name[0] != account_id:
                print(f"Error: Account with name '{name}' already exists. Cannot update to duplicate name.")
                return False

        print(f"DEBUG: Updating account ID {account_id}: Name='{name}', Type='{acc_type}' (Balance not changed via this method)") # <-- Изменен DEBUG-лог
        return self._execute_query(
            "UPDATE accounts SET name = ?, type = ? WHERE id = ?", # <-- ИЗМЕНЕН ЗАПРОС: БАЛАНСЫ НЕ МЕНЯЮТСЯ
            (name, acc_type, account_id)
        )'''
    
    # Получаем расход/доход за год
    def get_yearly_summary(self, year):
        """Получает сводку доходов и расходов по месяцам за весь год."""
        monthly_data = {}
        
        for month in range(1, 13):
            summary = self.get_monthly_summary(year, month)
            month_key = f"{year}-{month:02d}"
            monthly_data[month_key] = {
                'income': summary.get('total_income', 0) or 0,
                'expense': summary.get('total_expense', 0) or 0,
                'balance': 0  # Будет рассчитано позже
            }
        
        # Рассчитываем накопленный баланс
        cumulative_balance = 0
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            income = monthly_data[month_key]['income']
            expense = monthly_data[month_key]['expense']
            monthly_balance = income - expense
            cumulative_balance += monthly_balance
            monthly_data[month_key]['balance'] = cumulative_balance
        
        return monthly_data
    
    # --- Новые функции для отчетов и агрегации данных ---
    # --- Методы для дашборда (также убедитесь, что они присутствуют и корректны) ---
    def get_monthly_summary(self, year, month=None):
            print(f"DEBUG DB: get_monthly_summary called for year={year}, month={month}")
            query = """
                SELECT
                    SUM(CASE WHEN type = 'доход' THEN amount ELSE 0 END) AS total_income,    -- <-- ИЗМЕНЕНО
                    SUM(CASE WHEN type = 'расход' THEN amount ELSE 0 END) AS total_expense    -- <-- ИЗМЕНЕНО
                FROM transactions
                WHERE STRFTIME('%Y', date) = ?
            """
            params = [str(year)]

            if month:
                query += " AND STRFTIME('%m', date) = ?"
                params.append(f"{month:02d}")

            # print(f"DEBUG DB: get_monthly_summary query: {query}, params: {params}")
            result = self._execute_query(query, params, fetch_one=True)
            income = result[0] if result and result[0] is not None else 0
            expense = result[1] if result and result[1] is not None else 0
            print(f"DEBUG DB: get_monthly_summary returning: {income}, {expense}")
            return {"total_income": income, "total_expense": expense}

    def get_transactions_by_month(self, year):
        print(f"DEBUG DB: get_transactions_by_month called for year={year}") # <-- ДОБАВЛЕНО
        query = """
            SELECT
                STRFTIME('%Y-%m', date) as month_year_raw,
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
            FROM transactions
            WHERE STRFTIME('%Y', date) = ?
            GROUP BY month_year_raw
            ORDER BY month_year_raw
        """
        params = [str(year)]
        results = self._execute_query(query, params, fetch_all=True)
        
        formatted_results = []
        if results:
            for row in results:
                # ИСПРАВЛЕНИЕ: НЕ ФОРМАТИРУЕМ ЗДЕСЬ И ВОЗВРАЩАЕМ ПОД КЛЮЧОМ 'month_year_raw'
                # Убедитесь, что здесь НЕТ вызовов calendar.month_name
                formatted_results.append({
                    "month_year_raw": row[0], # 'YYYY-MM'
                    "income": row[1] if row[1] is not None else 0,
                    "expense": row[2] if row[2] is not None else 0
                })
        print(f"DEBUG DB: get_transactions_by_month returning {len(formatted_results)} items.")
        return formatted_results

    def get_expense_distribution_by_category(self, year, month=None):
        print(f"DEBUG DB: get_expense_distribution_by_category called for year={year}, month={month}")
        query = """
            SELECT c.name, SUM(t.amount)
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.type = 'расход' AND STRFTIME('%Y', t.date) = ? -- <-- ИЗМЕНЕНО
        """
        params = [str(year)]

        if month:
            query += " AND STRFTIME('%m', t.date) = ?"
            params.append(f"{month:02d}")
        
        query += " GROUP BY c.name ORDER BY SUM(t.amount) DESC"

        results = self._execute_query(query, params, fetch_all=True)
        
        formatted_results = []
        if results:
            for row in results:
                formatted_results.append({
                    "category": row[0],
                    "amount": abs(row[1]) if row[1] is not None else 0 # Суммы расходов должны быть положительными для круговой диаграммы
                })
        print(f"DEBUG DB: get_expense_distribution_by_category returning {len(formatted_results)} items.") # <-- ДОБАВЛЕНО
        return formatted_results
    
    def get_monthly_financial_dynamics(self, year):
        print(f"DEBUG DB: get_monthly_financial_dynamics called for year={year}")
        query = """
            SELECT
                STRFTIME('%Y-%m', date) as month_year_raw,
                SUM(CASE WHEN type = 'доход' THEN amount ELSE 0 END) as total_income,       -- <-- ИЗМЕНЕНО
                SUM(CASE WHEN type = 'расход' THEN amount ELSE 0 END) as total_expense_abs   -- <-- ИЗМЕНЕНО
            FROM transactions
            WHERE STRFTIME('%Y', date) = ?
            GROUP BY month_year_raw
            ORDER BY month_year_raw
        """
        params = [str(year)]
        results = self._execute_query(query, params, fetch_all=True)
        
        dynamic_data = []
        if results:
            for row in results:
                # ИСПРАВЛЕНИЕ: НЕ ФОРМАТИРУЕМ ЗДЕСЬ И ВОЗВРАЩАЕМ ПОД КЛЮЧОМ 'month_year_raw'
                # Убедитесь, что здесь НЕТ вызова calendar.month_name
                dynamic_data.append({
                    "month_year_raw": row[0], # 'YYYY-MM' - берем из запроса
                    "income": row[1] if row[1] is not None else 0,
                    "expense": abs(row[2]) if row[2] is not None else 0,
                    "net_income": (row[1] if row[1] is not None else 0) - (abs(row[2]) if row[2] is not None else 0)
                })
        print(f"DEBUG DB: get_monthly_financial_dynamics returning {len(dynamic_data)} items.")
        return dynamic_data
                   
    def add_loan(self, account_id, contact_name, loan_type, amount, issue_date, due_date=None, description=None):
        """Добавляет новый займ в базу данных С обновлением баланса ДВУХ счетов."""
        try:
            # Убедимся, что amount - это float
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                print(f"Error: Loan amount {amount} is not a number.")
                return False

            # ПРОВЕРКА СУЩЕСТВОВАНИЯ СЧЕТА
            account = self.get_account_by_id(account_id)
            if not account:
                print(f"Error: Account with ID {account_id} not found for loan")
                return False
            
            # СОЗДАЕМ/ПОЛУЧАЕМ СЧЕТ КОНТРАГЕНТА
            counterparty_account_name = f"Контрагент: {contact_name}"
            counterparty_account = self.get_account_by_name(counterparty_account_name)

            if not counterparty_account:
                # Создаем виртуальный счет для контрагента
                if self.add_account(counterparty_account_name, "Counterparty", 0.0):
                    counterparty_account = self.get_account_by_name(counterparty_account_name)
                    print(f"DEBUG: Created counterparty account: {counterparty_account_name}")
                else:
                    print(f"Error: Failed to create counterparty account: {counterparty_account_name}")
                    return False
            
            counterparty_account_id = counterparty_account[0]
            
            # Создаем соединение для выполнения нескольких операций
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Вставляем новый займ
            cursor.execute('''
                INSERT INTO loans (account_id, contact_name, loan_type, loan_amount, outstanding_amount, 
                                 issue_date, due_date, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (account_id, contact_name, loan_type, amount, amount, issue_date, due_date, description))
            
            loan_id = cursor.lastrowid
            
            # ОБНОВЛЯЕМ БАЛАНСЫ ДВУХ СЧЕТОВ В ЗАВИСИМОСТИ ОТ ТИПА ЗАЙМА
            if loan_type == "получен":
                # Если займ получен - деньги поступают на ваш счет от контрагента
                cursor.execute('UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?', 
                              (amount, account_id))  # Ваш счет: +amount
                cursor.execute('UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?', 
                              (amount, counterparty_account_id))  # Контрагент: -amount
                print(f"DEBUG DB: Received loan - account {account_id} +{amount}, counterparty {counterparty_account_id} -{amount}")
            else:  # "выдан"
                # Если займ выдан - деньги уходят с вашего счета контрагенту
                cursor.execute('UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?', 
                              (amount, account_id))  # Ваш счет: -amount
                cursor.execute('UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?', 
                              (amount, counterparty_account_id))  # Контрагент: +amount
                print(f"DEBUG DB: Issued loan - account {account_id} -{amount}, counterparty {counterparty_account_id} +{amount}")
            
            conn.commit()
            print(f"DEBUG DB: Added loan for {contact_name}, amount: {amount}, type: {loan_type}")
            return True
            
        except sqlite3.Error as e:
            print(f"Database error in add_loan: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()
                
    def get_transactions_by_description(self, description_text):
        """Получает транзакции по частичному совпадению описания."""
        return self._execute_query(
            "SELECT id, date, amount, type, category_id, description, account_id FROM transactions WHERE description LIKE ?",
            (f"%{description_text}%",),
            fetch_all=True
            )
            
    def delete_loan_by_transaction_id(self, transaction_id):
        """Удаляет займ по ID связанной транзакции."""
        return self._execute_query("DELETE FROM loans WHERE transaction_id = ?", (transaction_id,))
        
    def add_loan_payment(self, loan_id, from_account_id, to_account_id, payment_date, payment_amount, description=None):
        """Добавляет платеж по займу как перевод между счетами."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Получаем данные займа
            cursor.execute('''
                SELECT contact_name, loan_type, outstanding_amount 
                FROM loans WHERE id = ?
            ''', (loan_id,))
            loan_data = cursor.fetchone()
            
            if not loan_data:
                print(f"Error: Loan with ID {loan_id} not found")
                return False
                
            contact_name, loan_type, outstanding_amount = loan_data
            
            # Проверяем существование счетов
            cursor.execute("SELECT id FROM accounts WHERE id IN (?, ?)", (from_account_id, to_account_id))
            accounts = cursor.fetchall()
            if len(accounts) != 2:
                print(f"Error: One or both accounts not found")
                return False
            
            # Проверяем, что сумма платежа не превышает остаток долга
            if payment_amount > outstanding_amount:
                print(f"Error: Payment amount {payment_amount} exceeds outstanding amount {outstanding_amount}")
                return False
            
            # Создаем перевод между счетами
            if loan_type == "выдан":
                # Если займ выдан: получаем возврат денег (с чужого счета на наш)
                # from_account_id - счет заемщика, to_account_id - наш счет
                transfer_description = f"Возврат займа: {contact_name}"
            else:  # "получен"
                # Если займ получен: возвращаем деньги (с нашего счета на счет кредитора)
                # from_account_id - наш счет, to_account_id - счет кредитора
                transfer_description = f"Погашение займа: {contact_name}"
            
            if description:
                transfer_description += f" - {description}"
            
            # Создаем запись о переводе
            cursor.execute('''
                INSERT INTO transfers (date, amount, from_account_id, to_account_id, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (payment_date, payment_amount, from_account_id, to_account_id, transfer_description))
            
            # Обновляем балансы счетов
            cursor.execute('''
                UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?
            ''', (payment_amount, from_account_id))
            
            cursor.execute('''
                UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?
            ''', (payment_amount, to_account_id))
            
            # Добавляем запись о платеже по займу
            cursor.execute('''
                INSERT INTO loan_payments (loan_id, payment_date, payment_amount, description)
                VALUES (?, ?, ?, ?)
            ''', (loan_id, payment_date, payment_amount, description))
            
            # Обновляем остаток долга по займу
            new_outstanding = outstanding_amount - payment_amount
            cursor.execute('''
                UPDATE loans SET outstanding_amount = ? WHERE id = ?
            ''', (new_outstanding, loan_id))
            
            conn.commit()
            print(f"DEBUG DB: Added loan payment {payment_amount} for loan {loan_id}, new outstanding: {new_outstanding}")
            return True
            
        except sqlite3.Error as e:
            print(f"Database error in add_loan_payment: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def get_loan_payments(self, loan_id):
        """Получает все платежи по конкретному займу."""
        return self._execute_query('''
            SELECT id, payment_date, payment_amount, description, transaction_id
            FROM loan_payments 
            WHERE loan_id = ?
            ORDER BY payment_date DESC
        ''', (loan_id,), fetch_all=True)

    def get_loan_by_id(self, loan_id):
        """Получает займ по ID и гарантирует числовые типы."""
        loan_data = self._execute_query('''
            SELECT id, account_id, contact_name, loan_type, loan_amount, outstanding_amount, 
                   issue_date, due_date, description, transaction_id
            FROM loans WHERE id = ?
        ''', (loan_id,), fetch_one=True)
        
        if loan_data:
            # Преобразуем числовые поля к float
            loan_amount = float(loan_data[4]) if loan_data[4] is not None else 0.0
            outstanding_amount = float(loan_data[5]) if loan_data[5] is not None else 0.0
            
            # Возвращаем кортеж с правильными типами
            return (
                loan_data[0],  # id
                loan_data[1],  # account_id (ID счета займа)
                loan_data[2],  # contact_name
                loan_data[3],  # loan_type
                loan_amount,   # loan_amount (float)
                outstanding_amount,  # outstanding_amount (float)
                loan_data[6],  # issue_date
                loan_data[7],  # due_date
                loan_data[8],  # description
                loan_data[9]   # transaction_id
            )
        return None

    def delete_loan_payment(self, payment_id):
        """Удаляет платеж по займу и восстанавливает остаток долга."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Получаем данные платежа
            cursor.execute('''
                SELECT lp.loan_id, lp.payment_amount, lp.transaction_id, l.outstanding_amount
                FROM loan_payments lp
                JOIN loans l ON lp.loan_id = l.id
                WHERE lp.id = ?
            ''', (payment_id,))
            payment_data = cursor.fetchone()
            
            if not payment_data:
                return False
                
            loan_id, payment_amount, transaction_id, current_outstanding = payment_data
            
            # Восстанавливаем остаток долга
            new_outstanding = current_outstanding + payment_amount
            cursor.execute('''
                UPDATE loans SET outstanding_amount = ? WHERE id = ?
            ''', (new_outstanding, loan_id))
            
            # Откатываем баланс счета (удаляем транзакцию)
            if transaction_id:
                cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            
            # Удаляем запись о платеже
            cursor.execute("DELETE FROM loan_payments WHERE id = ?", (payment_id,))
            
            conn.commit()
            print(f"DEBUG DB: Deleted payment {payment_id}, restored outstanding to {new_outstanding}")
            return True
            
        except sqlite3.Error as e:
            print(f"Database error in delete_loan_payment: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()
                
    def update_loan(self, loan_id, contact_name=None, due_date=None, description=None):
        """Обновляет данные займа."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Получаем текущие данные займа
            current_data = self.get_loan_by_id(loan_id)
            if not current_data:
                print(f"Error: Loan with ID {loan_id} not found")
                return False
            
            # Подготавливаем данные для обновления
            update_fields = []
            update_values = []
            
            if contact_name is not None:
                update_fields.append("contact_name = ?")
                update_values.append(contact_name)
            
            if due_date is not None:
                update_fields.append("due_date = ?")
                update_values.append(due_date)
            
            if description is not None:
                update_fields.append("description = ?")
                update_values.append(description)
            
            if not update_fields:
                print("No fields to update")
                return True  # Ничего не обновляем - это нормально
            
            update_values.append(loan_id)
            
            # Выполняем обновление
            query = f"UPDATE loans SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, update_values)
            
            conn.commit()
            print(f"DEBUG DB: Updated loan {loan_id}")
            return True
            
        except sqlite3.Error as e:
            print(f"Database error in update_loan: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()
                
    def get_transfers(self, account_id=None):
        """Получает все переводы."""
        query = """
            SELECT tr.id, tr.date, tr.amount, fa.name AS from_account_name, 
                   ta.name AS to_account_name, tr.description
            FROM transfers tr
            JOIN accounts fa ON tr.from_account_id = fa.id
            JOIN accounts ta ON tr.to_account_id = ta.id
        """
        params = []
        if account_id:
            query += " WHERE from_account_id = ? OR to_account_id = ?"
            params = [account_id, account_id]
        query += " ORDER BY tr.date DESC"
        
        transfers = self._execute_query(query, tuple(params), fetch_all=True)
        if transfers:
            return [(t[0], t[1], float(t[2]), t[3], t[4], t[5]) for t in transfers]
        return []
        
    def delete_loan_payment(self, payment_id):
        """Удаляет платеж по займу и восстанавливает балансы счетов."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Получаем данные платежа
            cursor.execute('''
                SELECT lp.id, lp.loan_id, lp.payment_amount, lp.payment_date, lp.description,
                       l.contact_name, l.loan_type
                FROM loan_payments lp
                JOIN loans l ON lp.loan_id = l.id
                WHERE lp.id = ?
            ''', (payment_id,))
            
            payment_data = cursor.fetchone()
            
            if not payment_data:
                print(f"Error: Payment with ID {payment_id} not found")
                return False
                
            payment_id, loan_id, payment_amount, payment_date, payment_description, contact_name, loan_type = payment_data
            
            # Находим связанный перевод по дате, сумме и описанию
            cursor.execute('''
                SELECT id, from_account_id, to_account_id 
                FROM transfers 
                WHERE date = ? AND amount = ? 
                AND description LIKE ?
            ''', (payment_date, payment_amount, f'%{contact_name}%'))
            
            transfer_data = cursor.fetchone()
            
            # Восстанавливаем балансы счетов если нашли перевод
            if transfer_data:
                transfer_id, from_account_id, to_account_id = transfer_data
                
                # Восстанавливаем балансы (обратная операция)
                cursor.execute('UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?', 
                              (payment_amount, from_account_id))
                cursor.execute('UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?', 
                              (payment_amount, to_account_id))
                
                # Удаляем перевод
                cursor.execute('DELETE FROM transfers WHERE id = ?', (transfer_id,))
            
            # Восстанавливаем остаток долга по займу
            cursor.execute('UPDATE loans SET outstanding_amount = outstanding_amount + ? WHERE id = ?', 
                          (payment_amount, loan_id))
            
            # Удаляем запись о платеже
            cursor.execute('DELETE FROM loan_payments WHERE id = ?', (payment_id,))
            
            conn.commit()
            print(f"DEBUG DB: Deleted payment {payment_id}, restored {payment_amount} to loan {loan_id}")
            return True
            
        except sqlite3.Error as e:
            print(f"Database error in delete_loan_payment: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()
                
    def get_loan_payments(self, loan_id):
        """Получает все платежи по конкретному займу."""
        return self._execute_query('''
            SELECT id, payment_date, payment_amount, description
            FROM loan_payments 
            WHERE loan_id = ?
            ORDER BY payment_date DESC
        ''', (loan_id,), fetch_all=True)
        
    def get_loans_with_filters(self, loan_type=None, contact_name=None, status=None, date_from=None, date_to=None):
        """Получает займы с фильтрами."""
        query = """
            SELECT id, account_id, contact_name, loan_type, loan_amount, outstanding_amount, 
                   issue_date, due_date, description 
            FROM loans 
            WHERE 1=1
        """
        params = []

        if loan_type:
            query += " AND loan_type = ?"
            params.append(loan_type)
        
        if contact_name:
            query += " AND contact_name LIKE ?"
            params.append(f"%{contact_name}%")
        
        if status == "активные":
            query += " AND outstanding_amount > 0"
        elif status == "закрытые":
            query += " AND outstanding_amount = 0"
        
        if date_from:
            query += " AND issue_date >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND issue_date <= ?"
            params.append(date_to)

        query += " ORDER BY issue_date DESC"
        
        return self._execute_query(query, params, fetch_all=True)
        
    def export_transactions_to_csv(self, filename, date_from=None, date_to=None):
        """Экспортирует транзакции в CSV файл."""
        try:
            import csv
            transactions = self.get_transactions(date_from=date_from, date_to=date_to)
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Заголовки
                writer.writerow(['ID', 'Дата', 'Сумма', 'Тип', 'Категория', 'Счет', 'Описание'])
                
                for transaction in transactions:
                    t_id, date, amount, t_type, category_name, description, account_name, account_id = transaction
                    writer.writerow([t_id, date, amount, t_type, category_name or '', account_name, description or ''])
            
            return True
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False

    def import_transactions_from_csv(self, filename, progress_callback=None):
        """Импортирует транзакции из CSV файла с автоматическим созданием счетов."""
        with db_lock:
            try:
                import csv
                conn = sqlite3.connect(self.db_name)
                cursor = conn.cursor()
                
                # Сначала собираем все уникальные счета из CSV
                account_names = set()
                category_names = set()
                total_rows = 0
                
                # Первый проход - подсчет строк и сбор данных
                with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    rows = list(reader)
                    total_rows = len(rows)
                    
                    for row in rows:
                        account_name = row.get('Счет', '').strip()
                        category_name = row.get('Категория', '').strip()
                        
                        if account_name and account_name not in ['ID', 'Дата']:
                            account_names.add(account_name)
                        if category_name:
                            category_names.add(category_name)
                
                if progress_callback:
                    progress_callback("Подготовка данных...", 5)
                
                # ОПТИМИЗАЦИЯ: Получаем ВСЕ существующие счета одним запросом
                existing_accounts = {}
                cursor.execute("SELECT id, name FROM accounts")
                for account_id, name in cursor.fetchall():
                    existing_accounts[name] = account_id
                
                # ОПТИМИЗАЦИЯ: Получаем ВСЕ существующие категории одним запросом
                existing_categories = {}
                cursor.execute("SELECT id, name FROM categories")
                for category_id, name in cursor.fetchall():
                    existing_categories[name] = category_id
                
                if progress_callback:
                    progress_callback("Создание счетов...", 10)
                
                # Создаем только НЕСУЩЕСТВУЮЩИЕ счета
                created_accounts = {}
                accounts_to_create = [name for name in account_names if name not in existing_accounts]
                
                for i, account_name in enumerate(accounts_to_create):
                    if progress_callback:
                        progress = 10 + (i * 30) // len(accounts_to_create) if accounts_to_create else 10
                        progress_callback(f"Создание счетов: {i+1}/{len(accounts_to_create)}", progress)
                    
                    account_type = self._detect_account_type(account_name)
                    cursor.execute(
                        "INSERT INTO accounts (name, type, initial_balance, current_balance) VALUES (?, ?, ?, ?)",
                        (account_name, account_type, 0.0, 0.0)
                    )
                    account_id = cursor.lastrowid
                    created_accounts[account_name] = account_id
                    print(f"DEBUG: Created account '{account_name}' (type: {account_type})")
                
                # Объединяем существующие и созданные счета
                all_accounts = {**existing_accounts, **created_accounts}
                
                if progress_callback:
                    progress_callback("Создание категорий...", 40)
                
                # Создаем только НЕСУЩЕСТВУЮЩИЕ категории
                created_categories = {}
                categories_to_create = [name for name in category_names if name not in existing_categories]
                
                for i, category_name in enumerate(categories_to_create):
                    if progress_callback:
                        progress = 40 + (i * 20) // len(categories_to_create) if categories_to_create else 40
                        progress_callback(f"Создание категорий: {i+1}/{len(categories_to_create)}", progress)
                    
                    # Временно создаем как расход, тип уточним позже
                    cursor.execute(
                        "INSERT INTO categories (name, type, budget_amount_monthly) VALUES (?, ?, ?)",
                        (category_name, 'expense', 0.0)
                    )
                    category_id = cursor.lastrowid
                    created_categories[category_name] = category_id
                
                # Объединяем существующие и созданные категории
                all_categories = {**existing_categories, **created_categories}
                
                # Теперь импортируем транзакции
                imported_count = 0
                
                if progress_callback:
                    progress_callback("Импорт транзакций...", 60)
                
                for i, row in enumerate(rows):
                    try:
                        if progress_callback:
                            progress = 60 + (i * 40) // total_rows
                            progress_callback(f"Импорт: {i+1}/{total_rows}", progress)
                        
                        # Пропускаем заголовок если есть
                        if row.get('ID') == 'ID' or row.get('Дата') == 'Дата':
                            continue
                        
                        # --- ОБРАБОТКА СЧЕТА ---
                        account_name = row.get('Счет', '').strip()
                        if not account_name:
                            print(f"Warning: Row {i+1} - missing account name, skipping")
                            continue
                        
                        account_id = all_accounts.get(account_name)
                        if not account_id:
                            print(f"Warning: Row {i+1} - account '{account_name}' not found, skipping")
                            continue
                        
                        # --- ОБРАБОТКА КАТЕГОРИИ ---
                        category_name = row.get('Категория', '').strip()
                        category_id = all_categories.get(category_name) if category_name else None
                        
                        # --- ПОДГОТОВКА ДАННЫХ ---
                        try:
                            date_str = row.get('Дата', '').strip()
                            if not date_str:
                                date_str = datetime.now().strftime('%Y-%m-%d')
                            
                            amount = float(row['Сумма'])
                            trans_type = row.get('Тип', '').strip().lower()
                            if not trans_type:
                                trans_type = 'доход' if amount > 0 else 'расход'
                            
                            description = row.get('Описание', '').strip()
                            
                        except (ValueError, KeyError) as e:
                            print(f"Warning: Row {i+1} - invalid data: {e}, skipping")
                            continue
                        
                        # --- ВСТАВКА ТРАНЗАКЦИИ ---
                        cursor.execute('''
                            INSERT INTO transactions (date, amount, type, category_id, description, account_id)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            date_str,
                            amount,
                            trans_type,
                            category_id,
                            description,
                            account_id
                        ))
                        
                        # Обновляем баланс счета
                        cursor.execute(
                            "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?",
                            (amount, account_id)
                        )
                        
                        imported_count += 1
                        
                    except Exception as e:
                        print(f"Error importing row {i+1}: {e}")
                        continue
                
                conn.commit()
                print(f"DEBUG: Import completed - {imported_count} transactions, {len(created_accounts)} accounts created, {len(created_categories)} categories created")
                return imported_count
                
            except Exception as e:
                print(f"Error importing from CSV: {e}")
                if 'conn' in locals():
                    conn.rollback()
                return 0
            finally:
                if 'conn' in locals():
                    conn.close()

    def _detect_account_type(self, account_name):
        """Автоматически определяет тип счета по его названию."""
        account_name_lower = account_name.lower()
        
        bank_keywords = ['банк', 'bank', 'сбер', 'тиньк', 'теньк', 'альфа', 'втб', 'отп']
        cash_keywords = ['налич', 'cash', 'кошелек', 'бумажн']
        credit_keywords = ['кредит', 'credit', 'карта', 'card', 'рассроч']
        
        if any(keyword in account_name_lower for keyword in credit_keywords):
            return "Credit Card"
        elif any(keyword in account_name_lower for keyword in cash_keywords):
            return "Cash"
        elif any(keyword in account_name_lower for keyword in bank_keywords):
            return "Bank Account"
        else:
            return "Bank Account"  # По умолчанию
                
    def update_account_initial_balance(self, account_id, new_initial_balance):
        """Обновляет начальный баланс счета и пересчитывает текущий баланс."""
        # ЕСЛИ new_initial_balance - СТРОКА, ОБРАБАТЫВАЕМ ЗАПЯТЫЕ
        if isinstance(new_initial_balance, str):
            new_initial_balance = new_initial_balance.replace(',', '.')
        
        try:
            new_initial_balance = float(new_initial_balance)
        except (ValueError, TypeError):
            print(f"Error: new_initial_balance {new_initial_balance} is not a number")
            return False

        with db_lock:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            try:
                # Получаем текущие данные счета
                cursor.execute("SELECT initial_balance, current_balance FROM accounts WHERE id = ?", (account_id,))
                result = cursor.fetchone()
                if not result:
                    return False
                    
                old_initial_balance, current_balance = result
                old_initial_balance = float(old_initial_balance)
                current_balance = float(current_balance)
                
                # Вычисляем разницу в начальном балансе
                initial_balance_diff = new_initial_balance - old_initial_balance
                
                # Обновляем начальный и текущий баланс
                new_current_balance = current_balance + initial_balance_diff
                
                cursor.execute(
                    "UPDATE accounts SET initial_balance = ?, current_balance = ? WHERE id = ?",
                    (new_initial_balance, new_current_balance, account_id)
                )
                
                conn.commit()
                print(f"DEBUG: Updated account {account_id} initial balance from {old_initial_balance} to {new_initial_balance}")
                return True
                
            except sqlite3.Error as e:
                print(f"Database error updating initial balance: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()
                
    def reconcile_account(self, account_id, actual_balance, difference):
        """Выполняет сверку баланса счета"""
        try:
            # Создаем транзакцию сверки
            reconcile_category = self.get_category_by_name("Сверка Баланса")
            if not reconcile_category:
                print("ERROR: Reconciliation category not found")
                return False
                
            category_id = reconcile_category[0]
            
            # Добавляем корректирующую транзакцию
            today = datetime.now().strftime('%Y-%m-%d')
            description = f"Сверка баланса. Разница: {difference:.2f} ₽"
            
            # Определяем тип транзакции
            trans_type = "доход" if difference > 0 else "расход"
            amount = abs(difference)
            
            result = self.add_transaction(
                today, amount if difference > 0 else -amount, 
                trans_type, category_id, description, account_id
            )
            
            if result:
                print(f"DEBUG: Successfully reconciled account {account_id}, difference: {difference:.2f}")
            else:
                print(f"DEBUG: Failed to add reconciliation transaction for account {account_id}")
                
            return result
            
        except Exception as e:
            print(f"Error in reconcile_account: {e}")
            return False

    def add_external_transfer(self, date_str, amount, account_id, direction, description):
        """Добавляет внешний перевод как транзакцию"""
        try:
            # Определяем тип транзакции и знак суммы
            if direction == "incoming":
                trans_type = "доход"
                amount_for_db = amount
            else:  # outgoing
                trans_type = "расход" 
                amount_for_db = -amount
                
            # Создаем транзакцию
            return self.add_transaction(
                date_str, amount_for_db, trans_type,
                None, description, account_id
            )
            
        except Exception as e:
            print(f"Error in add_external_transfer: {e}")
            return False
            
    def add_external_transfer(self, date_str, amount, account_id, direction, description):
        """Временная заглушка для обратной совместимости"""
        print("DEBUG: Using add_external_transfer stub")
        if direction == "incoming":
            return self.add_transaction(date_str, amount, "доход", None, description, account_id)
        else:
            return self.add_transaction(date_str, -amount, "расход", None, description, account_id)
            
    def delete_transfer(self, transfer_id):
        """Удаляет перевод и восстанавливает балансы счетов"""
        try:
            with db_lock:
                conn = sqlite3.connect(self.db_name)
                cursor = conn.cursor()
                
                # Получаем данные перевода
                cursor.execute('''
                    SELECT amount, from_account_id, to_account_id 
                    FROM transfers WHERE id = ?
                ''', (transfer_id,))
                
                transfer_data = cursor.fetchone()
                if not transfer_data:
                    print(f"Error: Transfer with ID {transfer_id} not found")
                    return False
                    
                amount, from_account_id, to_account_id = transfer_data
                amount = float(amount)
                
                print(f"DEBUG DB: Deleting transfer {transfer_id}: amount={amount}, from={from_account_id}, to={to_account_id}")
                
                # Восстанавливаем балансы счетов (обратная операция)
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?", 
                    (amount, from_account_id)
                )
                cursor.execute(
                    "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?", 
                    (amount, to_account_id)
                )
                
                # Удаляем перевод
                cursor.execute('DELETE FROM transfers WHERE id = ?', (transfer_id,))
                
                # Проверяем, что перевод удален
                cursor.execute('SELECT COUNT(*) FROM transfers WHERE id = ?', (transfer_id,))
                if cursor.fetchone()[0] > 0:
                    print(f"Error: Transfer {transfer_id} was not deleted")
                    conn.rollback()
                    return False
                
                conn.commit()
                print(f"DEBUG DB: Successfully deleted transfer {transfer_id}")
                return True
                
        except sqlite3.Error as e:
            print(f"Database error in delete_transfer: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()
                
    # В класс DatabaseManager добавить:
    def recalculate_all_initial_balances(self):
        """Пересчитывает начальные балансы для всех счетов"""
        accounts = self.get_accounts()
        updated_count = 0
        
        for account in accounts:
            account_id, name, acc_type, initial_balance, current_balance = account
            
            # Устанавливаем начальный баланс = текущему
            if self.update_account_initial_balance(account_id, current_balance):
                updated_count += 1
        
        return updated_count
        
    # В класс DatabaseManager добавить:
    def recalculate_all_current_balances(self, progress_callback=None):
        """Пересчитывает текущие балансы для всех счетов на основе транзакций"""
        try:
            with db_lock:
                conn = sqlite3.connect(self.db_name)
                cursor = conn.cursor()
                
                # Получаем все счета
                cursor.execute("SELECT id, name FROM accounts")
                accounts = cursor.fetchall()
                total_accounts = len(accounts)
                
                if progress_callback:
                    progress_callback("Получение списка счетов...", 10)
                
                updated_count = 0
                
                for i, (account_id, account_name) in enumerate(accounts):
                    if progress_callback:
                        progress = 10 + (i * 80) // total_accounts
                        progress_callback(f"Обработка счета: {account_name}...", progress)
                    
                    # 1. Суммируем все транзакции по счету
                    cursor.execute('''
                        SELECT SUM(amount) FROM transactions 
                        WHERE account_id = ?
                    ''', (account_id,))
                    transaction_sum = cursor.fetchone()[0] or 0.0
                    
                    # 2. Суммируем переводы (исходящие - отрицательно, входящие - положительно)
                    cursor.execute('''
                        SELECT 
                        COALESCE(SUM(CASE WHEN from_account_id = ? THEN -amount ELSE 0 END), 0) +
                        COALESCE(SUM(CASE WHEN to_account_id = ? THEN amount ELSE 0 END), 0)
                        FROM transfers
                        WHERE from_account_id = ? OR to_account_id = ?
                    ''', (account_id, account_id, account_id, account_id))
                    transfer_sum = cursor.fetchone()[0] or 0.0
                    
                    # 3. Получаем текущий начальный баланс
                    cursor.execute("SELECT initial_balance FROM accounts WHERE id = ?", (account_id,))
                    initial_balance = cursor.fetchone()[0] or 0.0
                    
                    # 4. Вычисляем новый текущий баланс
                    new_current_balance = float(initial_balance) + float(transaction_sum) + float(transfer_sum)
                    
                    print(f"DEBUG: Account {account_name} - initial: {initial_balance}, "
                          f"transactions: {transaction_sum}, transfers: {transfer_sum}, "
                          f"new_current: {new_current_balance}")
                    
                    # 5. Обновляем текущий баланс
                    cursor.execute(
                        "UPDATE accounts SET current_balance = ? WHERE id = ?",
                        (new_current_balance, account_id)
                    )
                    
                    updated_count += 1
                
                if progress_callback:
                    progress_callback("Сохранение изменений...", 90)
                
                conn.commit()
                
                if progress_callback:
                    progress_callback("Завершение...", 100)
                
                return updated_count
                
        except sqlite3.Error as e:
            print(f"Database error in recalculate_all_current_balances: {e}")
            if 'conn' in locals():
                conn.rollback()
            return 0
        finally:
            if 'conn' in locals():
                conn.close()
                
    def _show_recalculation_details(self):
        """Показывает детали перерасчета балансов"""
        # Получаем обновленные данные
        accounts = self.db.get_accounts()
        
        details_text = "Детали перерасчета:\n\n"
        
        for account in accounts:
            account_id, name, acc_type, initial_balance, current_balance = account
            details_text += f"• {name}: {current_balance:.2f} ₽\n"
        
        details_text += f"\nВсего обработано: {len(accounts)} счетов"
        
        # Показываем в отдельном окне с прокруткой
        details_window = tk.Toplevel(self)
        details_window.title("Детали перерасчета")
        details_window.geometry("400x300")
        details_window.transient(self)
        
        # Текстовая область с прокруткой
        text_frame = ttk.Frame(details_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap="word", font=("TkDefaultFont", 9))
        text_widget.insert("1.0", details_text)
        text_widget.config(state="disabled")
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Кнопка закрытия
        ttk.Button(details_window, text="Закрыть", command=details_window.destroy).pack(pady=10)
        
        self.master.center_window(details_window, self)
        
    def recalculate_single_account_balance(self, account_id):
        """Пересчитывает баланс для одного счета"""
        return self.recalculate_all_current_balances()  # Можно адаптировать для одного счета
     
    def get_category_statistics(self, include_subcategories=False, date_from=None, date_to=None):
        """Получает статистику по категориям."""
        try:
            query = '''
            SELECT c.id, c.name, c.type, c.budget_amount_monthly, c.parent_id,
                   COALESCE(SUM(CASE WHEN t.type = 'расход' THEN ABS(t.amount) ELSE 0 END), 0) as total_expense,
                   COALESCE(SUM(CASE WHEN t.type = 'доход' THEN t.amount ELSE 0 END), 0) as total_income,
                   COUNT(t.id) as transaction_count,
                   COALESCE(AVG(ABS(t.amount)), 0) as avg_amount
            FROM categories c
            LEFT JOIN transactions t ON c.id = t.category_id
            '''
            
            # Добавляем фильтр по дате если нужно
            where_conditions = []
            params = []
            
            if date_from:
                where_conditions.append("t.date >= ?")
                params.append(date_from)
            
            if date_to:
                where_conditions.append("t.date <= ?")
                params.append(date_to)
            
            # Добавляем условие для подкатегорий
            if not include_subcategories:
                where_conditions.append("c.parent_id IS NULL")
            
            # Если есть условия, добавляем WHERE
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)
            
            query += '''
            GROUP BY c.id, c.name, c.type, c.budget_amount_monthly, c.parent_id
            '''
            
            # Сортировка
            if include_subcategories:
                query += " ORDER BY c.parent_id IS NULL DESC, c.parent_id, c.name"
            else:
                query += " ORDER BY c.name"
            
            results = self._execute_query(query, tuple(params), fetch_all=True)
            
            if results:
                formatted_results = []
                for row in results:
                    formatted_results.append((
                        row[0],  # id
                        row[1],  # name
                        row[2],  # type
                        float(row[3]) if row[3] is not None else 0.0,  # budget_amount_monthly
                        row[4],  # parent_id
                        float(row[5]) if row[5] is not None else 0.0,  # total_expense
                        float(row[6]) if row[6] is not None else 0.0,  # total_income
                        row[7],  # transaction_count
                        float(row[8]) if row[8] is not None else 0.0   # avg_amount
                    ))
                return formatted_results
            return []
            
        except sqlite3.OperationalError as e:
            print(f"ERROR in get_category_statistics: {e}")
            return []       
    
    
    def update_transaction(self, transaction_id, date, amount, trans_type, category_id, 
                          description, account_id, quantity=1.0):
        """Обновляет транзакцию и корректирует балансы счетов."""
        try:
            # Получаем старую транзакцию для отката баланса
            old_transaction = self._execute_query(
                "SELECT amount, account_id, quantity FROM transactions WHERE id = ?",
                (transaction_id,), 
                fetch_one=True
            )
            
            if not old_transaction:
                print(f"Error: Transaction with ID {transaction_id} not found")
                return False
            
            old_amount, old_account_id, old_quantity = old_transaction
            old_amount = float(old_amount) if old_amount else 0.0
            old_quantity = float(old_quantity) if old_quantity else 1.0
            
            # Подготавливаем новые значения
            if isinstance(amount, str):
                amount = amount.replace(',', '.')
            
            try:
                amount = float(amount)
                quantity = float(quantity)
            except (ValueError, TypeError):
                print(f"Error: Transaction amount {amount} or quantity {quantity} is not a number.")
                return False
            
            # Определяем сумму для БД в зависимости от типа
            if trans_type == "корректировка":
                db_amount = amount
            elif trans_type == "расход":
                if amount >= 0:
                    db_amount = -amount  # Обычный расход
                else:
                    db_amount = -amount  # Возврат покупки
            else:  # "доход"
                db_amount = abs(amount)
            
            # Обновляем транзакцию
            success = self._execute_query('''
                UPDATE transactions 
                SET date = ?, 
                    amount = ?, 
                    type = ?, 
                    category_id = ?, 
                    description = ?, 
                    account_id = ?,
                    quantity = ?
                WHERE id = ?
            ''', (date, db_amount, trans_type, category_id, description, account_id, quantity, transaction_id))
            
            if not success:
                return False
            
            # Корректируем балансы счетов
            # 1. Отменяем старую транзакцию
            if old_account_id:
                self.update_account_balance(old_account_id, -old_amount)
            
            # 2. Применяем новую транзакцию
            if account_id:
                self.update_account_balance(account_id, db_amount)
            
            print(f"DEBUG: Updated transaction {transaction_id}: old_amount={old_amount}, new_amount={db_amount}")
            print(f"DEBUG: Account changed from {old_account_id} to {account_id}")
            
            return True
            
        except Exception as e:
            print(f"DEBUG: Error updating transaction: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def close(self):
        """Закрывает соединение с БД."""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
                print("Database connection closed")
        except Exception as e:
            print(f"Error closing database: {e}")
    
    def __del__(self):
        """Деструктор - автоматически закрывает соединение при удалении объекта."""
        self.close()