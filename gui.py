# gui.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import datetime

from explaintrust import ExplainTrust

# ================== Встроенные примеры ==================
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
        "name": "3. Умеренное доверие",
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
        self.root.geometry("1150x800")
        self.root.resizable(True, True)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', font=('Segoe UI', 9))
        style.configure('TButton', font=('Segoe UI', 9, 'bold'))
        style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))

        self.engine = ExplainTrust()
        self.chat_history = []   # [{role, content}, ...] для живого чата
        self.chat_turns = []     # результаты CTI по парам живого чата

        # Вкладки
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.single_frame = ttk.Frame(self.notebook, padding=10)
        self.dialog_frame = ttk.Frame(self.notebook, padding=10)
        self.chat_frame = ttk.Frame(self.notebook, padding=10)
        self.compare_frame = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.single_frame, text="Одиночный ответ")
        self.notebook.add(self.dialog_frame, text="Диалог")
        self.notebook.add(self.chat_frame, text="Живой чат")
        self.notebook.add(self.compare_frame, text="Сравнение")

        self._build_single_tab()
        self._build_dialog_tab()
        self._build_chat_tab()
        self._build_compare_tab()

    # ================== Утилиты ==================
    def _trust_color(self, cti):
        if cti >= 75:
            return '#2E7D32'
        elif cti >= 55:
            return '#388E3C'
        elif cti >= 35:
            return '#F57F17'
        elif cti >= 15:
            return '#E65100'
        else:
            return '#B71C1C'

    def _update_progress(self, bar, cti):
        bar['value'] = cti
        style_name = f"{bar}.Horizontal.TProgressbar"
        color = self._trust_color(cti)
        style = ttk.Style()
        style.configure(style_name, background=color, troughcolor='#EEEEEE')

    # ================== Одиночный ответ ==================
    def _build_single_tab(self):
        left = ttk.Frame(self.single_frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="Готовые примеры:", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.example_combo = ttk.Combobox(left, values=[e["name"] for e in BUILTIN_EXAMPLES], state='readonly')
        self.example_combo.pack(fill='x', pady=(0,5))
        self.example_combo.bind('<<ComboboxSelected>>', self._load_single_example)

        ttk.Button(left, text="Загрузить пару из JSON", command=self._load_single_json).pack(fill='x', pady=(0,5))
        ttk.Button(left, text="Сохранить отчёт", command=self._save_single_report).pack(fill='x', pady=(0,10))

        ttk.Label(left, text="Ответ LLM:", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.llm_text = tk.Text(left, height=8, wrap='word', font=('Segoe UI', 10), bg='#fafafa')
        self.llm_text.pack(fill=tk.BOTH, expand=True, pady=(0,10))

        ttk.Label(left, text="Реакция пользователя:", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.user_text = tk.Text(left, height=5, wrap='word', font=('Segoe UI', 10), bg='#fafafa')
        self.user_text.pack(fill=tk.BOTH, expand=True, pady=(0,10))

        ttk.Button(left, text="Оценить доверие", command=self._evaluate_single).pack(pady=8)

        self.single_progress = ttk.Progressbar(left, orient='horizontal', length=200, mode='determinate')
        self.single_progress.pack(pady=(5,0))
        self.single_progress['maximum'] = 100
        self.single_progress['value'] = 0

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
        ttk.Separator(self.result_frame, orient='horizontal').pack(fill='x', pady=5)
        ttk.Label(self.result_frame, text="Внешний локус:").pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.si_var).pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.cm_var).pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.ld_var).pack(anchor='w')
        ttk.Label(self.result_frame, text="Внутренний локус:").pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.dm_var).pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.fq_var).pack(anchor='w')
        ttk.Label(self.result_frame, textvariable=self.rl_var).pack(anchor='w')

        right = ttk.Frame(self.single_frame, padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.single_fig, self.single_ax = plt.subplots(figsize=(5.5, 4.2))
        self.single_canvas = FigureCanvasTkAgg(self.single_fig, master=right)
        self.single_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._draw_single_plot(None)

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
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'llm_response' in data and 'user_reply' in data:
                self.llm_text.delete("1.0", tk.END)
                self.llm_text.insert("1.0", data['llm_response'])
                self.user_text.delete("1.0", tk.END)
                self.user_text.insert("1.0", data['user_reply'])
                messagebox.showinfo("Успех", "Пара загружена")
            else:
                messagebox.showerror("Ошибка", "JSON должен содержать 'llm_response' и 'user_reply'")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _evaluate_single(self):
        llm = self.llm_text.get("1.0", tk.END).strip()
        user = self.user_text.get("1.0", tk.END).strip()
        if not llm or not user:
            messagebox.showwarning("Предупреждение", "Введите оба текста")
            return
        res = self.engine.evaluate({'llm_response': llm, 'user_reply': user})
        cti = res['CTI']
        self.cti_var.set(f"CTI: {cti:.2f}")
        self.trust_var.set(f"Уровень доверия: {res['trust_level']}")
        self.si_var.set(f"SI: {res['SI']:.4f}")
        self.cm_var.set(f"CM: {res['CM']:.4f}")
        self.ld_var.set(f"LD: {res['LD']:.4f}")
        self.dm_var.set(f"DM: {res['DM']:.4f}")
        self.fq_var.set(f"FQ: {res['FQ']}")
        self.rl_var.set(f"RL: {res['RL']:.4f}")
        self._update_progress(self.single_progress, cti)
        self._draw_single_plot(cti)
        self._last_single_result = res

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

    def _save_single_report(self):
        if not hasattr(self, '_last_single_result'):
            messagebox.showinfo("Информация", "Сначала выполните оценку")
            return
        res = self._last_single_result
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
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            messagebox.showinfo("Сохранено", "Отчёт сохранён")

    # ================== Диалог ==================
    def _build_dialog_tab(self):
        ctrl = ttk.Frame(self.dialog_frame)
        ctrl.pack(fill=tk.X, pady=(0,8))
        ttk.Label(ctrl, text="Готовые диалоги:", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=(0,5))
        self.dialog_combo = ttk.Combobox(ctrl, values=[d["name"] for d in BUILTIN_DIALOGS],
                                         state='readonly', width=30)
        self.dialog_combo.pack(side=tk.LEFT, padx=5)
        self.dialog_combo.bind('<<ComboboxSelected>>', self._load_dialog_example)
        ttk.Button(ctrl, text="Загрузить JSON", command=self._load_dialog_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Оценить", command=self._evaluate_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Сохранить отчёт", command=self._save_dialog_report).pack(side=tk.LEFT, padx=5)

        ttk.Label(self.dialog_frame, text="Текст диалога (LLM: ... / User: ...):", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.dialog_text = tk.Text(self.dialog_frame, height=10, wrap='word', font=('Segoe UI', 10), bg='#fafafa')
        self.dialog_text.pack(fill=tk.BOTH, expand=True, pady=(0,10))

        bottom = ttk.Frame(self.dialog_frame)
        bottom.pack(fill=tk.BOTH, expand=True)

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

        self.dialog_progress = ttk.Progressbar(table_frame, orient='horizontal', length=200, mode='determinate')
        self.dialog_progress.pack(pady=(5,0))
        self.dialog_progress['maximum'] = 100
        self.avg_var = tk.StringVar(value="Средний CTI: —")
        ttk.Label(table_frame, textvariable=self.avg_var, font=('Segoe UI', 11, 'bold')).pack(pady=(5,0))

        graph_frame = ttk.Frame(bottom)
        graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.dialog_fig, self.dialog_ax = plt.subplots(figsize=(6, 4.2))
        self.dialog_canvas = FigureCanvasTkAgg(self.dialog_fig, master=graph_frame)
        self.dialog_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._draw_dialog_plot([], [])

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
        if not path: return
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
        msgs = []
        cur_role = None
        cur_content = []
        for line in lines:
            if line.startswith("LLM:"):
                if cur_role and cur_content:
                    msgs.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
                cur_role = 'llm'
                cur_content = [line[4:].strip()]
            elif line.startswith("User:"):
                if cur_role and cur_content:
                    msgs.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
                cur_role = 'user'
                cur_content = [line[5:].strip()]
            else:
                if cur_role:
                    cur_content.append(line.strip())
        if cur_role and cur_content:
            msgs.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
        return msgs

    def _evaluate_dialog(self):
        raw = self.dialog_text.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("Предупреждение", "Введите или загрузите диалог")
            return
        messages = self._parse_dialog(raw)
        if len(messages) < 2:
            messagebox.showerror("Ошибка", "Нужна хотя бы одна пара LLM/User")
            return
        turns = self.engine.evaluate_dialog_turns(messages)
        if not turns:
            messagebox.showinfo("Информация", "Нет полных пар")
            return
        self.tree.delete(*self.tree.get_children())
        cti_vals = []
        for i, t in enumerate(turns, 1):
            self.tree.insert("", tk.END, values=(i, t['CTI'], t['trust_level']))
            cti_vals.append(t['CTI'])
        avg = np.mean(cti_vals)
        self.avg_var.set(f"Средний CTI: {avg:.2f}")
        self._update_progress(self.dialog_progress, avg)
        self._draw_dialog_plot(list(range(1, len(cti_vals)+1)), cti_vals, avg)
        self._last_dialog_turns = turns, cti_vals, avg

    def _draw_dialog_plot(self, x, y, avg=None):
        self.dialog_ax.clear()
        self.dialog_ax.set_title("Динамика когнитивного доверия", fontsize=12, pad=12)
        self.dialog_ax.set_xlabel("Номер пары")
        self.dialog_ax.set_ylabel("CTI")
        self.dialog_ax.grid(True, alpha=0.3)
        self.dialog_ax.axhspan(0, 15, facecolor='#FFCDD2', alpha=0.2)
        self.dialog_ax.axhspan(15, 35, facecolor='#FFE0B2', alpha=0.2)
        self.dialog_ax.axhspan(35, 55, facecolor='#FFF9C4', alpha=0.2)
        self.dialog_ax.axhspan(55, 75, facecolor='#C8E6C9', alpha=0.2)
        self.dialog_ax.axhspan(75, 100, facecolor='#BBDEFB', alpha=0.2)
        if x and y:
            self.dialog_ax.plot(x, y, 'o-', color='#1E88E5', linewidth=2, markersize=7, label='CTI')
            self.dialog_ax.set_xticks(x)
            self.dialog_ax.set_ylim(0, 105)
            if avg is not None:
                self.dialog_ax.axhline(avg, color='#D32F2F', linewidth=2, linestyle='--',
                                       label=f'Средний = {avg:.2f}')
        else:
            self.dialog_ax.set_ylim(0, 105)
        handles, labels = self.dialog_ax.get_legend_handles_labels()
        if handles:
            self.dialog_ax.legend(loc='upper right', fontsize='medium')
        self.dialog_canvas.draw()

    def _save_dialog_report(self):
        if not hasattr(self, '_last_dialog_turns'):
            messagebox.showinfo("Информация", "Сначала выполните оценку диалога")
            return
        turns, cti_vals, avg = self._last_dialog_turns
        text = f"Отчёт ExplainTrust по диалогу\nДата: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        for i, t in enumerate(turns, 1):
            text += f"Пара {i}: CTI = {t['CTI']:.2f} ({t['trust_level']})\n"
        text += f"\nСредний CTI = {avg:.2f}\n"
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            messagebox.showinfo("Сохранено", "Отчёт сохранён")

    # ================== Живой чат (без заглушки) ==================
    def _build_chat_tab(self):
        left = ttk.Frame(self.chat_frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,10))

        ttk.Label(left, text="Живой диалог (вводите реплики обеих сторон)", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.chat_history_text = tk.Text(left, height=15, wrap='word', font=('Segoe UI', 10),
                                         bg='#f0f0f0', state='disabled')
        self.chat_history_text.pack(fill=tk.BOTH, expand=True, pady=(5,10))

        # Панель ввода с выбором роли
        input_frame = ttk.Frame(left)
        input_frame.pack(fill='x', pady=(0,5))
        self.chat_role = tk.StringVar(value='user')
        ttk.Radiobutton(input_frame, text='LLM', variable=self.chat_role, value='llm').pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(input_frame, text='Пользователь', variable=self.chat_role, value='user').pack(side=tk.LEFT, padx=5)

        self.chat_input = ttk.Entry(left, font=('Segoe UI', 10))
        self.chat_input.pack(fill='x', pady=(0,5))
        self.chat_input.bind('<Return>', lambda e: self._send_chat_message())

        btn_frame = ttk.Frame(left)
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text="Отправить", command=self._send_chat_message).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Очистить историю", command=self._clear_chat).pack(side=tk.LEFT, padx=5)

        self.chat_progress = ttk.Progressbar(left, orient='horizontal', length=200, mode='determinate')
        self.chat_progress.pack(pady=(10,0))
        self.chat_progress['maximum'] = 100
        self.chat_cti_var = tk.StringVar(value="Текущий CTI: —")
        ttk.Label(left, textvariable=self.chat_cti_var, font=('Segoe UI', 11, 'bold')).pack()

        right = ttk.Frame(self.chat_frame)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.chat_fig, self.chat_ax = plt.subplots(figsize=(5.5, 4))
        self.chat_canvas = FigureCanvasTkAgg(self.chat_fig, master=right)
        self.chat_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._draw_chat_plot([], [])

    def _send_chat_message(self):
        text = self.chat_input.get().strip()
        if not text:
            return
        role = self.chat_role.get()
        self.chat_input.delete(0, tk.END)

        # Добавляем в историю
        self.chat_history.append({'role': role, 'content': text})

        # Отображаем в истории
        prefix = "LLM:" if role == 'llm' else "Вы:"
        self.chat_history_text.config(state='normal')
        self.chat_history_text.insert(tk.END, f"{prefix} {text}\n")
        self.chat_history_text.config(state='disabled')
        self.chat_history_text.see(tk.END)

        # Пересчитываем все пары
        turns = self.engine.evaluate_dialog_turns(self.chat_history)
        if turns:
            last = turns[-1]
            cti = last['CTI']
            self.chat_cti_var.set(f"Текущий CTI: {cti:.2f} ({last['trust_level']})")
            self._update_progress(self.chat_progress, cti)
            cti_vals = [t['CTI'] for t in turns]
            self._draw_chat_plot(list(range(1, len(cti_vals)+1)), cti_vals)
        else:
            self.chat_cti_var.set("Текущий CTI: —")
            self.chat_progress['value'] = 0
            self._draw_chat_plot([], [])

    def _clear_chat(self):
        self.chat_history.clear()
        self.chat_history_text.config(state='normal')
        self.chat_history_text.delete('1.0', tk.END)
        self.chat_history_text.config(state='disabled')
        self.chat_cti_var.set("Текущий CTI: —")
        self.chat_progress['value'] = 0
        self._draw_chat_plot([], [])

    def _draw_chat_plot(self, x, y):
        self.chat_ax.clear()
        self.chat_ax.set_title("Динамика CTI (живой чат)")
        self.chat_ax.set_xlabel("Ход")
        self.chat_ax.set_ylabel("CTI")
        self.chat_ax.grid(True, alpha=0.3)
        # Цветовые зоны
        self.chat_ax.axhspan(0, 25, facecolor='#FFCDD2', alpha=0.2)
        self.chat_ax.axhspan(25, 50, facecolor='#FFF9C4', alpha=0.2)
        self.chat_ax.axhspan(50, 75, facecolor='#C8E6C9', alpha=0.2)
        self.chat_ax.axhspan(75, 100, facecolor='#BBDEFB', alpha=0.2)
        if x and y:
            self.chat_ax.plot(x, y, 'mo-', markersize=6)
            self.chat_ax.set_xticks(x)
            self.chat_ax.set_ylim(0, 105)
        else:
            self.chat_ax.set_ylim(0, 105)
        self.chat_canvas.draw()

    # ================== Сравнение ==================
    def _build_compare_tab(self):
        top = ttk.Frame(self.compare_frame)
        top.pack(fill=tk.BOTH, expand=True)

        # Пара A
        left = ttk.LabelFrame(top, text="Пара A", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))

        ttk.Label(left, text="Пример A:").pack(anchor='w')
        self.comp_a_combo = ttk.Combobox(left, values=[e["name"] for e in BUILTIN_EXAMPLES],
                                         state='readonly', width=25)
        self.comp_a_combo.pack(anchor='w', pady=(0,5))
        self.comp_a_combo.bind('<<ComboboxSelected>>', lambda e: self._load_compare_example('A'))

        ttk.Label(left, text="LLM A:").pack(anchor='w')
        self.comp_a_llm = tk.Text(left, height=6, wrap='word', font=('Segoe UI', 9))
        self.comp_a_llm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(left, text="Пользователь A:").pack(anchor='w')
        self.comp_a_user = tk.Text(left, height=4, wrap='word', font=('Segoe UI', 9))
        self.comp_a_user.pack(fill=tk.BOTH, expand=True)

        # Пара B
        right = ttk.LabelFrame(top, text="Пара B", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(right, text="Пример B:").pack(anchor='w')
        self.comp_b_combo = ttk.Combobox(right, values=[e["name"] for e in BUILTIN_EXAMPLES],
                                         state='readonly', width=25)
        self.comp_b_combo.pack(anchor='w', pady=(0,5))
        self.comp_b_combo.bind('<<ComboboxSelected>>', lambda e: self._load_compare_example('B'))

        ttk.Label(right, text="LLM B:").pack(anchor='w')
        self.comp_b_llm = tk.Text(right, height=6, wrap='word', font=('Segoe UI', 9))
        self.comp_b_llm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(right, text="Пользователь B:").pack(anchor='w')
        self.comp_b_user = tk.Text(right, height=4, wrap='word', font=('Segoe UI', 9))
        self.comp_b_user.pack(fill=tk.BOTH, expand=True)

        ctrl = ttk.Frame(self.compare_frame)
        ctrl.pack(fill='x', pady=5)
        ttk.Button(ctrl, text="Сравнить", command=self._compare).pack(side=tk.LEFT, padx=5)

        self.comp_result = tk.StringVar(value="Результаты сравнения появятся здесь")
        ttk.Label(self.compare_frame, textvariable=self.comp_result, font=('Segoe UI', 10)).pack()

        self.comp_fig, self.comp_ax = plt.subplots(figsize=(7, 3.5))
        self.comp_canvas = FigureCanvasTkAgg(self.comp_fig, master=self.compare_frame)
        self.comp_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _load_compare_example(self, side):
        combo = self.comp_a_combo if side == 'A' else self.comp_b_combo
        name = combo.get()
        for ex in BUILTIN_EXAMPLES:
            if ex["name"] == name:
                if side == 'A':
                    self.comp_a_llm.delete("1.0", tk.END)
                    self.comp_a_llm.insert("1.0", ex["llm"])
                    self.comp_a_user.delete("1.0", tk.END)
                    self.comp_a_user.insert("1.0", ex["user"])
                else:
                    self.comp_b_llm.delete("1.0", tk.END)
                    self.comp_b_llm.insert("1.0", ex["llm"])
                    self.comp_b_user.delete("1.0", tk.END)
                    self.comp_b_user.insert("1.0", ex["user"])
                break

    def _compare(self):
        a_llm = self.comp_a_llm.get("1.0", tk.END).strip()
        a_user = self.comp_a_user.get("1.0", tk.END).strip()
        b_llm = self.comp_b_llm.get("1.0", tk.END).strip()
        b_user = self.comp_b_user.get("1.0", tk.END).strip()
        if not all([a_llm, a_user, b_llm, b_user]):
            messagebox.showwarning("Предупреждение", "Заполните оба примера")
            return
        res_a = self.engine.evaluate({'llm_response': a_llm, 'user_reply': a_user})
        res_b = self.engine.evaluate({'llm_response': b_llm, 'user_reply': b_user})
        self.comp_result.set(f"A: CTI = {res_a['CTI']:.2f} ({res_a['trust_level']})   |   "
                             f"B: CTI = {res_b['CTI']:.2f} ({res_b['trust_level']})")
        self.comp_ax.clear()
        self.comp_ax.set_title("Сравнение CTI")
        self.comp_ax.set_xlabel("CTI")
        self.comp_ax.set_ylabel("Принадлежность")
        self.comp_ax.grid(True, alpha=0.3)
        import skfuzzy as fuzz
        x = np.arange(0, 101, 1)
        self.comp_ax.plot(x, fuzz.trapmf(x, [0,0,15,25]), '#D32F2F', label='Очень низкое')
        self.comp_ax.plot(x, fuzz.trimf(x, [15,30,45]), '#F57C00', label='Низкое')
        self.comp_ax.plot(x, fuzz.trimf(x, [35,50,65]), '#FBC02D', label='Среднее')
        self.comp_ax.plot(x, fuzz.trimf(x, [55,70,85]), '#388E3C', label='Высокое')
        self.comp_ax.plot(x, fuzz.trapmf(x, [75,85,100,100]), '#1976D2', label='Очень высокое')
        self.comp_ax.axvline(res_a['CTI'], color='green', linestyle='--', label=f'A: {res_a["CTI"]:.1f}')
        self.comp_ax.axvline(res_b['CTI'], color='red', linestyle='--', label=f'B: {res_b["CTI"]:.1f}')
        self.comp_ax.legend(loc='upper left', fontsize='small')
        self.comp_canvas.draw()


if __name__ == '__main__':
    root = tk.Tk()
    app = ExplainTrustGUI(root)
    root.mainloop()