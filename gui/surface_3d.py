# gui/surface_3d.py

import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import cm
from explaintrust import fuzzy_engine
from skfuzzy import control as ctrl

class Surface3DTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.cbar = None
        self._build_ui()
        self._update_surface()

    def _build_ui(self):
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, pady=(0,5))

        ttk.Label(ctrl_frame, text="Фиксированные параметры:").pack(side=tk.LEFT, padx=5)

        self.cm_var = tk.DoubleVar(value=0.06)
        self.ld_var = tk.DoubleVar(value=0.6)
        self.fq_var = tk.DoubleVar(value=0)
        self.rl_var = tk.DoubleVar(value=0.3)

        for name, var, frm, to in [("CM:", self.cm_var, 0, 0.15),
                                   ("LD:", self.ld_var, 0, 1),
                                   ("FQ:", self.fq_var, 0, 1),
                                   ("RL:", self.rl_var, 0, 1)]:
            ttk.Label(ctrl_frame, text=name).pack(side=tk.LEFT)
            ttk.Scale(ctrl_frame, from_=frm, to=to, variable=var, orient=tk.HORIZONTAL,
                      length=80).pack(side=tk.LEFT, padx=2)

        ttk.Button(ctrl_frame, text="Обновить", command=self._update_surface).pack(side=tk.LEFT, padx=10)

        self.fig = plt.figure(figsize=(8,6))
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _update_surface(self, event=None):
        # Удаляем старый colorbar, если он был
        if self.cbar is not None:
            self.cbar.remove()
            self.cbar = None

        self.ax.cla()   # очистка оси

        si_vals = np.linspace(0, 1, 20)
        dm_vals = np.linspace(0, 1, 20)
        SI, DM = np.meshgrid(si_vals, dm_vals)
        CTI = np.zeros_like(SI)

        system, _ = fuzzy_engine.build_system()

        cm_val = self.cm_var.get()
        ld_val = self.ld_var.get()
        fq_val = self.fq_var.get()
        rl_val = self.rl_var.get()

        for i in range(len(si_vals)):
            for j in range(len(dm_vals)):
                sim = ctrl.ControlSystemSimulation(system)
                sim.input['SI'] = SI[i,j]
                sim.input['CM'] = cm_val
                sim.input['LD'] = ld_val
                sim.input['DM'] = DM[i,j]
                sim.input['FQ'] = fq_val
                sim.input['RL'] = rl_val
                sim.compute()
                # Используем безопасное извлечение с значением по умолчанию 0.0
                CTI[i,j] = sim.output.get('CTI', 0.0)

        surf = self.ax.plot_surface(SI, DM, CTI, cmap=cm.coolwarm,
                                    linewidth=0, antialiased=True, alpha=0.9)
        self.ax.set_xlabel('SI (Структурная целостность)')
        self.ax.set_ylabel('DM (Маркеры сомнения)')
        self.ax.set_zlabel('CTI')
        self.ax.set_title('3D‑поверхность CTI(SI, DM)')

        # Новый colorbar
        self.cbar = self.fig.colorbar(surf, ax=self.ax, shrink=0.5, aspect=10)
        self.canvas.draw()