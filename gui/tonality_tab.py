# gui/tonality_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from nltk.stem.snowball import SnowballStemmer

from explaintrust import ExplainTrust

POSITIVE_WORDS = {
    "отлично", "прекрасно", "замечательно", "хорошо", "верно", "правильно", "убедительно",
    "понял", "поняла", "согласен", "согласна", "спасибо", "благодарю", "ясно", "логично",
    "точно", "именно", "разумеется", "конечно", "совершенно", "верно", "правда", "добро",
    "супер", "великолепно", "чудесно", "отличный", "хороший", "полезный", "интересно",
    "здорово", "класс", "ок", "да", "ага", "угу",
    "помогло", "помог", "помогла", "разобрался", "разобралась"
}

NEGATIVE_WORDS = {
    "плохо", "ужасно", "неверно", "неправильно", "нет", "ничего", "ерунда", "чушь", "бред",
    "глупость", "сомневаюсь", "не уверен", "не уверена", "вряд ли", "не согласен",
    "не согласна", "ошибка", "не работает", "ерунда", "фигня", "отвратительно",
    "не помогло", "не понял", "не поняла", "тупик", "бесполезно", "ни о чём",
    "не верю", "чепуха", "глупо", "не логично", "странно", "подозрительно"
}

stemmer = SnowballStemmer('russian')
POS_STEMS = {stemmer.stem(w) for w in POSITIVE_WORDS}
NEG_STEMS = {stemmer.stem(w) for w in NEGATIVE_WORDS}

def simple_sentiment(text):
    words = text.lower().split()
    if not words:
        return 0.0
    pos = 0
    neg = 0
    for w in words:
        s = stemmer.stem(w)
        if s in POS_STEMS:
            pos += 1
        elif s in NEG_STEMS:
            neg += 1
    return (pos - neg) / len(words)

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

class TonalityTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.engine = ExplainTrust()
        self.messages = []
        self.cbar = None
        self._build_ui()

    def _build_ui(self):
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(ctrl, text="Готовые диалоги:", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.dialog_combo = ttk.Combobox(ctrl, values=[d["name"] for d in BUILTIN_DIALOGS],
                                         state='readonly', width=30)
        self.dialog_combo.pack(side=tk.LEFT, padx=5)
        self.dialog_combo.bind('<<ComboboxSelected>>', self._on_select_example)

        ttk.Button(ctrl, text="Загрузить JSON", command=self._load_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Анализировать тональность", command=self._analyze_tonality).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="?", width=3, command=lambda: messagebox.showinfo(
            "Справка: Тональность",
            "Оценивается простой словарной моделью: подсчитывается доля позитивных и негативных слов.\n"
            "График показывает зависимость CTI от тональности сообщений LLM (круги) и пользователя (крестики).\n"
            "Фон: красный – негативная зона, зелёный – позитивная.\n"
            "Цвет точек соответствует CTI (красный – низкий, зелёный – высокий)."
        )).pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(ctrl, text="Диалог не выбран", foreground='gray')
        self.status_label.pack(side=tk.LEFT, padx=10)

        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        table_frame = ttk.Frame(paned)
        cols = ("#", "CTI", "Тональность LLM", "Тональность User")
        self.table = ttk.Treeview(table_frame, columns=cols, show='headings', height=5)
        self.table.heading("#", text="№")
        self.table.heading("CTI", text="CTI")
        self.table.heading("Тональность LLM", text="Тональность LLM")
        self.table.heading("Тональность User", text="Тональность User")
        self.table.column("#", width=40, anchor='center')
        self.table.column("CTI", width=70, anchor='center')
        self.table.column("Тональность LLM", width=120, anchor='center')
        self.table.column("Тональность User", width=120, anchor='center')
        self.table.pack(fill=tk.BOTH, expand=True)
        paned.add(table_frame, weight=1)

        graph_frame = ttk.Frame(paned)
        self.fig, self.ax = plt.subplots(figsize=(7, 4.5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        paned.add(graph_frame, weight=3)

        ttk.Label(self, text="Упрощённый анализ тональности на основе словарей. "
                             "CTI vs. доля позитивных/негативных слов.",
                  font=('Segoe UI', 8), foreground='gray').pack(pady=(5, 0))

    def _on_select_example(self, event=None):
        name = self.dialog_combo.get()
        for d in BUILTIN_DIALOGS:
            if d["name"] == name:
                self.messages = d["messages"]
                self.status_label.config(text=f"Выбран: {name}")
                self._analyze_tonality()
                break

    def _load_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                self.messages = data
                self.status_label.config(text=f"Загружено {len(data)} сообщений")
                self._analyze_tonality()
            else:
                messagebox.showerror("Ошибка", "Ожидался массив сообщений")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _analyze_tonality(self):
        if not self.messages:
            messagebox.showwarning("Предупреждение", "Сначала загрузите или выберите диалог")
            return
        pairs = []
        sentiments_llm = []
        sentiments_user = []
        ctis = []
        i = 0
        while i < len(self.messages) - 1:
            if self.messages[i]['role'] == 'llm' and self.messages[i+1]['role'] == 'user':
                llm_text = self.messages[i]['content']
                user_text = self.messages[i+1]['content']
                try:
                    res = self.engine.evaluate({'llm_response': llm_text, 'user_reply': user_text})
                except Exception:
                    i += 2
                    continue
                cti = res['CTI']
                sent_llm = simple_sentiment(llm_text)
                sent_user = simple_sentiment(user_text)
                pairs.append((len(pairs)+1, cti, sent_llm, sent_user))
                sentiments_llm.append(sent_llm)
                sentiments_user.append(sent_user)
                ctis.append(cti)
                i += 2
            else:
                i += 1
        if not pairs:
            messagebox.showinfo("Результат", "Нет полных пар LLM/User")
            return
        self.table.delete(*self.table.get_children())
        for idx, cti, s_llm, s_user in pairs:
            self.table.insert("", tk.END, values=(idx, f"{cti:.2f}", f"{s_llm:.3f}", f"{s_user:.3f}"))
        if self.cbar is not None:
            self.cbar.remove()
            self.cbar = None
        self.ax.clear()
        self.ax.set_title("Зависимость CTI от тональности сообщений", fontsize=12)
        self.ax.set_xlabel("Тональность (от -1 негатив до +1 позитив)")
        self.ax.set_ylabel("CTI")
        self.ax.grid(True, alpha=0.25)
        self.ax.axvspan(-1.1, -0.05, facecolor='#FFCDD2', alpha=0.15)
        self.ax.axvspan( 0.05,  1.1, facecolor='#C8E6C9', alpha=0.15)
        cmap = plt.cm.RdYlGn
        norm = plt.Normalize(0, 100)
        sc_llm = self.ax.scatter(sentiments_llm, ctis, c=ctis, cmap=cmap, norm=norm,
                                 marker='o', s=100, edgecolors='#333333', linewidth=0.8,
                                 label='LLM sentiment')
        self.ax.scatter(sentiments_user, ctis, c=ctis, cmap=cmap, norm=norm,
                       marker='X', s=120, edgecolors='#333333', linewidth=0.8,
                       label='User sentiment')
        for idx, cti, s_llm, s_user in pairs:
            self.ax.annotate(str(idx), (s_llm, cti), textcoords="offset points",
                             xytext=(0, 10), ha='center', fontsize=8, color='#1E88E5')
            self.ax.annotate(str(idx), (s_user, cti), textcoords="offset points",
                             xytext=(0, -14), ha='center', fontsize=8, color='#D81B60')
        avg_cti = np.mean(ctis)
        self.ax.axhline(y=avg_cti, color='#555555', linestyle='--', alpha=0.7,
                        label=f'Средний CTI: {avg_cti:.1f}')
        self.cbar = self.fig.colorbar(sc_llm, ax=self.ax, fraction=0.035, pad=0.04)
        self.cbar.set_label('CTI', rotation=270, labelpad=15)
        self.ax.set_xlim(-1.1, 1.1)
        self.ax.set_ylim(0, 105)
        self.ax.legend(loc='upper right', fontsize='small')
        self.canvas.draw()