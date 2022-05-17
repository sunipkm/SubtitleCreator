import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QTextEdit, QSplitter, QStyleFactory, QFrame, QSizePolicy)

class Example(QWidget):
    def __init__(self):
        super(Example, self).__init__()
        self.initUI()
	
    def initUI(self):
	
        hbox = QHBoxLayout(self)
        
        topleft = QTextEdit()
        # topleft.setFrameShape(QFrame.StyledPanel)
        bottom = QFrame()
        bottom.setFrameShape(QFrame.StyledPanel)
        
        splitter1 = QSplitter(Qt.Horizontal)
        splitter1.setChildrenCollapsible(False)
        textedit = QTextEdit()
        textedit.setMinimumWidth(100)
        splitter1.addWidget(topleft)
        topleft.setMinimumWidth(100)
        splitter1.addWidget(textedit)
        splitter1.setSizes([100,200])
        splitter1.setMinimumHeight(200)
        splitter1.setStretchFactor(1, 1)

        splitter2 = QSplitter(Qt.Vertical)
        splitter2.addWidget(splitter1)
        bottom.setMinimumHeight(200)
        splitter2.setChildrenCollapsible(False)
        splitter2.addWidget(bottom)
        
        hbox.addWidget(splitter2)
        
        self.setLayout(hbox)
        QApplication.setStyle(QStyleFactory.create('Cleanlooks'))
        
        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle('QSplitter demo')
        self.show()

		
def main():
   app = QApplication(sys.argv)
   ex = Example()
   sys.exit(app.exec_())
	
if __name__ == '__main__':
   main()