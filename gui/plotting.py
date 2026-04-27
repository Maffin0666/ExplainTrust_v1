# gui/plotting.py

import matplotlib.pyplot as plt
import numpy as np
import skfuzzy as fuzz


def draw_trust_membership(ax, cti_value=None):
    """Рисует функции принадлежности CTI и опционально вертикальную линию."""
    ax.clear()
    ax.set_title("Функции принадлежности CTI", fontsize=11)
    ax.set_xlabel("CTI")
    ax.set_ylabel("Принадлежность")
    ax.grid(True, alpha=0.3)
    x = np.arange(0, 101, 1)
    ax.plot(x, fuzz.trapmf(x, [0, 0, 15, 25]), '#D32F2F', label='Очень низкое')
    ax.plot(x, fuzz.trimf(x, [15, 30, 45]), '#F57C00', label='Низкое')
    ax.plot(x, fuzz.trimf(x, [35, 50, 65]), '#FBC02D', label='Среднее')
    ax.plot(x, fuzz.trimf(x, [55, 70, 85]), '#388E3C', label='Высокое')
    ax.plot(x, fuzz.trapmf(x, [75, 85, 100, 100]), '#1976D2', label='Очень высокое')
    if cti_value is not None:
        ax.axvline(cti_value, color='black', linewidth=2, linestyle='--',
                   label=f'CTI = {cti_value:.2f}')
    ax.legend(loc='upper left', fontsize='small')


def draw_dialog_dynamics(ax, x, y, avg=None):
    """Рисует график динамики CTI с зонами уровней доверия."""
    ax.clear()
    ax.set_title("Динамика когнитивного доверия", fontsize=12, pad=12)
    ax.set_xlabel("Номер пары (ход)")
    ax.set_ylabel("CTI")
    ax.grid(True, alpha=0.3)
    # Цветовые зоны
    ax.axhspan(0, 15, facecolor='#FFCDD2', alpha=0.2)    # очень низкое
    ax.axhspan(15, 35, facecolor='#FFE0B2', alpha=0.2)   # низкое
    ax.axhspan(35, 55, facecolor='#FFF9C4', alpha=0.2)   # среднее
    ax.axhspan(55, 75, facecolor='#C8E6C9', alpha=0.2)   # высокое
    ax.axhspan(75, 100, facecolor='#BBDEFB', alpha=0.2)  # очень высокое
    if x and y:
        ax.plot(x, y, 'o-', color='#1E88E5', linewidth=2, markersize=7, label='CTI')
        ax.set_xticks(x)
        ax.set_ylim(0, 105)
        if avg is not None:
            ax.axhline(avg, color='#D32F2F', linewidth=2, linestyle='--',
                       label=f'Средний = {avg:.2f}')
    else:
        ax.set_ylim(0, 105)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc='upper right', fontsize='medium')