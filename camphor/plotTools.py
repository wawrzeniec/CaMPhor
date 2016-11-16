import matplotlib.pyplot as plt

def plotData(x):
    fig = plt.figure()
    for d in x:
        plt.plot(d)
    plt.show()
    return fig