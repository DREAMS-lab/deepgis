import matplotlib.pyplot as plt
import csv
from sklearn.linear_model import LinearRegression
import numpy as np
from scipy import stats
x = []
y = []
index = []

with open('/home/jdas/litter-area-vs-mass.csv','r') as csvfile:
    plots = csv.reader(csvfile, delimiter=',')
    for row in plots:
        x.append(float(row[2])*0.00541658112)
        y.append(float(row[3]))
        index.append(str(row[0]))

vals = stats.linregress(x, y)
rval = vals.rvalue
r2 = rval * rval

x = np.asarray(x)
y= np.asarray(y)
x = x.reshape(-1,1)
y = y.reshape(-1,1)

model = LinearRegression()
model.fit(x, y)

x_new = np.linspace(0, 6000, 100)
y_new = model.predict(x_new[:, np.newaxis])



f = plt.figure(figsize=(4, 3))
ax = plt.axes()
ax.scatter(x, y)
ax.plot(x_new, y_new,'k')
ax.axis('tight')

for i in range(0,len(index)):
    ax.text(x[i]-100, y[i]+3, index[i],fontsize=8)


plt.xlabel('Area (cm sq.)')
plt.ylabel('Mass (g)')
title = "Litter area vs mass, R2 = %3.3f" %(r2)
plt.title(title)
plt.show()
f.savefig("/home/jdas/litter-area-vs-mass.pdf", bbox_inches='tight')
f.savefig("/home/jdas/litter-area-vs-mass.png", bbox_inches='tight')



