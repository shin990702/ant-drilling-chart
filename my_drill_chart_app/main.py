import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from chart_widget import ChartWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChartWindow()
    window.show()
    sys.exit(app.exec_())
