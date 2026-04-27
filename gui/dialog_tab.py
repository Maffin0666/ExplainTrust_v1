# gui/dialog_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from explaintrust import ExplainTrust
from .plotting import draw_dialog_dynamics

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


class DialogTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.engine = ExplainTrust()
        self._last_turns = None
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
        ttk.Button(ctrl, text="Оценить", command=self._evaluate_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Сохранить отчёт", command=self._save_report).pack(side=tk.LEFT, padx=5)

        ttk.Label(self, text="Текст диалога (LLM: ... / User: ...):", font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.dialog_text = tk.Text(self, height=10, wrap='word', font=('Segoe UI', 10), bg='#fafafa')
        self.dialog_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.BOTH, expand=True)

        table_frame = ttk.Frame(bottom)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        cols = ("#", "CTI", "Уровень")
        self.tree = ttk.Treeview(table_frame, columns=cols, show='headings', height=8)
        self.tree.heading("#", text="№")
        self.tree.heading("CTI", text="CTI")
        self.tree.heading("Уровень", text="Уровень доверия")
        self.tree.column("#", width=40, anchor='center')
        self.tree.column("CTI", width=75, anchor='center')
        self.tree.column("Уровень", width=120, anchor='center')
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.progress = ttk.Progressbar(table_frame, orient='horizontal', length=200, mode='determinate')
        self.progress.pack(pady=(5, 0))
        self.progress['maximum'] = 100
        self.avg_var = tk.StringVar(value="Средний CTI: —")
        ttk.Label(table_frame, textvariable=self.avg_var, font=('Segoe UI', 11, 'bold')).pack(pady=(5, 0))

        graph_frame = ttk.Frame(bottom)
        graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.fig, self.ax = plt.subplots(figsize=(6, 4.2))
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        draw_dialog_dynamics(self.ax, [], [])

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
        """Загружает диалог из JSON-файла (массив сообщений)."""
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                messagebox.showerror("Ошибка", "Ожидался массив сообщений")
                return

            # Формируем текст с префиксами, сохраняя переносы строк внутри сообщений
            lines = []
            for msg in data:
                role = msg.get('role', '').lower()
                content = msg.get('content', '')
                if role == 'llm':
                    prefix = "LLM: "
                elif role == 'user':
                    prefix = "User: "
                else:
                    prefix = ""
                # Заменяем внутренние переводы строк на отступ, чтобы не сломать парсинг
                content_escaped = content.replace('\n', '\n    ')
                lines.append(prefix + content_escaped)
            full_text = "\n".join(lines)

            self.dialog_text.delete("1.0", tk.END)
            self.dialog_text.insert("1.0", full_text)
            messagebox.showinfo("Успех", f"Загружено {len(data)} сообщений")
        except Exception as e:
            messagebox.showerror("Ошибка чтения", str(e))

    def _parse_dialog(self, raw):
        """Превращает текст диалога с префиксами LLM: / User: в список сообщений."""
        lines = raw.strip().splitlines()
        msgs = []
        cur_role = None
        cur_content = []
        for line in lines:
            # Удаляем отступы, добавленные при загрузке
            clean_line = line.lstrip()
            if clean_line.startswith("LLM:"):
                if cur_role and cur_content:
                    msgs.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
                cur_role = 'llm'
                cur_content = [clean_line[4:].strip()]
            elif clean_line.startswith("User:"):
                if cur_role and cur_content:
                    msgs.append({'role': cur_role, 'content': '\n'.join(cur_content).strip()})
                cur_role = 'user'
                cur_content = [clean_line[5:].strip()]
            else:
                if cur_role:
                    cur_content.append(clean_line)
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
            messagebox.showinfo("Информация", "Нет полных пар LLM→User")
            return

        self.tree.delete(*self.tree.get_children())
        cti_vals = []
        for i, t in enumerate(turns, 1):
            self.tree.insert("", tk.END, values=(i, t['CTI'], t['trust_level']))
            cti_vals.append(t['CTI'])
        avg = np.mean(cti_vals)
        self.avg_var.set(f"Средний CTI: {avg:.2f}")

        # Цветной прогресс-бар
        self.progress['value'] = avg
        style = ttk.Style()
        if avg >= 75:
            color = '#2E7D32'
        elif avg >= 55:
            color = '#388E3C'
        elif avg >= 35:
            color = '#F57F17'
        elif avg >= 15:
            color = '#E65100'
        else:
            color = '#B71C1C'
        style.configure("dialog.Horizontal.TProgressbar", background=color, troughcolor='#EEEEEE')
        self.progress.config(style="dialog.Horizontal.TProgressbar")

        draw_dialog_dynamics(self.ax, list(range(1, len(cti_vals) + 1)), cti_vals, avg)
        self.canvas.draw()
        self._last_turns = turns, cti_vals, avg

    def _save_report(self):
        if not self._last_turns:
            messagebox.showinfo("Информация", "Сначала выполните оценку диалога")
            return
        turns, cti_vals, avg = self._last_turns
        text = f"Отчёт ExplainTrust по диалогу\nДата: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        for i, t in enumerate(turns, 1):
            text += f"Пара {i}: CTI = {t['CTI']:.2f} ({t['trust_level']})\n"
        text += f"\nСредний CTI = {avg:.2f}\n"
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Текстовые файлы", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            messagebox.showinfo("Сохранено", "Отчёт сохранён")