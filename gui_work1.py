# gui.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

from explaintrust import ExplainTrust

# ---------- Примеры ----------
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

BUILTIN_DIALOGS = [
    {
        "name": "Доверительный диалог",
        "messages": [
            {"role": "llm", "content": "Согласно анализу, основная причина задержек – "
                                     "неоптимальные SQL-запросы. Во-первых, отсутствуют индексы, "
                                     "во-вторых, много JOIN-ов. Рекомендую добавить индексы."},
            {"role": "user", "content": "Понял, спасибо. Сделаю."},
            {"role": "llm", "content": "Также обратите внимание на кэширование – "
                                     "в логах видны повторные загрузки одних и тех же данных."},
            {"role": "user", "content": "Хорошо, я проверю конфигурацию кэша."},
            {"role": "llm", "content": "Отличная идея. Если появятся вопросы – обращайтесь."},
            {"role": "user", "content": "Спасибо, пока вопросов нет."}
        ]
    },
    {
        "name": "Недоверчивый диалог",
        "messages": [
            {"role": "llm", "content": "Производительность упала из-за ошибок. Надо исправить."},
            {"role": "user", "content": "Почему вы так решили? Я не уверен, что проблема только в этом."},
            {"role": "llm", "content": "Я проанализировал логи и вижу аномалии в ответах базы данных."},
            {"role": "user", "content": "Может быть, дело в сетевых задержках? Ваши логи могут быть неполными."},
            {"role": "llm", "content": "Сетевые задержки в норме. Источник именно в запросах."},
            {"role": "user", "content": "Вряд ли. Я перепроверю всё сам."}
        ]
    },
    {
        "name": "Смешанный диалог (рост доверия)",
        "messages": [
            {"role": "llm", "content": "Проблема, скорее всего, в конфигурации веб-сервера."},
            {"role": "user", "content": "Почему? Я не вижу связи."},
            {"role": "llm", "content": "Логи показывают большое количество 5xx ошибок. "
                                     "Вот подробный отчёт (прилагаю)."},
            {"role": "user", "content": "Хорошо, это убедительно. Я проверю настройки сервера."},
            {"role": "llm", "content": "Если потребуется помощь с конкретными параметрами, дайте знать."},
            {"role": "user", "content": "Спасибо, я разобрался. Ваш анализ помог."}
        ]
    }
]


class ExplainTrustGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ExplainTrust – оценка когнитивного доверия")
        self.root.geometry("1100x750")
        self.root.resizable(True, True)

        # Приятная тема ttk
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', font=('Segoe UI', 9))
        style.configure('TButton', font=('Segoe UI', 9, 'bold'))
        style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))

        self.engine = ExplainTrust()

        # Вкладки
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.single_frame = ttk.Frame(self.notebook, padding=10)
        self.dialog_frame = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.single_frame, text="Одиночный ответ")
        self.notebook.add(self.dialog_frame, text="Диалог")

        self._build_single_tab()
        self._build_dialog_tab()

    # ========================== Одиночный ответ ==========================
    def _build_single_tab(self):
        left = ttk.Frame(self.single_frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="Готовые примеры:", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.example_combo = ttk.Combobox(left, values=[e["name"] for e in BUILTIN_EXAMPLES],
                                          state='readonly')
        self.example_combo.pack(fill='x', pady=(0,5))
        self.example_combo.bind('<<ComboboxSelected>>', self._load_single_example)

        ttk.Button(left, text="Загрузить пару из JSON", command=self._load_single_json).pack(fill='x', pady=(0,10))

        ttk.Label(left, text="Ответ языковой модели (LLM):", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.llm_text = tk.Text(left, height=8, wrap='word', font=('Segoe UI', 10),
                                bg='#fafafa', relief='solid', borderwidth=1)
        self.llm_text.pack(fill=tk.BOTH, expand=True, pady=(0,10))

        ttk.Label(left, text="Реакция пользователя:", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.user_text = tk.Text(left, height=5, wrap='word', font=('Segoe UI', 10),
                                 bg='#fafafa', relief='solid', borderwidth=1)
        self.user_text.pack(fill=tk.BOTH, expand=True, pady=(0,10))

        ttk.Button(left, text="Оценить доверие", command=self._evaluate_single).pack(pady=8)

        # Результаты
        self.result_frame = ttk.LabelFrame(left, text="Результаты", padding=10)
        self.result_frame.pack(fill=tk.BOTH, expand=True)

        self.cti_var = tk.StringVar(value="CTI: —")
        self.trust_var = tk.StringVar(value="Уровень доверия: —")
        self.si_var = tk.StringVar(value="SI: —")
        self.cm_var = tk.StringVar(value="CM: —")
        self.ld_var = tk.StringVar(value="LD: —")
        self.dm_var = tk.StringVar(value="DM: —")
        self.fq_var = tk.StringVar(value="FQ: —")
        self.rl_var = tk.StringVar(value="RL: —")

        ttk.Label(self.result_frame, textvariable=self.cti_var, font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.trust_var, font=('Segoe UI', 10)).pack(anchor='w')
        ttk.Separator(self.result_frame, orient='horizontal').pack(fill='x', pady=8)
        ttk.Label(self.result_frame, text="Внешний локус (качество ответа ИИ):").pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.si_var).pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.cm_var).pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.ld_var).pack(anchor='w')
        ttk.Label(self.result_frame, text="Внутренний локус (реакция пользователя):").pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.dm_var).pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.fq_var).pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.rl_var).pack(anchor='w')

        # График
        right = ttk.Frame(self.single_frame, padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.single_fig, self.single_ax = plt.subplots(figsize=(5.5, 4.2))
        self.single_canvas = FigureCanvasTkAgg(self.single_fig, master=right)
        self.single_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._draw_single_plot(None)

    # ========================== Диалог ==========================
    def _build_dialog_tab(self):
        # Панель управления
        ctrl = ttk.Frame(self.dialog_frame)
        ctrl.pack(fill=tk.X, pady=(0,8))

        ttk.Label(ctrl, text="Готовые диалоги:", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=(0,5))
        self.dialog_combo = ttk.Combobox(ctrl, values=[d["name"] for d in BUILTIN_DIALOGS],
                                         state='readonly', width=30)
        self.dialog_combo.pack(side=tk.LEFT, padx=5)
        self.dialog_combo.bind('<<ComboboxSelected>>', self._load_dialog_example)

        ttk.Button(ctrl, text="Загрузить JSON", command=self._load_dialog_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Оценить диалог", command=self._evaluate_dialog).pack(side=tk.LEFT, padx=5)

        # Поле диалога
        ttk.Label(self.dialog_frame, text="Текст диалога (LLM: ... / User: ...):",
                  font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.dialog_text = tk.Text(self.dialog_frame, height=10, wrap='word', font=('Segoe UI', 10),
                                   bg='#fafafa', relief='solid', borderwidth=1)
        self.dialog_text.pack(fill=tk.BOTH, expand=True, pady=(0,10))

        # Нижняя часть: таблица + график + среднее
        bottom = ttk.Frame(self.dialog_frame)
        bottom.pack(fill=tk.BOTH, expand=True)

        # Таблица с результатами
        table_frame = ttk.Frame(bottom)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))

        cols = ("#", "CTI", "Уровень")
        self.tree = ttk.Treeview(table_frame, columns=cols, show='headings', height=8)
        self.tree.heading("#", text="№")
        self.tree.heading("CTI", text="CTI")
        self.tree.heading("Уровень", text="Уровень доверия")
        self.tree.column("#", width=40, anchor='center')
        self.tree.column("CTI", width=75, anchor='center')
        self.tree.column("Уровень", width=120, anchor='center')
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Средний CTI
        self.avg_var = tk.StringVar(value="Средний CTI: —")
        ttk.Label(table_frame, textvariable=self.avg_var, font=('Segoe UI', 11, 'bold'),
                  foreground='#2E7D32').pack(pady=(8, 0))

        # График
        graph_frame = ttk.Frame(bottom)
        graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.dialog_fig, self.dialog_ax = plt.subplots(figsize=(6, 4.2))
        self.dialog_canvas = FigureCanvasTkAgg(self.dialog_fig, master=graph_frame)
        self.dialog_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._draw_dialog_plot([], [])

    # -------- Одиночные методы --------
    def _load_single_example(self, event=None):
        name = self.example_combo.get()
        for ex in BUILTIN_EXAMPLES:
            if ex["name"] == name:
                self.llm_text.delete("1.0", tk.END)
                self.llm_text.insert("1.0", ex["llm"])
                self.user_text.delete("1.0", tk.END)
                self.user_text.insert("1.0", ex["user"])
                break

    def _load_single_json(self):
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
                messagebox.showinfo("Успех", "Пара загружена")
            else:
                messagebox.showerror("Ошибка", "JSON должен содержать 'llm_response' и 'user_reply'")
        except Exception as e:
            messagebox.showerror("Ошибка чтения", str(e))

    def _evaluate_single(self):
        llm = self.llm_text.get("1.0", tk.END).strip()
        user = self.user_text.get("1.0", tk.END).strip()
        if not llm or not user:
            messagebox.showwarning("Предупреждение", "Введите оба текста")
            return
        try:
            res = self.engine.evaluate({'llm_response': llm, 'user_reply': user})
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return

        self.cti_var.set(f"CTI: {res['CTI']:.2f}")
        self.trust_var.set(f"Уровень доверия: {res['trust_level']}")
        self.si_var.set(f"SI: {res['SI']:.4f}")
        self.cm_var.set(f"CM: {res['CM']:.4f}")
        self.ld_var.set(f"LD: {res['LD']:.4f}")
        self.dm_var.set(f"DM: {res['DM']:.4f}")
        self.fq_var.set(f"FQ: {res['FQ']}")
        self.rl_var.set(f"RL: {res['RL']:.4f}")
        self._draw_single_plot(res['CTI'])

    def _draw_single_plot(self, cti_val):
        self.single_ax.clear()
        self.single_ax.set_title("Функции принадлежности CTI", fontsize=11)
        self.single_ax.set_xlabel("CTI")
        self.single_ax.set_ylabel("Принадлежность")
        self.single_ax.grid(True, alpha=0.3)

        import skfuzzy as fuzz
        x = np.arange(0, 101, 1)
        self.single_ax.plot(x, fuzz.trapmf(x, [0,0,15,25]), '#D32F2F', label='Очень низкое')
        self.single_ax.plot(x, fuzz.trimf(x, [15,30,45]), '#F57C00', label='Низкое')
        self.single_ax.plot(x, fuzz.trimf(x, [35,50,65]), '#FBC02D', label='Среднее')
        self.single_ax.plot(x, fuzz.trimf(x, [55,70,85]), '#388E3C', label='Высокое')
        self.single_ax.plot(x, fuzz.trapmf(x, [75,85,100,100]), '#1976D2', label='Очень высокое')
        if cti_val is not None:
            self.single_ax.axvline(cti_val, color='black', linewidth=2, linestyle='--',
                                   label=f'CTI = {cti_val:.2f}')
        self.single_ax.legend(loc='upper left', fontsize='small')
        self.single_canvas.draw()

    # -------- Диалоговые методы --------
    def _load_dialog_example(self, event=None):
        name = self.dialog_combo.get()
        for d in BUILTIN_DIALOGS:
            if d["name"] == name:
                text = ""
                for msg in d["messages"]:
                    prefix = "LLM: " if msg['role'] == 'llm' else "User: "
                    text += prefix + msg['content'] + "\n"
                self.dialog_text.delete("1.0", tk.END)
                self.dialog_text.insert("1.0", text.strip())
                break

    def _load_dialog_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                text = ""
                for msg in data:
                    if msg['role'] == 'llm':
                        prefix = "LLM: "
                    elif msg['role'] == 'user':
                        prefix = "User: "
                    else:
                        prefix = ""
                    text += prefix + msg['content'] + "\n"
                self.dialog_text.delete("1.0", tk.END)
                self.dialog_text.insert("1.0", text.strip())
                messagebox.showinfo("Успех", "Диалог загружен")
            else:
                messagebox.showerror("Ошибка", "Ожидался массив сообщений")
        except Exception as e:
            messagebox.showerror("Ошибка чтения", str(e))

    def _parse_dialog(self, raw):
        lines = raw.strip().splitlines()
        messages = []
        cur_role = None
        cur_content = []
        for line in lines:
            if line.startswith("LLM:"):
                if cur_role and cur_content:
                    messages.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
                cur_role = 'llm'
                cur_content = [line[4:].strip()]
            elif line.startswith("User:"):
                if cur_role and cur_content:
                    messages.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
                cur_role = 'user'
                cur_content = [line[5:].strip()]
            else:
                if cur_role:
                    cur_content.append(line.strip())
        if cur_role and cur_content:
            messages.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
        return messages

    def _evaluate_dialog(self):
        raw = self.dialog_text.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("Предупреждение", "Введите или загрузите диалог")
            return

        messages = self._parse_dialog(raw)
        if len(messages) < 2:
            messagebox.showerror("Ошибка", "Диалог должен содержать хотя бы одну пару LLM/User")
            return

        try:
            turns = self.engine.evaluate_dialog_turns(messages)
        except Exception as e:
            messagebox.showerror("Ошибка обработки", str(e))
            return

        if not turns:
            messagebox.showinfo("Информация", "Не найдено ни одной полной пары LLM → User")
            return

        # Таблица
        self.tree.delete(*self.tree.get_children())
        cti_vals = []
        for i, t in enumerate(turns, 1):
            self.tree.insert("", tk.END, values=(i, t['CTI'], t['trust_level']))
            cti_vals.append(t['CTI'])

        # Среднее
        avg = np.mean(cti_vals)
        self.avg_var.set(f"Средний CTI: {avg:.2f}")

        # График с зонами и средней линией
        self._draw_dialog_plot(list(range(1, len(cti_vals)+1)), cti_vals, avg)

    def _draw_dialog_plot(self, x, y, avg=None):
        self.dialog_ax.clear()
        self.dialog_ax.set_title("Динамика когнитивного доверия", fontsize=12, pad=12)
        self.dialog_ax.set_xlabel("Номер пары (ход)")
        self.dialog_ax.set_ylabel("CTI")
        self.dialog_ax.grid(True, alpha=0.3)

        # Цветовые зоны уровней доверия
        self.dialog_ax.axhspan(0, 15, facecolor='#FFCDD2', alpha=0.2)      # очень низкое
        self.dialog_ax.axhspan(15, 35, facecolor='#FFE0B2', alpha=0.2)     # низкое
        self.dialog_ax.axhspan(35, 55, facecolor='#FFF9C4', alpha=0.2)     # среднее
        self.dialog_ax.axhspan(55, 75, facecolor='#C8E6C9', alpha=0.2)     # высокое
        self.dialog_ax.axhspan(75, 100, facecolor='#BBDEFB', alpha=0.2)    # очень высокое

        if x and y:
            self.dialog_ax.plot(x, y, 'o-', color='#1E88E5', linewidth=2, markersize=7, label='CTI')
            self.dialog_ax.set_xticks(x)
            self.dialog_ax.set_ylim(0, 105)

            if avg is not None:
                self.dialog_ax.axhline(avg, color='#D32F2F', linewidth=2, linestyle='--',
                                       label=f'Средний CTI = {avg:.2f}')
        else:
            self.dialog_ax.set_ylim(0, 105)
        if self.dialog_ax.get_legend_handles_labels()[0]:
            self.dialog_ax.legend(loc='upper right', fontsize='medium')
        self.dialog_canvas.draw()


if __name__ == '__main__':
    root = tk.Tk()
    app = ExplainTrustGUI(root)
    root.mainloop()