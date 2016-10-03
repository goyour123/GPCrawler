import sys
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
from PyQt4 import QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


def calculateEma(price_list, period):
    ema_list = []
    for price in price_list:
        try:
            ema = ((price * 2) / (period+1)) + ((ema_list[-1] * (period-1)) / (period+1))
            ema_list.append(ema)
        except IndexError:
            ema_list.append(price)
    return ema_list


def calulateDif(ema_list0, ema_list1):
    dif_list = []
    for ema0, ema1 in zip(ema_list0, ema_list1):
        dif_list.append(ema0 - ema1)
    return dif_list


class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=7, height=4, dpi=110):
        self.fig = Figure(figsize=(width, height), dpi=dpi, linewidth=1)
        self.axes = self.fig.add_subplot(111)

        FigureCanvasQTAgg.__init__(self, self.fig)
        self.setParent(parent)

        FigureCanvasQTAgg.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        FigureCanvasQTAgg.updateGeometry(self)

        self.date_list, self.num_date_list, self.price_in_list, self.price_out_list = [], [], [], []
        self.update_data()

    def update_data(self):
        conn = sqlite3.connect('goldprice.sqlite')
        cur = conn.cursor()

        cur.execute('SELECT * FROM Gold ORDER BY Date ASC')
        all_fetch = cur.fetchall()

        for date, price_out, price_in in all_fetch:
            self.date_list.append(date)
            self.price_out_list.append(price_out)
            self.price_in_list.append(price_in)

        converted_dates = map(datetime.strptime, self.date_list, len(self.date_list) * ['%Y/%m/%d'])
        self.num_date_list = list(converted_dates)

    def calculate_start_date_index(self, interval):
        start_date = self.num_date_list[-1] + relativedelta(months=-interval)
        while True:
            if start_date in self.num_date_list:
                return self.num_date_list.index(start_date)
            start_date -= relativedelta(days=1)


class GoldPriceCanvas(MplCanvas):
    def __init__(self, *args, **kwargs):
        MplCanvas.__init__(self, *args, **kwargs)
        MplCanvas.setStatusTip(self, '銀行賣出價格')
        self.update_figure(1, 12)

    def update_figure(self, canvas_price_out, interval):
        start_date_index = self.calculate_start_date_index(interval)
        self.axes.cla()
        if canvas_price_out:
            self.axes.set_title('Selling Price')
            self.axes.plot(self.num_date_list[start_date_index:], self.price_out_list[start_date_index:], 'r',
                           color='#B99A1D', picker=1)
            self.axes.patch.set_facecolor('#E3F0FD')
            self.fig.set_facecolor('#CBD7E6')
        else:
            self.axes.set_title('Buying Price')
            self.axes.plot(self.num_date_list[start_date_index:], self.price_in_list[start_date_index:], 'r',
                           color='#FF53D5', picker=1)
            self.axes.patch.set_facecolor('#FFECFF')
            self.fig.set_facecolor('#FFC8FF')
        self.draw()


class TechnicalAnalysisCanvas(MplCanvas):
    def __init__(self, *args, **kwargs):
        MplCanvas.__init__(self, *args, **kwargs)
        MplCanvas.setStatusTip(self, '技術分析線圖')
        self.po_diff_list, self.pi_diff_list = [], []
        self.po_dem_list, self.pi_dem_list = [], []
        self.po_macd_list, self.pi_macd_list = [], []
        self.technical_analysis_init()
        self.update_figure(1, 12)

    def update_figure(self, canvas_price_out, month_interval):
        start_date_index = self.calculate_start_date_index(month_interval)
        self.axes.cla()
        if canvas_price_out:
            self.axes.plot(self.num_date_list[start_date_index:], self.po_diff_list[start_date_index:], 'r', label='dif')
            self.axes.plot(self.num_date_list[start_date_index:], self.po_dem_list[start_date_index:], 'b', label='ema')
            self.axes.bar(self.num_date_list[start_date_index:], self.po_macd_list[start_date_index:],
                          color='g', edgecolor='g')
        else:
            self.axes.plot(self.num_date_list[start_date_index:], self.pi_diff_list[start_date_index:], 'r', label='dif')
            self.axes.plot(self.num_date_list[start_date_index:], self.pi_dem_list[start_date_index:], 'b', label='ema')
            self.axes.bar(self.num_date_list[start_date_index:], self.pi_macd_list[start_date_index:],
                          color='g', edgecolor='g')
        self.axes.legend(bbox_to_anchor=(1.1, 1.05))
        self.draw()

    def technical_analysis_init(self):
        po_ema12_list = calculateEma(self.price_out_list, 12)
        po_ema26_list = calculateEma(self.price_out_list, 26)
        self.po_diff_list = calulateDif(po_ema12_list, po_ema26_list)
        self.po_dem_list = calculateEma(self.po_diff_list, 9)

        pi_ema12_list = calculateEma(self.price_in_list, 12)
        pi_ema26_list = calculateEma(self.price_in_list, 26)
        self.pi_diff_list = calulateDif(pi_ema12_list, pi_ema26_list)
        self.pi_dem_list = calculateEma(self.pi_diff_list, 9)

        self.po_macd_list = calulateDif(self.po_diff_list, self.po_dem_list)
        self.pi_macd_list = calulateDif(self.pi_diff_list, self.pi_dem_list)


class AppWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.init_ui()

        self.main_widget = QtGui.QWidget(self)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self.layout = QtGui.QVBoxLayout(self.main_widget)
        self.price_canvas = 1
        self.canvas_interval = 12
        self.gold_price_canvas = GoldPriceCanvas(self.main_widget)
        self.technical_analyze_canvas = TechnicalAnalysisCanvas(self.main_widget)
        self.layout.addWidget(self.gold_price_canvas)
        self.layout.addWidget(self.technical_analyze_canvas)

        priceInAction = QtGui.QAction('&銀行買入', self)
        priceInAction.setStatusTip("更改顯示的價格為銀行買入價格")
        priceInAction.triggered.connect(self.change_canvas_price_in)

        priceOutAction = QtGui.QAction('&銀行賣出', self)
        priceOutAction.setStatusTip("更改顯示的價格為銀行賣出價格")
        priceOutAction.triggered.connect(self.change_canvas_price_out)

        intervalAction3 = QtGui.QAction('&最近3個月', self)
        intervalAction3.setStatusTip("更改顯示期間為最近的3個月")
        intervalAction3.triggered.connect(self.update_figure_interval3)

        intervalAction6 = QtGui.QAction('&最近6個月', self)
        intervalAction6.setStatusTip("更改顯示期間為最近的6個月")
        intervalAction6.triggered.connect(self.update_figure_interval6)

        intervalAction12 = QtGui.QAction('&最近1年', self)
        intervalAction12.setStatusTip("更改顯示期間為最近的1年")
        intervalAction12.triggered.connect(self.update_figure_interval12)

        self.statusBar()

        mainMenu = self.menuBar()

        priceMenu = mainMenu.addMenu('&價格顯示')
        priceMenu.addAction(priceInAction)
        priceMenu.addAction(priceOutAction)

        settingMenu = mainMenu.addMenu('&顯示期間')
        settingMenu.addAction(intervalAction3)
        settingMenu.addAction(intervalAction6)
        settingMenu.addAction(intervalAction12)

    def init_ui(self):
        self.setWindowTitle("Gold Price Analyzer")
        self.setWindowIcon(QtGui.QIcon('png/gold.png'))

    def update_figure_interval3(self):
        self.canvas_interval = 3
        self.gold_price_canvas.update_figure(self.price_canvas, self.canvas_interval)
        self.technical_analyze_canvas.update_figure(self.price_canvas, self.canvas_interval)

    def update_figure_interval6(self):
        self.canvas_interval = 6
        self.gold_price_canvas.update_figure(self.price_canvas, self.canvas_interval)
        self.technical_analyze_canvas.update_figure(self.price_canvas, self.canvas_interval)

    def update_figure_interval12(self):
        self.canvas_interval = 12
        self.gold_price_canvas.update_figure(self.price_canvas, self.canvas_interval)
        self.technical_analyze_canvas.update_figure(self.price_canvas, self.canvas_interval)

    def change_canvas_price_in(self):
        self.price_canvas = 0
        self.gold_price_canvas.setStatusTip('銀行買入價格')
        self.gold_price_canvas.update_figure(self.price_canvas, self.canvas_interval)
        self.technical_analyze_canvas.update_figure(self.price_canvas, self.canvas_interval)

    def change_canvas_price_out(self):
        self.price_canvas = 1
        self.gold_price_canvas.setStatusTip('銀行賣出價格')
        self.gold_price_canvas.update_figure(self.price_canvas, self.canvas_interval)
        self.technical_analyze_canvas.update_figure(self.price_canvas, self.canvas_interval)


def main():
    app = QtGui.QApplication(sys.argv)
    app_window = AppWindow()
    app_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
