from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
import time


app= QApplication([])
view= QWebView()
view.setGeometry(100,150,1280,550)
url="http://192.168.2.176"
view.setWindowTitle("Browser "+url)
view.load(QUrl(url))
view.show()
view.hide()
app.exec_()