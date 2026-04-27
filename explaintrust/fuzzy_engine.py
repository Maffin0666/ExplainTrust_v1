# explaintrust/fuzzy_engine.py

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

def build_system():
    # Диапазоны переменных
    SI = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'SI')
    CM = ctrl.Antecedent(np.arange(0, 0.151, 0.001), 'CM')
    LD = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'LD')
    DM = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'DM')
    FQ = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'FQ')
    RL = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'RL')
    CTI = ctrl.Consequent(np.arange(0, 101, 1), 'CTI')

    # SI
    SI['низкая'] = fuzz.trapmf(SI.universe, [0, 0, 0.3, 0.4])
    SI['средняя'] = fuzz.trimf(SI.universe, [0.3, 0.5, 0.7])
    SI['высокая'] = fuzz.trapmf(SI.universe, [0.6, 0.7, 1, 1])

    # CM
    CM['низкая'] = fuzz.trapmf(CM.universe, [0, 0, 0.03, 0.05])
    CM['средняя'] = fuzz.trimf(CM.universe, [0.03, 0.07, 0.10])
    CM['высокая'] = fuzz.trapmf(CM.universe, [0.08, 0.10, 0.15, 0.15])

    # LD
    LD['низкое'] = fuzz.trapmf(LD.universe, [0, 0, 0.4, 0.5])
    LD['среднее'] = fuzz.trimf(LD.universe, [0.4, 0.6, 0.8])
    LD['высокое'] = fuzz.trapmf(LD.universe, [0.7, 0.8, 1, 1])

    # DM
    DM['отсутствуют'] = fuzz.trapmf(DM.universe, [0, 0, 0.02, 0.05])
    DM['единичные'] = fuzz.trimf(DM.universe, [0.02, 0.08, 0.15])
    DM['частые'] = fuzz.trapmf(DM.universe, [0.10, 0.15, 1, 1])

    # FQ
    FQ['нет'] = fuzz.trapmf(FQ.universe, [0, 0, 0, 0.5])
    FQ['есть'] = fuzz.trapmf(FQ.universe, [0.5, 1, 1, 1])

    # RL
    RL['короткий'] = fuzz.trapmf(RL.universe, [0, 0, 0.2, 0.4])
    RL['средний'] = fuzz.trimf(RL.universe, [0.2, 0.5, 0.8])
    RL['длинный'] = fuzz.trapmf(RL.universe, [0.6, 0.8, 1, 1])

    # CTI
    CTI['очень низкое'] = fuzz.trapmf(CTI.universe, [0, 0, 15, 25])
    CTI['низкое'] = fuzz.trimf(CTI.universe, [15, 30, 45])
    CTI['среднее'] = fuzz.trimf(CTI.universe, [35, 50, 65])
    CTI['высокое'] = fuzz.trimf(CTI.universe, [55, 70, 85])
    CTI['очень высокое'] = fuzz.trapmf(CTI.universe, [75, 85, 100, 100])

    rules = []
    rules.append(ctrl.Rule(SI['высокая'] & CM['высокая'] & LD['высокое'] &
                           DM['отсутствуют'] & FQ['нет'] & RL['средний'],
                           CTI['очень высокое']))
    rules.append(ctrl.Rule(SI['низкая'] & CM['низкая'] & DM['частые'] & FQ['есть'],
                           CTI['очень низкое']))
    rules.append(ctrl.Rule(SI['средняя'] & DM['единичные'] & FQ['нет'],
                           CTI['среднее']))
    rules.append(ctrl.Rule(FQ['есть'] & RL['длинный'], CTI['низкое']))
    rules.append(ctrl.Rule(DM['отсутствуют'] & FQ['нет'] & RL['короткий'], CTI['высокое']))
    rules.append(ctrl.Rule(LD['низкое'] & CM['низкая'] & DM['отсутствуют'], CTI['среднее']))
    rules.append(ctrl.Rule(SI['высокая'] & DM['единичные'], CTI['высокое']))
    rules.append(ctrl.Rule(DM['частые'] & FQ['есть'], CTI['очень низкое']))
    rules.append(ctrl.Rule(FQ['нет'] & RL['средний'] & DM['единичные'], CTI['среднее']))
    rules.append(ctrl.Rule(RL['короткий'] & DM['частые'], CTI['низкое']))
    rules.append(ctrl.Rule(RL['длинный'] & FQ['нет'] & DM['единичные'], CTI['среднее']))
    rules.append(ctrl.Rule(LD['высокое'] & CM['высокая'] & FQ['нет'] & DM['отсутствуют'],
                           CTI['высокое']))

    system = ctrl.ControlSystem(rules)
    sim = ctrl.ControlSystemSimulation(system)
    return system, sim