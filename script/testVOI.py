import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

c1 = {'red':((0,0,0),(0.5,1,1),(1,1,1)),
      'green': ((0,0,0),(0.5,0,0),(1,0,0)),
      'blue': ((0,0,0),(0.5,1,1),(1,1,1))}

c2 = {'red':((0,0,0),(0.5,0,0),(1,0,0)),
      'green': ((0,0,0),(0.5,1,1),(1,1,1)),
      'blue': ((0,0,0),(0.5,0,0),(1,0,0))}

c1a = {'red':((0,0,0),(1,1,1)), 'green': ((0,0,0),(1,0,0)), 'blue': ((0,0,0),(1,1,1)), 'alpha': ((0,0,0),(0.1,0.5,0.5), (1,1,1))}
c2a = {'red':((0,0,0),(1,0,0)), 'green': ((0,0,0),(1,1,1)), 'blue': ((0,0,0),(1,0,0)), 'alpha': ((0,0,0),(0.1,0.5,0.5), (1,1,1))}


plt.register_cmap(name='magenta',data=c1)
plt.register_cmap(name='green',data=c2)

plt.register_cmap(name='magentaA',data=c1a)
plt.register_cmap(name='greenA',data=c2a)

nplt = len(self.pltdata1)
d1 = [d/np.mean(d[0:2])-1 for d in self.pltdata1]
d2 = [d/np.mean(d[0:2])-1 for d in self.pltdata2]
t = np.add(range(len(self.pltdata1[0])),1)

sp0 = np.ceil(np.sqrt(nplt)).astype(np.int)

fig = plt.figure()
for i in range(nplt):
    plt.hold(False)
    plt.subplot(sp0,sp0,i+1)
    plt.plot(t,d1[i],linewidth=2.0, color='magenta')
    plt.hold(True)
    plt.plot(t, d2[i],linewidth=2.0, color='green')
    plt.ylim(-1,3)
    if i==0:
        plt.ylabel('$\Delta F/F$')
    if i==1:
        plt.xlabel('Imaging frame')
fig.tight_layout()

d1 = self.vtkView.tdata
d2 = self.vtkView2.tdata
fig2 = plt.figure()
ind = [0,4]
for i in range(2):
    zo = np.zeros([25,30,3])
    zo[:,:,0] = d1[ind[i]][22,85:110,30:60]
    zo[:,:,1] = d2[ind[i]][22,85:110,30:60]
    zo[:,:,2] = d1[ind[i]][22,85:110,30:60]

    z1 = np.zeros([25,30,3])
    z1[:,:,0] = d1[ind[i]][22,85:110,30:60]
    z1[:,:,2] = d1[ind[i]][22,85:110,30:60]

    z2 = np.zeros([25,30,3])
    z2[:,:,1] = d2[ind[i]][22,85:110,30:60]

    plt.subplot('23' + str(i*3+1))
    plt.tick_params(axis='both',which='both',bottom='off',top='off',labelbottom='off',left='off',right='off',labelleft='off')
    plt.imshow(z1/255)
    if i==0:
        plt.ylabel('Baseline')
        plt.title('Odor 1')
    else:
        plt.ylabel('Odor')
    plt.subplot('23' + str(i * 3 + 2))
    plt.tick_params(axis='both', which='both', bottom='off', top='off', labelbottom='off',left='off',right='off',labelleft='off')
    plt.imshow(z2/255)
    if i==0:
        plt.title('Odor 2')
    plt.subplot('23' + str(i*3+3))
    plt.tick_params(axis='both', which='both', bottom='off', top='off', labelbottom='off',left='off',right='off',labelleft='off')
    plt.imshow(zo/255)
    if i==0:
        plt.title('Merge')

fig2.tight_layout()
