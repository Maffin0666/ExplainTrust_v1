# gui/__init__.py

import tkinter as tk
from tkinter import ttk

from .single_tab import SingleTab
from .dialog_tab import DialogTab
from .analysis_tab import AnalysisTab
from .tonality_tab import TonalityTab


class ExplainTrustApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ExplainTrust – оценка когнитивного доверия")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', font=('Segoe UI', 9))
        style.configure('TButton', font=('Segoe UI', 9, 'bold'))
        style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладки
        self.single_tab = SingleTab(self.notebook)
        self.dialog_tab = DialogTab(self.notebook)
        self.analysis_tab = AnalysisTab(self.notebook)
        self.tonality_tab = TonalityTab(self.notebook)

        self.notebook.add(self.single_tab, text="Одиночный ответ")
        self.notebook.add(self.dialog_tab, text="Диалог")
        self.notebook.add(self.analysis_tab, text="Анализ пар")
        self.notebook.add(self.tonality_tab, text="Тональность")


def main():
    root = tk.Tk()
    app = ExplainTrustApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()