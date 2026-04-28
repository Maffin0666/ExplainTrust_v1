# gui/__init__.py

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt

from .single_tab import SingleTab
from .dialog_tab import DialogTab
from .analysis_tab import AnalysisTab
from .tonality_tab import TonalityTab
from .surface_3d import Surface3DTab
from .psycho_tab import PsychoPortraitTab

class ExplainTrustApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ExplainTrust – оценка когнитивного доверия")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        self.theme = 'light'
        self._apply_theme()

        # ---------- Меню ----------
        menubar = tk.Menu(root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self._show_about)
        help_menu.add_command(label="Как интерпретировать результаты", command=self._show_help)
        menubar.add_cascade(label="Справка", menu=help_menu)
        root.config(menu=menubar)

        # ---------- Вкладки ----------
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.single_tab = SingleTab(self.notebook)
        self.dialog_tab = DialogTab(self.notebook)
        self.analysis_tab = AnalysisTab(self.notebook)
        self.tonality_tab = TonalityTab(self.notebook)
        self.surface_tab = Surface3DTab(self.notebook)
        self.psycho_tab = PsychoPortraitTab(self.notebook)

        self.notebook.add(self.single_tab, text="Одиночный ответ")
        self.notebook.add(self.dialog_tab, text="Диалог")
        self.notebook.add(self.analysis_tab, text="Анализ пар")
        self.notebook.add(self.tonality_tab, text="Тональность")
        self.notebook.add(self.surface_tab, text="3D‑анализ")
        self.notebook.add(self.psycho_tab, text="Психопортрет")

        self.theme_btn = ttk.Button(root, text="Тёмная тема", command=self._toggle_theme)
        self.theme_btn.pack(side=tk.BOTTOM, pady=5)

    def _apply_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        if self.theme == 'dark':
            bg = '#2e2e2e'
            fg = 'white'
            plt.style.use('dark_background')
            self.root.tk_setPalette(background=bg, foreground=fg)
            style.configure('.', background=bg, foreground=fg, fieldbackground=bg)
            style.map('TButton', background=[('active', '#555')])
        else:
            bg = '#f0f0f0'
            fg = 'black'
            plt.style.use('default')
            self.root.tk_setPalette(background=bg, foreground=fg)
            style.configure('.', background=bg, foreground=fg)

    def _toggle_theme(self):
        if self.theme == 'light':
            self.theme = 'dark'
            self.theme_btn.config(text="Светлая тема")
        else:
            self.theme = 'light'
            self.theme_btn.config(text="Тёмная тема")
        self._apply_theme()

    def _show_about(self):
        messagebox.showinfo("О программе",
            "ExplainTrust v1.0\n\n"
            "Нечеткая экспертная система оценки когнитивного доверия пользователя "
            "к ответам больших языковых моделей на основе лингвистического анализа.\n\n"
            "Разработана в рамках лабораторной работы по дисциплине "
            "«Интеллектуальные информационные системы».\n"
            "РГСУ, 2026"
        )

    def _show_help(self):
        messagebox.showinfo("Справка по интерпретации",
            "Индекс когнитивного доверия (CTI) принимает значения от 0 до 100.\n\n"
            "Уровни доверия:\n"
            "  0–15  — очень низкое (пользователь отвергает ответ)\n"
            " 15–35  — низкое (активное несогласие, переспросы)\n"
            " 35–55  — среднее (неуверенность, единичные сомнения)\n"
            " 55–75  — высокое (принятие с возможными уточнениями)\n"
            " 75–100 — очень высокое (полное доверие)\n\n"
            "Признаки внешнего локуса (качество ответа LLM):\n"
            "  SI — структурная целостность (0..1)\n"
            "  CM — насыщенность дискурсивными маркерами (0..0.15)\n"
            "  LD — лексическое разнообразие (0..1)\n\n"
            "Признаки внутреннего локуса (реакция пользователя):\n"
            "  DM — доля маркеров сомнения (0..1)\n"
            "  FQ — наличие переспроса (0/1)\n"
            "  RL — нормированная длина ответа (0..1)"
        )

def main():
    root = tk.Tk()
    app = ExplainTrustApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()