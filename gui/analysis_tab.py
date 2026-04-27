# gui/analysis_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from explaintrust import ExplainTrust, fuzzy_engine
from skfuzzy import control as ctrl

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
    },
    {
        "name": "Длинный диалог (7 пар)",
        "messages": [
            {"role": "llm", "content": "Здравствуйте! Чем могу помочь?"},
            {"role": "user", "content": "Расскажите о преимуществах Python."},
            {"role": "llm", "content": "Python — язык с простым синтаксисом, огромным сообществом и библиотеками для науки, веба, автоматизации."},
            {"role": "user", "content": "А есть ли недостатки?"},
            {"role": "llm", "content": "Да, медленнее компилируемых языков, сложности с многопоточностью из-за GIL."},
            {"role": "user", "content": "Что такое GIL?"},
            {"role": "llm", "content": "Global Interpreter Lock блокирует выполнение нескольких потоков одновременно."},
            {"role": "user", "content": "Понял, спасибо! Помогло."},
            {"role": "llm", "content": "Обращайтесь!"},
            {"role": "user", "content": "Ок."},
            {"role": "llm", "content": "Если будут ещё вопросы, я здесь."},
            {"role": "user", "content": "Спасибо, пока что всё."},
            {"role": "llm", "content": "Хорошего дня!"},
            {"role": "user", "content": "И вам!"}
        ]
    }
]


class AnalysisTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.engine = ExplainTrust()
        self.turns = []
        self._build_ui()

    def _build_ui(self):
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(ctrl, text="Готовые диалоги:", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.dialog_combo = ttk.Combobox(ctrl, values=[d["name"] for d in BUILTIN_DIALOGS],
                                         state='readonly', width=30)
        self.dialog_combo.pack(side=tk.LEFT, padx=5)
        self.dialog_combo.bind('<<ComboboxSelected>>', self._load_dialog_example)

        ttk.Button(ctrl, text="Загрузить JSON", command=self._load_dialog_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Анализировать", command=self._analyze_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Radar", command=self._show_radar).pack(side=tk.LEFT, padx=5)

        ttk.Label(self, text="Текст диалога (LLM: ... / User: ...):", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.dialog_text = tk.Text(self, height=8, wrap='word', font=('Segoe UI', 10), bg='#fafafa')
        self.dialog_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.BOTH, expand=True)

        ttk.Label(bottom, text="Пара для анализа:").pack(anchor='w')
        self.turn_combo = ttk.Combobox(bottom, values=[], state='readonly')
        self.turn_combo.pack(fill='x', pady=(0, 5))
        self.turn_combo.bind('<<ComboboxSelected>>', self._show_turn_analysis)

        self.rules_tree = ttk.Treeview(bottom, columns=("rule", "activation"), show='headings', height=6)
        self.rules_tree.heading("rule", text="Активированные правила")
        self.rules_tree.heading("activation", text="Степень активации")
        self.rules_tree.column("rule", width=420)
        self.rules_tree.column("activation", width=100, anchor='center')
        self.rules_tree.pack(fill=tk.BOTH, expand=True, pady=5)

        self.feat_fig, self.feat_ax = plt.subplots(figsize=(5, 3))
        self.feat_canvas = FigureCanvasTkAgg(self.feat_fig, master=bottom)
        self.feat_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _load_dialog_example(self, event=None):
        name = self.dialog_combo.get()
        for d in BUILTIN_DIALOGS:
            if d["name"] == name:
                text = ""
                for msg in d["messages"]:
                    prefix = "LLM: " if msg['role'] == 'llm' else "User: "
                    text += prefix + msg['content'].replace('\n', '\n    ') + "\n"
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
                    text += prefix + msg['content'].replace('\n', '\n    ') + "\n"
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
            clean = line.lstrip()
            if clean.startswith("LLM:"):
                if cur_role and cur_content:
                    msgs.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
                cur_role = 'llm'
                cur_content = [clean[4:].strip()]
            elif clean.startswith("User:"):
                if cur_role and cur_content:
                    msgs.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
                cur_role = 'user'
                cur_content = [clean[5:].strip()]
            else:
                if cur_role:
                    cur_content.append(clean)
        if cur_role and cur_content:
            msgs.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
        return msgs

    def _analyze_dialog(self):
        raw = self.dialog_text.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showwarning("Предупреждение", "Введите или загрузите диалог")
            return
        messages = self._parse_dialog(raw)
        if len(messages) < 2:
            messagebox.showerror("Ошибка", "Нужна хотя бы одна пара LLM/User")
            return
        self.turns = self.engine.evaluate_dialog_turns(messages)
        if not self.turns:
            messagebox.showinfo("Информация", "Нет полных пар")
            return
        self.turn_combo['values'] = [f"Пара {i+1}" for i in range(len(self.turns))]
        self.turn_combo.current(0)
        self._show_turn_analysis()

    def _show_turn_analysis(self, event=None):
        idx = self.turn_combo.current()
        if idx < 0 or idx >= len(self.turns):
            return
        turn = self.turns[idx]

        system, _ = fuzzy_engine.build_system()
        input_data = {
            'SI': turn['SI'],
            'CM': turn['CM'],
            'LD': turn['LD'],
            'DM': turn['DM'],
            'FQ': turn['FQ'],
            'RL': turn['RL']
        }

        activations = []
        for rule in system.rules:
            act = 1.0
            for term in rule.antecedent_terms:
                var_name = term.parent.label
                val = input_data[var_name]
                mf = term.mf
                univ = term.parent.universe
                idx_val = np.argmin(np.abs(univ - val))
                act = min(act, mf[idx_val])
            # Правильный доступ к label терма консеквента
            if rule.consequent:
                cons_label = rule.consequent[0].term.label
            else:
                cons_label = "?"
            desc = f"IF {' AND '.join([f'{t.parent.label} is {t.label}' for t in rule.antecedent_terms])} THEN CTI is {cons_label}"
            activations.append((desc, act))

        self.rules_tree.delete(*self.rules_tree.get_children())
        for desc, act in activations:
            if act > 0.001:
                self.rules_tree.insert("", tk.END, values=(desc, f"{act:.3f}"))

        self.feat_ax.clear()
        features = ['SI', 'CM', 'LD', 'DM', 'FQ', 'RL']
        values = [turn[f] for f in features]
        colors = ['#1f77b4'] * 3 + ['#ff7f0e'] * 3
        self.feat_ax.bar(features, values, color=colors)
        self.feat_ax.set_title("Значения признаков для выбранной пары")
        self.feat_ax.set_ylim(0, 1)
        self.feat_canvas.draw()

    def _show_radar(self):
        try:
            turn = self.turns[self.turn_combo.current()]
        except:
            messagebox.showerror("Ошибка", "Сначала выполните анализ диалога")
            return
        top = tk.Toplevel(self)
        top.title("Radar-диаграмма признаков")
        fig, ax = plt.subplots(figsize=(5,5), subplot_kw=dict(polar=True))
        categories = ['SI', 'CM', 'LD', 'DM', 'FQ', 'RL']
        values = [turn['SI'], turn['CM'], turn['LD'], turn['DM'], turn['FQ'], turn['RL']]
        values += values[:1]
        angles = [n / 6 * 2 * np.pi for n in range(6)]
        angles += angles[:1]
        ax.plot(angles, values, 'o-', linewidth=2)
        ax.fill(angles, values, alpha=0.25)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 1)
        ax.set_title("Профиль признаков")
        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()