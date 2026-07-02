import tkinter as tk

# Никаких дополнительных импортов не нужно

def get_simple_taskbar_height():
    """
    Упрощенный метод определения высоты панели задач.
    """
    screen_height = 1080
    
    try:
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
    except:
        pass
    
    try:
        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)
            ]
        
        rect = RECT()
        success = ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
        
        if success:
            work_height = rect.bottom - rect.top
            taskbar_height = screen_height - work_height
            
            if 0 <= taskbar_height <= 100:
                return taskbar_height
    
    except:
        pass
    
    if screen_height <= 768:
        return 30
    elif screen_height <= 1080:
        return 40
    elif screen_height <= 1440:
        return 45
    else:
        return 50

def center_window(window):
    """
    Центрирует окно с автоматическим учетом панели задач.
    """
    try:
        window.update_idletasks()
        
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        width = window.winfo_width()
        height = window.winfo_height()
        
        print(f"DEBUG центрирование начальное: окно={width}x{height}")
        
        if width <= 1 or height <= 1:
            try:
                geom = window.geometry()
                if 'x' in geom:
                    geom_parts = geom.split('+')[0]
                    width, height = map(int, geom_parts.split('x'))
                    print(f"DEBUG: Взято из geometry: {width}x{height}")
                else:
                    width = 1000
                    height = 680
                    print(f"DEBUG: Использованы размеры по умолчанию: {width}x{height}")
            except:
                width, height = 1000, 680
                print(f"DEBUG: Ошибка, размеры по умолчанию: {width}x{height}")
            
            window.geometry(f"{width}x{height}")
            window.update_idletasks()
            
            width = window.winfo_width()
            height = window.winfo_height()
            print(f"DEBUG после обновления: окно={width}x{height}")
        
        try:
            taskbar_height = get_simple_taskbar_height()
            print(f"DEBUG: Высота панели задач определена как {taskbar_height}px")
        except Exception as e:
            print(f"DEBUG: Ошибка определения панели: {e}, используем 40px")
            taskbar_height = 40
        
        work_height = screen_height - taskbar_height
        
        print(f"DEBUG: Экран={screen_width}x{screen_height}, Рабочая область={work_height}px")
        
        if height > work_height - 50:
            height = work_height - 50
            window.geometry(f"{width}x{height}")
            print(f"DEBUG: Высота ограничена до {height}px")
        
        x = (screen_width - width) // 2
        y = (work_height - height) // 2 - 20
        
        print(f"DEBUG: Окно размещено на позиции x={x}, y={y}, размер {width}x{height}")
        
        window.geometry(f"{width}x{height}+{x}+{y}")
        
        window.lift()
        window.focus_force()
        
    except Exception as e:
        print(f"ERROR: Ошибка при центрировании окна: {e}")
        window.update_idletasks()
        width = window.winfo_width() if window.winfo_width() > 1 else 1000
        height = window.winfo_height() if window.winfo_height() > 1 else 680
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

def center_window_relative(window, parent=None):
    """
    Центрирует окно относительно родителя или экрана.
    """
    window.update_idletasks()
    
    width = window.winfo_width()
    height = window.winfo_height()
    
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
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
    else:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
    
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.lift()
    window.focus_force()