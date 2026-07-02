import threading
import queue
import time
from typing import Callable, Any
import tkinter as tk

class AsyncTaskManager:
    """Менеджер для выполнения задач в фоновых потоках"""
    def __init__(self):
        self.task_queue = queue.Queue()
        self.results = {}
        self.current_tasks = {}
        
    def run_async(self, task_id, function, *args, **kwargs):
        """Запускает функцию в фоновом потоке"""
        if task_id in self.current_tasks:
            return False  # Задача уже выполняется
            
        def task_wrapper():
            try:
                result = function(*args, **kwargs)
                self.task_queue.put((task_id, result, None))
            except Exception as e:
                self.task_queue.put((task_id, None, e))
            finally:
                if task_id in self.current_tasks:
                    del self.current_tasks[task_id]
        
        thread = threading.Thread(target=task_wrapper, daemon=True)
        self.current_tasks[task_id] = thread
        thread.start()
        return True
        
    def get_results(self):
        """Получает результаты выполненных задач"""
        results = {}
        while not self.task_queue.empty():
            try:
                task_id, result, error = self.task_queue.get_nowait()
                results[task_id] = (result, error)
            except queue.Empty:
                break
        return results
        
    def is_task_running(self, task_id):
        """Проверяет, выполняется ли задача"""
        return task_id in self.current_tasks

# Глобальный менеджер задач
async_manager = AsyncTaskManager()