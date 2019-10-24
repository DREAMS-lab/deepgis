import matplotlib.pyplot as plt
import csv
from sklearn.linear_model import LinearRegression
import numpy as np
from scipy import stats

x = []
y = []
x_AI = []
index = []

with open('/home/jdas/litter-area-vs-mass.csv', 'r') as csvfile:
    plots = csv.reader(csvfile, delimiter=',')
    for row in plots:
        human_area = float(row[2]) * 0.00541658112
        x.append(human_area)
        AI_area = float(row[4]) * 0.03358506556
        x_AI.append(AI_area)
        mass = float(row[3])
        y.append(mass)
        ind = str(row[0])
        index.append(ind)
        print(ind, mass, human_area, AI_area, sep=", ")

# f = plt.figure(figsize=(4, 3))
#
#
# def fit_line(_x, _y, ax, _marker_size, _plot_color, _plot_label):
#     _x = np.asarray(_x)
#     _y = np.asarray(_y)
#     vals = stats.linregress(_x,_y)
#     rval = vals.rvalue
#     _r2 = rval * rval
#     _x = _x.reshape(-1, 1)
#     _y = _y.reshape(-1, 1)
#     model = LinearRegression()
#     model.fit(_y, _x)
#
#     _x_new = np.linspace(0, 110, 100)
#     _y_new = model.predict(_x_new[:, np.newaxis])
#
#     ax.scatter(_y, _x, s=_marker_size)
#     ax.plot(_x_new, _y_new, _plot_color, label=_plot_label)
#     ax.axis('tight')
#     return _r2, _x_new, _y_new, ax
#
#
# ax = plt.axes()
#
# r2, x_new, y_new, ax = fit_line(x, y, ax,2,'blue','Human labeling')
# r2_AI, x_new_AI, y_new_AI, ax = fit_line(x_AI, y, ax,2,'orange','AI labeling')
#
# for i in range(0, len(index)):
#     ax.text(y[i], x[i], index[i], fontsize=8)
# ax.legend()
#
# plt.xlabel('Mass (g)')
# plt.ylabel('Area (cm sq.)')
# title = "Litter mass vs area, R2 = %3.3f, R2_AI = %3.3f" % (r2, r2_AI)
# plt.title(title, fontsize=10)
# plt.show()
# f.savefig("/home/jdas/litter-area-vs-mass-AI.pdf", bbox_inches='tight')
