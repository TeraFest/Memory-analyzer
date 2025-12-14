import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess

# Функция для открытия директории в Проводнике Windows
def open_directory(path):
    # Если выбран путь к файлу, открываем его родительскую папку
    directory = path if os.path.isdir(path) else os.path.dirname(path)
    try:
        os.startfile(directory)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть директорию:\n{e}")

# Функция преобразования байт в выбранные единицы
def convert_size(size_in_bytes, unit):
    if unit == "КБ":
        return size_in_bytes / 1024
    elif unit == "МБ":
        return size_in_bytes / (1024 ** 2)
    elif unit == "ГБ":
        return size_in_bytes / (1024 ** 3)
    else:
        return size_in_bytes

# Сканирование файлов: собираем (размер, путь к файлу)
def scan_files(start_path, result_list, progress_callback=None):
    for root, dirs, files in os.walk(start_path, topdown=True):
        for file in files:
            try:
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                result_list.append((size, file_path))
            except Exception:
                continue
        if progress_callback:
            progress_callback(root)
    # Сортировка по размеру (от большего к меньшему)
    result_list.sort(key=lambda x: x[0], reverse=True)

# Сканирование папок: для каждой директории вычисляем суммарный размер всех файлов внутри (включая поддиректории)
def scan_folders(start_path, result_list, progress_callback=None):
    folder_sizes = {}
    # Обходим дерево в порядке bottom-up, чтобы сначала обработать поддиректории
    for root, dirs, files in os.walk(start_path, topdown=False):
        total = 0
        # Суммируем размеры файлов в текущей директории
        for file in files:
            try:
                total += os.path.getsize(os.path.join(root, file))
            except Exception:
                continue
        # Добавляем размеры дочерних директорий, если они уже посчитаны
        for d in dirs:
            child_dir = os.path.join(root, d)
            total += folder_sizes.get(child_dir, 0)
        folder_sizes[root] = total
        result_list.append((total, root))
        if progress_callback:
            progress_callback(root)
    # Сортировка списка по размеру (от большего к меньшему)
    result_list.sort(key=lambda x: x[0], reverse=True)

# Основное приложение
class FileScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Анализатор больших файлов/папок")
        self.geometry("900x600")
        self.resizable(True, True)

        # Переменные для выбора режима и единиц измерения
        self.scan_mode = tk.StringVar(value="Файлы")  # "Файлы" или "Папки"
        self.unit = tk.StringVar(value="КБ")           # "КБ", "МБ", "ГБ"

        # Фрейм с настройками
        settings_frame = tk.Frame(self)
        settings_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Label(settings_frame, text="Режим сканирования:").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(settings_frame, text="Файлы", variable=self.scan_mode, value="Файлы").pack(side=tk.LEFT)
        tk.Radiobutton(settings_frame, text="Папки", variable=self.scan_mode, value="Папки").pack(side=tk.LEFT, padx=(0,10))

        tk.Label(settings_frame, text="Единицы размера:").pack(side=tk.LEFT, padx=5)
        unit_options = ["КБ", "МБ", "ГБ"]
        tk.OptionMenu(settings_frame, self.unit, *unit_options).pack(side=tk.LEFT, padx=5)

        # Кнопка запуска сканирования
        self.scan_button = tk.Button(settings_frame, text="Начать сканирование", command=self.start_scan)
        self.scan_button.pack(side=tk.LEFT, padx=10)

        # Виджет для отображения статуса сканирования
        self.status_var = tk.StringVar()
        self.status_var.set("Выберите папку для сканирования и параметры.")
        self.status_label = tk.Label(self, textvariable=self.status_var)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview для отображения результатов
        self.tree = ttk.Treeview(self, columns=("size", "path"), show="headings")
        self.tree.heading("size", text="Размер")
        self.tree.heading("path", text="Путь")
        self.tree.column("size", width=150, anchor="center")
        self.tree.column("path", width=700, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Привязка двойного клика для открытия директории
        self.tree.bind("<Double-1>", self.on_item_double_click)

        self.results = []

    def start_scan(self):
        # Спрашиваем у пользователя путь для сканирования
        path = filedialog.askdirectory(title="Выберите папку для сканирования")
        if not path:
            return
        # Очищаем предыдущие результаты
        self.results = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.status_var.set("Сканирование...")
        self.scan_button.config(state=tk.DISABLED)

        # Запуск сканирования в отдельном потоке, чтобы не блокировать интерфейс
        threading.Thread(target=self.scan_thread, args=(path,), daemon=True).start()

    def scan_thread(self, path):
        mode = self.scan_mode.get()
        if mode == "Файлы":
            scan_files(path, self.results, progress_callback=self.update_status)
        else:
            scan_folders(path, self.results, progress_callback=self.update_status)
        # После завершения сканирования обновляем интерфейс
        self.after(0, self.display_results)

    def update_status(self, current_dir):
        # Обновление статуса сканирования
        self.status_var.set(f"Сканируется: {current_dir}")

    def display_results(self):
        unit = self.unit.get()
        # Очищаем Treeview и вставляем результаты с преобразованием единиц
        for item in self.tree.get_children():
            self.tree.delete(item)
        for size, path in self.results:
            conv_size = convert_size(size, unit)
            # Форматирование числа с двумя знаками после запятой
            size_str = f"{conv_size:,.2f} {unit}"
            self.tree.insert("", tk.END, values=(size_str, path))
        self.status_var.set(f"Сканирование завершено. Найдено объектов: {len(self.results)}")
        self.scan_button.config(state=tk.NORMAL)

    def on_item_double_click(self, event):
        # Открытие выбранного объекта (файла или папки) в проводнике
        item = self.tree.selection()
        if item:
            path = self.tree.item(item, "values")[1]
            open_directory(path)

if __name__ == "__main__":
    app = FileScannerApp()
    app.mainloop()
