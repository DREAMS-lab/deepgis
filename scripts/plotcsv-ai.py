import matplotlib.pyplot as plt
import csv
from sklearn.linear_model import LinearRegression
import numpy as np
from scipy import stats
x = []
y = []
x_AI = []
index = []

with open('/home/jdas/litter-area-vs-mass.csv','r') as csvfile:
    plots = csv.reader(csvfile, delimiter=',')
    for row in plots:
        x.append(float(row[2])*0.00541658112)
        x_AI.append(float(row[4])*0.02920440484)
        y.append(float(row[3]))
        index.append(str(row[0]))

vals = stats.linregress(x, y)
vals_AI = stats.linregress(x_AI, y)
rval_AI = vals_AI.rvalue
rval = vals.rvalue

r2_AI = rval_AI * rval_AI
r2 = rval * rval

x = np.asarray(x)
y= np.asarray(y)
x_AI = np.asarray(x_AI)

x = x.reshape(-1,1)
x_AI = x_AI.reshape(-1,1)

y = y.reshape(-1,1)

model = LinearRegression()
model.fit(y,x)

x_new = np.linspace(0, 110, 100)
y_new = model.predict(x_new[:, np.newaxis])


model2 = LinearRegression()
model2.fit(y,x_AI)

x_new_ai = np.linspace(0, 110, 100)
y_new_ai = model2.predict(x_new_ai[:, np.newaxis])


f = plt.figure(figsize=(4, 3))
ax = plt.axes()
ax.scatter(y, x,s=2)
ax.scatter(y,x_AI,s=1)

ax.plot(x_new,y_new,'blue', label='Human labeling')
ax.plot(x_new_ai,y_new_ai,'orange',label='AI labeling')
ax.axis('tight')

for i in range(0,len(index)):
    ax.text(y[i], x[i], index[i],fontsize=8)


ax.legend()

plt.xlabel('Mass (g)')
plt.ylabel('Area (cm sq.)')
title = "Litter mass vs area, R2 = %3.3f, R2_AI = %3.3f" %(r2, r2_AI)
plt.title(title)
plt.show()
f.savefig("/home/jdas/litter-area-vs-mass-AI.pdf", bbox_inches='tight')



