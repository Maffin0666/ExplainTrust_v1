# gui/psycho_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import numpy as np
from explaintrust import ExplainTrust
from .tonality_tab import simple_sentiment

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

class PsychoPortraitTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.engine = ExplainTrust()
        self.messages = []
        self._build_ui()

    def _build_ui(self):
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(ctrl, text="Готовые диалоги:", font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.dialog_combo = ttk.Combobox(ctrl, values=[d["name"] for d in BUILTIN_DIALOGS],
                                         state='readonly', width=30)
        self.dialog_combo.pack(side=tk.LEFT, padx=5)
        self.dialog_combo.bind('<<ComboboxSelected>>', self._on_select_example)

        ttk.Button(ctrl, text="Загрузить диалог (JSON)", command=self._load_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="Сформировать портрет", command=self._analyze).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="?", width=3, command=lambda: messagebox.showinfo(
            "Справка: Психопортрет",
            "Формирует текстовое описание типового поведения пользователя\n"
            "на основе средних значений признаков и тональности по всем парам диалога.\n"
            "Учитываются: уровень доверия, склонность к сомнениям,\n"
            "частота переспросов, длина ответов и эмоциональная окраска."
        )).pack(side=tk.LEFT, padx=5)

        self.status = ttk.Label(ctrl, text="Диалог не выбран")
        self.status.pack(side=tk.LEFT, padx=10)

        self.portrait_text = tk.Text(self, height=20, wrap='word', font=('Segoe UI', 10), bg='#fafafa')
        self.portrait_text.pack(fill=tk.BOTH, expand=True)

    def _on_select_example(self, event=None):
        name = self.dialog_combo.get()
        for d in BUILTIN_DIALOGS:
            if d["name"] == name:
                self.messages = d["messages"]
                self.status.config(text=f"Выбран: {name}")
                self._analyze()
                break

    def _load_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                self.messages = data
                self.status.config(text=f"Загружено {len(data)} сообщений")
                self._analyze()
            else:
                messagebox.showerror("Ошибка", "Ожидался массив сообщений")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _analyze(self):
        if not self.messages:
            messagebox.showwarning("Предупреждение", "Сначала загрузите или выберите диалог")
            return
        turns = []
        i = 0
        while i < len(self.messages) - 1:
            if self.messages[i]['role'] == 'llm' and self.messages[i+1]['role'] == 'user':
                llm = self.messages[i]['content']
                user = self.messages[i+1]['content']
                res = self.engine.evaluate({'llm_response': llm, 'user_reply': user})
                sent_llm = simple_sentiment(llm)
                sent_user = simple_sentiment(user)
                turns.append((res, sent_llm, sent_user))
                i += 2
            else:
                i += 1
        if not turns:
            messagebox.showinfo("Результат", "Нет полных пар LLM/User")
            return
        avg_cti = np.mean([t[0]['CTI'] for t in turns])
        avg_dm = np.mean([t[0]['DM'] for t in turns])
        avg_fq = np.mean([t[0]['FQ'] for t in turns])
        avg_rl = np.mean([t[0]['RL'] for t in turns])
        avg_sent_user = np.mean([t[2] for t in turns])
        if avg_cti >= 70:
            trust = "высокий"
        elif avg_cti >= 40:
            trust = "средний"
        else:
            trust = "низкий"
        if avg_dm > 0.1:
            doubt = "склонен к сомнениям"
        else:
            doubt = "уверенный"
        if avg_fq > 0.5:
            questions = "часто задаёт уточняющие вопросы"
        else:
            questions = "редко переспрашивает"
        if avg_rl > 0.6:
            length = "развёрнутые ответы (обсуждение)"
        elif avg_rl < 0.2:
            length = "короткие, односложные реакции"
        else:
            length = "лаконичные, но содержательные ответы"
        if avg_sent_user > 0.02:
            tone = "положительная"
        elif avg_sent_user < -0.02:
            tone = "отрицательная"
        else:
            tone = "нейтральная"
        portrait = (
            f"ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ ПОЛЬЗОВАТЕЛЯ\n"
            f"==================================\n"
            f"Средний CTI: {avg_cti:.2f} (уровень доверия: {trust})\n"
            f"Маркеры сомнения: {avg_dm:.3f} ({doubt})\n"
            f"Частота переспросов: {avg_fq:.2f} ({questions})\n"
            f"Длина ответов: {avg_rl:.3f} ({length})\n"
            f"Тональность ответов: {avg_sent_user:.3f} ({tone})\n\n"
            f"ВЫВОД: пользователь демонстрирует {trust} уровень доверия, "
            f"{doubt}, {questions}. Стиль общения: {length}. "
            f"Эмоциональная окраска сообщений: {tone}.\n"
        )
        self.portrait_text.delete("1.0", tk.END)
        self.portrait_text.insert("1.0", portrait)