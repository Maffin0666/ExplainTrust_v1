# explaintrust/__init__.py

from .feature_extraction import compute_external_features, compute_internal_features
from .fuzzy_engine import build_system
from skfuzzy import control as ctrl


class ExplainTrust:
    """
    Нечеткая экспертная система оценки когнитивного доверия пользователя
    к ответу большой языковой модели.
    """
    def __init__(self):
        self.system, _ = build_system()

    def evaluate(self, dialog_pair: dict) -> dict:
        """
        Вычисляет CTI для одной пары (LLM-ответ + реакция пользователя).
        dialog_pair: {'llm_response': ..., 'user_reply': ...}
        """
        return self._compute(dialog_pair['llm_response'], dialog_pair['user_reply'])

    def evaluate_dialog_turns(self, messages: list) -> list:
        """
        Обрабатывает целый диалог – список сообщений.
        Каждое сообщение: {'role': 'llm'|'user', 'content': '...'}
        Образуются пары: (LLM_i, user_i) – ответ модели и следующая за ним реакция пользователя.
        Возвращает список словарей с результатами для каждой пары.
        """
        turns = []
        i = 0
        while i < len(messages) - 1:
            if messages[i]['role'] == 'llm' and messages[i+1]['role'] == 'user':
                res = self._compute(messages[i]['content'], messages[i+1]['content'])
                turns.append(res)
                i += 2
            else:
                # Пропускаем одиночные сообщения без пары
                i += 1
        return turns

    def _compute(self, llm_text: str, user_text: str) -> dict:
        """Внутренний метод для расчёта CTI по паре текстов."""
        ext = compute_external_features(llm_text)
        intf = compute_internal_features(user_text)

        sim = ctrl.ControlSystemSimulation(self.system)
        sim.input['SI'] = ext['SI']
        sim.input['CM'] = ext['CM']
        sim.input['LD'] = ext['LD']
        sim.input['DM'] = intf['DM']
        sim.input['FQ'] = intf['FQ']
        sim.input['RL'] = intf['RL']
        sim.compute()

        cti = sim.output.get('CTI', 0.0)

        if cti >= 75:
            level = 'очень высокое'
        elif cti >= 55:
            level = 'высокое'
        elif cti >= 35:
            level = 'среднее'
        elif cti >= 15:
            level = 'низкое'
        else:
            level = 'очень низкое'

        return {
            'CTI': round(cti, 2),
            'trust_level': level,
            'SI': ext['SI'],
            'CM': ext['CM'],
            'LD': ext['LD'],
            'DM': intf['DM'],
            'FQ': intf['FQ'],
            'RL': intf['RL']
        }