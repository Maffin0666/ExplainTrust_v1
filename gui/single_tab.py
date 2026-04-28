# gui/single_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import datetime

from explaintrust import ExplainTrust
from .plotting import draw_trust_membership
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

BUILTIN_EXAMPLES = [
    {
        "name": "1. Высокое доверие",
        "llm": ("Согласно анализу, основными причинами являются: во-первых, "
                "устаревшие библиотеки, во-вторых, некорректный кэш. Поэтому "
                "рекомендуется обновить зависимости и изменить конфигурацию. "
                "Более того, утечек памяти не обнаружено."),
        "user": "Понял, спасибо за подробный ответ!"
    },
    {
        "name": "2. Низкое доверие",
        "llm": "Производительность упала из-за ошибок. Надо исправить.",
        "user": "Почему вы так решили? Я не уверен, может быть, проблема в сети?"
    },
    {
        "name": "3. Очень низкое доверие",
        "llm": "Вероятная причина – нагрузка на базу данных. Также проверьте пул соединений.",
        "user": "Хорошо, я проверю. Возможно, вы правы."
    },
    {
        "name": "4. Короткое согласие",
        "llm": "Ошибка исправлена в последнем обновлении.",
        "user": "Ок."
    },
    {
        "name": "5. Развёрнутый переспрос",
        "llm": "Система работает стабильно.",
        "user": "Как вы можете это утверждать? Уточните, откуда такая информация?"
    },
    {
        "name": "6. Шаблонный ответ, принятие",
        "llm": "Для решения проблемы перезагрузите устройство.",
        "user": "Спасибо, попробую."
    }
]

class SingleTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.engine = ExplainTrust()
        self._last_result = None
        self._build_ui()

    def _build_ui(self):
        left = ttk.Frame(self)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="Готовые примеры:", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.example_combo = ttk.Combobox(left, values=[e["name"] for e in BUILTIN_EXAMPLES], state='readonly')
        self.example_combo.pack(fill='x', pady=(0, 5))
        self.example_combo.bind('<<ComboboxSelected>>', self._load_example)

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill='x', pady=(0, 5))
        ttk.Button(btn_frame, text="Загрузить пару из JSON", command=self._load_json).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="?", width=3, command=lambda: messagebox.showinfo(
            "Справка: Одиночный ответ",
            "Оцените одну диалоговую пару.\n\n"
            "SI – структурная целостность (0..1)\n"
            "CM – дискурсивные маркеры (0..0.15)\n"
            "LD – лексическое разнообразие (0..1)\n"
            "DM – маркеры сомнения в ответе пользователя (0..1)\n"
            "FQ – наличие переспроса (0/1)\n"
            "RL – длина ответа, нормированная на 50 слов (0..1)\n\n"
            "CTI – итоговый индекс доверия (0–100)."
        )).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Сохранить отчёт", command=self._save_report).pack(side=tk.LEFT)

        ttk.Label(left, text="Ответ LLM:", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.llm_text = tk.Text(left, height=8, wrap='word', font=('Segoe UI', 10), bg='#fafafa')
        self.llm_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(left, text="Реакция пользователя:", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.user_text = tk.Text(left, height=5, wrap='word', font=('Segoe UI', 10), bg='#fafafa')
        self.user_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Button(left, text="Оценить доверие", command=self._evaluate).pack(pady=8)

        self.progress = ttk.Progressbar(left, orient='horizontal', length=200, mode='determinate')
        self.progress.pack(pady=(5, 0))
        self.progress['maximum'] = 100
        self.progress['value'] = 0

        result_frame = ttk.LabelFrame(left, text="Результаты", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.cti_var = tk.StringVar(value="CTI: —")
        self.trust_var = tk.StringVar(value="Уровень доверия: —")
        self.si_var = tk.StringVar(value="SI: —")
        self.cm_var = tk.StringVar(value="CM: —")
        self.ld_var = tk.StringVar(value="LD: —")
        self.dm_var = tk.StringVar(value="DM: —")
        self.fq_var = tk.StringVar(value="FQ: —")
        self.rl_var = tk.StringVar(value="RL: —")

        ttk.Label(result_frame, textvariable=self.cti_var, font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(result_frame, textvariable=self.trust_var, font=('Segoe UI', 10)).pack(anchor='w')
        ttk.Separator(result_frame, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(result_frame, text="Внешний локус (качество ответа ИИ):").pack(anchor='w')
        ttk.Label(result_frame, textvariable=self.si_var).pack(anchor='w')
        ttk.Label(result_frame, textvariable=self.cm_var).pack(anchor='w')
        ttk.Label(result_frame, textvariable=self.ld_var).pack(anchor='w')
        ttk.Label(result_frame, text="Внутренний локус (реакция пользователя):").pack(anchor='w')
        ttk.Label(result_frame, textvariable=self.dm_var).pack(anchor='w')
        ttk.Label(result_frame, textvariable=self.fq_var).pack(anchor='w')
        ttk.Label(result_frame, textvariable=self.rl_var).pack(anchor='w')

        right = ttk.Frame(self, padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.fig, self.ax = plt.subplots(figsize=(5.5, 4.2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        draw_trust_membership(self.ax)
        self.canvas.draw()

    def _load_example(self, event=None):
        name = self.example_combo.get()
        for ex in BUILTIN_EXAMPLES:
            if ex["name"] == name:
                self.llm_text.delete("1.0", tk.END)
                self.llm_text.insert("1.0", ex["llm"])
                self.user_text.delete("1.0", tk.END)
                self.user_text.insert("1.0", ex["user"])
                break

    def _load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'llm_response' in data and 'user_reply' in data:
                self.llm_text.delete("1.0", tk.END)
                self.llm_text.insert("1.0", data['llm_response'])
                self.user_text.delete("1.0", tk.END)
                self.user_text.insert("1.0", data['user_reply'])
                messagebox.showinfo("Успех", "Диалоговая пара загружена")
            else:
                messagebox.showerror("Ошибка", "JSON должен содержать ключи 'llm_response' и 'user_reply'")
        except Exception as e:
            messagebox.showerror("Ошибка чтения", str(e))

    def _evaluate(self):
        llm = self.llm_text.get("1.0", tk.END).strip()
        user = self.user_text.get("1.0", tk.END).strip()
        if not llm or not user:
            messagebox.showwarning("Предупреждение", "Введите оба текста")
            return
        try:
            res = self.engine.evaluate({'llm_response': llm, 'user_reply': user})
        except Exception as e:
            messagebox.showerror("Ошибка обработки", str(e))
            return

        cti = res['CTI']
        self.cti_var.set(f"CTI: {cti:.2f}")
        self.trust_var.set(f"Уровень доверия: {res['trust_level']}")
        self.si_var.set(f"SI (структурная целостность): {res['SI']:.4f}")
        self.cm_var.set(f"CM (маркеры связности): {res['CM']:.4f}")
        self.ld_var.set(f"LD (лексическое разнообразие): {res['LD']:.4f}")
        self.dm_var.set(f"DM (маркеры сомнения): {res['DM']:.4f}")
        self.fq_var.set(f"FQ (наличие переспроса): {res['FQ']}")
        self.rl_var.set(f"RL (норм. длина ответа): {res['RL']:.4f}")

        self.progress['value'] = cti
        style_name = f"custom.Horizontal.TProgressbar"
        style = ttk.Style()
        if cti >= 75:
            color = '#2E7D32'
        elif cti >= 55:
            color = '#388E3C'
        elif cti >= 35:
            color = '#F57F17'
        elif cti >= 15:
            color = '#E65100'
        else:
            color = '#B71C1C'
        style.configure(style_name, background=color, troughcolor='#EEEEEE')
        self.progress.config(style=style_name)

        draw_trust_membership(self.ax, cti)
        self.canvas.draw()
        self._last_result = res

    def _save_report(self):
        if not self._last_result:
            messagebox.showinfo("Информация", "Сначала выполните оценку")
            return
        res = self._last_result
        text = f"""Отчёт ExplainTrust
Дата: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Ответ LLM:
{self.llm_text.get('1.0', tk.END).strip()}

Реакция пользователя:
{self.user_text.get('1.0', tk.END).strip()}

Результаты:
CTI = {res['CTI']:.2f} ({res['trust_level']})
Внешний локус: SI={res['SI']:.4f}, CM={res['CM']:.4f}, LD={res['LD']:.4f}
Внутренний локус: DM={res['DM']:.4f}, FQ={res['FQ']}, RL={res['RL']:.4f}
"""
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Текстовые файлы", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            messagebox.showinfo("Сохранено", "Отчёт сохранён")