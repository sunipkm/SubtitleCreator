import random
import sys

from PyQt5 import QtWidgets


class Delegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.data() == "NN":
            return super(Delegate, self).createEditor(parent, option, index)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    texts = ["Hello", "Stack", "Overflow", "NN"]

    table = QtWidgets.QTableWidget(10, 5)
    delegate = Delegate(table)
    table.setItemDelegate(delegate)

    for i in range(table.rowCount()):
        for j in range(table.columnCount()):
            text = random.choice(texts)
            it = QtWidgets.QTableWidgetItem(text)
            table.setItem(i, j, it)

    table.resize(640, 480)
    table.show()
    sys.exit(app.exec_())