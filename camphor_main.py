import sys
from camphor import camphorapp
from PyQt4 import QtGui

app = QtGui.QApplication(sys.argv)
ex = camphorapp.camphor()
sys.exit(app.exec_())