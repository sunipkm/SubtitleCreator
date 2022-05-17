from PyQt5 import QtCore, QtGui, QtWidgets


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        self.m_w11 = QtWidgets.QWidget()
        self.m_w12 = QtWidgets.QWidget()
        self.m_w21 = QtWidgets.QWidget()
        self.m_w22 = QtWidgets.QWidget()

        lay = QtWidgets.QGridLayout(central_widget)

        for w, (r, c) in zip(
            (self.m_w11, self.m_w12, self.m_w21, self.m_w22),
            ((0, 0), (0, 1), (1, 0), (1, 1)),
        ):
            lay.addWidget(w, r, c)
        for c in range(2):
            lay.setColumnStretch(c, 1)
        for r in range(2):
            lay.setRowStretch(r, 1)

        lay = QtWidgets.QVBoxLayout(self.m_w11)
        lay.addWidget(QtWidgets.QTextEdit())

        lay = QtWidgets.QVBoxLayout(self.m_w12)
        lay.addWidget(QtWidgets.QTableWidget(4, 4))

        lay = QtWidgets.QVBoxLayout(self.m_w21)
        lay.addWidget(QtWidgets.QLineEdit())

        lay = QtWidgets.QVBoxLayout(self.m_w22)
        lay.addWidget(QtWidgets.QLabel("Text", alignment=QtCore.Qt.AlignCenter))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.resize(640, 480)
    w.show()
    sys.exit(app.exec_())