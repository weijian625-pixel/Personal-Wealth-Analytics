import sys
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QPushButton, QInputDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle

from engine import AssetEngine

class AssetPieChart(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 4), dpi=100, facecolor='#252b36')
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

    def update_chart(self, data):
        self.ax.clear()
        self.ax.axis('off')

        labels = [key for key in data.keys() if key != "TOTAL_WEALTH"]
        values = []
        for key in labels:
            try: values.append(max(0.0, float(data[key])))
            except: values.append(0.0)

        if sum(values) <= 0:
            self.ax.text(0.5, 0.5, "Waiting for Asset Data...", ha='center', va='center', color='#7f8c8d', fontsize=12, weight='bold')
            self.draw_idle()
            return

        colors = ['#3498db', '#f1c40f', '#f39c12', '#2ecc71', '#e67e22']
        wedges, texts, autotexts = self.ax.pie(
            values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors,
            textprops=dict(color="#ffffff", fontsize=11, weight='bold'), pctdistance=0.75
        )
        centre_circle = Circle((0,0), 0.55, fc='#252b36')
        self.ax.add_artist(centre_circle)
        for autotext in autotexts:
            autotext.set_color('#ffffff')
            autotext.set_weight('bold')

        self.ax.axis('equal')
        self.fig.subplots_adjust(left=0.15, right=0.85, top=0.85, bottom=0.15)
        self.draw_idle()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Billionaire's Core5 Permanent Investment Dashboard")
        self.resize(1250, 680)

        self.engine = AssetEngine()
        self.current_cash_inflow = 0.0 
        self.latest_rebalance_report = {}
        
        self.init_ui()
        self.apply_dark_theme()
        self.refresh_data()

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setObjectName("MainWidget")
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(20)

        top_card = QWidget()
        top_card.setObjectName("TopCard")
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(25, 20, 25, 20)
        
        self.wealth_title = QLabel("CORE 5 PORTFOLIO | CASH RESERVOIR CLOSED ECOLOGY")
        self.wealth_title.setObjectName("WealthTitle")
        
        self.wealth_value = QLabel("RM 0.00")
        self.wealth_value.setObjectName("WealthValue")
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.refresh_btn = QPushButton("🔄 Refresh Market Data")
        self.refresh_btn.setObjectName("RefreshBtn")
        self.refresh_btn.clicked.connect(self.refresh_data)

        self.edit_btn = QPushButton("✏️ Adjust Holdings")
        self.edit_btn.setObjectName("EditBtn")
        self.edit_btn.clicked.connect(self.edit_asset_dialog)

        self.invest_btn = QPushButton("💵 Plan New Capital")
        self.invest_btn.setObjectName("InvestBtn")
        self.invest_btn.clicked.connect(self.plan_investment_dialog)

        self.buy_stock_btn = QPushButton("🛒 Convert Reservoir Cash")
        self.buy_stock_btn.setObjectName("BuyStockBtn")
        self.buy_stock_btn.clicked.connect(self.execute_pool_conversion)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.invest_btn)
        btn_layout.addWidget(self.buy_stock_btn)
        btn_layout.addStretch()

        top_layout.addWidget(self.wealth_title)
        top_layout.addWidget(self.wealth_value)
        top_layout.addLayout(btn_layout)
        main_layout.addWidget(top_card)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        table_card = QWidget()
        table_card.setObjectName("TableCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)
        
        self.table_label = QLabel("📊 Asset Breakdown & Smart Rebalancing Recommendations")
        self.table_label.setStyleSheet("color: #ecf0f1; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        table_layout.addWidget(self.table_label)

        self.table = QTableWidget()
        self.table.setColumnCount(4) 
        self.table.setHorizontalHeaderLabels(["Asset", "Total Value (Inc. Reservoir)", "Current Weight", "Dynamic Recommendation"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.table)
        
        bottom_layout.addWidget(table_card, stretch=4)

        chart_card = QWidget()
        chart_card.setObjectName("ChartCard")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(15, 15, 15, 15)
        
        chart_label = QLabel("🎯 Real-Time Weight Allocation")
        chart_label.setStyleSheet("color: #ecf0f1; font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        chart_layout.addWidget(chart_label)
        
        self.chart_canvas = AssetPieChart(self)
        chart_layout.addWidget(self.chart_canvas)
        
        bottom_layout.addWidget(chart_card, stretch=2)
        main_layout.addLayout(bottom_layout)

    def apply_dark_theme(self):
        dark_stylesheet = """
            QWidget#MainWidget { background-color: #1e222b; }
            QWidget#TopCard { background-color: #252b36; border-radius: 12px; }
            QWidget#TableCard, QWidget#ChartCard { background-color: #252b36; border-radius: 12px; }
            QLabel#WealthTitle { color: #95a5a6; font-size: 13px; font-weight: bold; letter-spacing: 1px; }
            QLabel#WealthValue { color: #2ecc71; font-size: 38px; font-weight: bold; font-family: 'Segoe UI', Arial, sans-serif; margin-top: 5px; margin-bottom: 10px; }
            QPushButton#RefreshBtn { background-color: #3498db; color: white; border: none; padding: 8px 18px; font-size: 12px; font-weight: bold; border-radius: 6px; }
            QPushButton#RefreshBtn:hover { background-color: #2980b9; }
            QPushButton#RefreshBtn:disabled { background-color: #7f8c8d; }
            QPushButton#EditBtn { background-color: #4b5563; color: white; border: none; padding: 8px 18px; font-size: 12px; font-weight: bold; border-radius: 6px; }
            QPushButton#EditBtn:hover { background-color: #374151; }
            QPushButton#InvestBtn { background-color: #2ecc71; color: white; border: none; padding: 8px 18px; font-size: 12px; font-weight: bold; border-radius: 6px; }
            QPushButton#InvestBtn:hover { background-color: #27ae60; }
            QPushButton#BuyStockBtn { background-color: #e67e22; color: white; border: none; padding: 8px 18px; font-size: 12px; font-weight: bold; border-radius: 6px; }
            QPushButton#BuyStockBtn:hover { background-color: #d35400; }
            QTableWidget { background-color: #252b36; border: none; color: #ecf0f1; font-size: 13px; }
            QTableWidget::item { padding: 12px; border-bottom: 1px solid #2d3545; }
            QTableWidget::item:selected { background-color: #2d3545; color: #2ecc71; }
            QHeaderView::section { background-color: #252b36; color: #7f8c8d; padding: 8px; font-weight: bold; border: none; border-bottom: 2px solid #3498db; }
        """
        self.setStyleSheet(dark_stylesheet)

    def refresh_data(self):
        self.refresh_btn.setText("Fetching market quotes...")
        self.refresh_btn.setEnabled(False)
        QApplication.processEvents()

        result = self.engine.calculate_portfolio()
        total_wealth = 0.0
        assets_keys = [key for key in result.keys() if key != "TOTAL_WEALTH"]
        for name in assets_keys: total_wealth += result[name]

        self.wealth_value.setText(f"RM {total_wealth:,.2f}")
        self.latest_rebalance_report = self.engine.calculate_rebalancing(result, self.current_cash_inflow)
        self.chart_canvas.update_chart(result)

        mb_info = self.engine.data["assets"]["Maybank"]
        current_pool = mb_info.get("cash_pool", 0.0)

        if self.current_cash_inflow > 0:
            self.table_label.setText(f"📊 Planned Inflow: RM {self.current_cash_inflow:,.2f} | Reservoir Balance: RM {current_pool:,.2f}")
            self.table.setHorizontalHeaderLabels(["Asset", "Total Value (Inc. Pool)", "Current Weight", "Allocation Advice"])
        else:
            self.table_label.setText(f"📊 Portfolio Breakdown | Maybank Reservoir Cash: RM {current_pool:,.2f}")
            self.table.setHorizontalHeaderLabels(["Asset", "Total Value (Inc. Pool)", "Current Weight", "Target Deviation"])

        self.table.setRowCount(len(assets_keys))
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignVCenter)
        for c in range(4):
            align = Qt.AlignmentFlag.AlignCenter if c == 0 else (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.model().setHeaderData(c, Qt.Orientation.Horizontal, align, Qt.ItemDataRole.TextAlignmentRole)

        one_lot_cost = 100 * self.engine.maybank_price

        for row, name in enumerate(assets_keys):
            value = result[name]
            asset_info = self.latest_rebalance_report[name]
            percentage = asset_info["actual_pct"]
            suggested = asset_info["suggested_investment"]

            item_name = QTableWidgetItem(name)
            item_name.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_value = QTableWidgetItem(f"RM {value:,.2f}  ")
            item_value.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_pct = QTableWidgetItem(f"{percentage:.1f}%  ")
            item_pct.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            if self.current_cash_inflow > 0:
                if name == "Maybank":
                    total_available_pool = current_pool + suggested
                    if total_available_pool >= one_lot_cost:
                        lots = int(total_available_pool // one_lot_cost)
                        item_suggest = QTableWidgetItem(f"🛒 Ready! Buy {lots} Lot(s) (Allocate RM {suggested:,.2f})  ")
                        item_suggest.setForeground(QColor('#2ecc71'))
                    else:
                        shortfall = one_lot_cost - total_available_pool
                        item_suggest = QTableWidgetItem(f"⏳ Route to Pool +RM {suggested:,.2f} (Need RM {shortfall:.2f})  ")
                        item_suggest.setForeground(QColor('#f39c12'))
                else:
                    if suggested > 0:
                        item_suggest = QTableWidgetItem(f"🎯 Invest +RM {suggested:,.2f}  ")
                        item_suggest.setForeground(QColor('#2ecc71'))
                    else:
                        item_suggest = QTableWidgetItem("Skip (Fully Allocated)  ")
                        item_suggest.setForeground(QColor('#e74c3c'))
            else:
                if percentage >= 30.0:
                    item_suggest = QTableWidgetItem(f"🚨 Overallocated (+RM {abs(suggested):,.2f})  ")
                    item_suggest.setForeground(QColor('#ff3333'))
                elif percentage <= 10.0:
                    item_suggest = QTableWidgetItem(f"⚠️ Underallocated (-RM {abs(suggested):,.2f})  ")
                    item_suggest.setForeground(QColor('#e67e22'))
                elif suggested > 0:
                    item_suggest = QTableWidgetItem(f"Deficit -RM {abs(suggested):,.2f}  ")
                    item_suggest.setForeground(QColor('#3498db'))
                elif suggested < 0:
                    item_suggest = QTableWidgetItem(f"Surplus +RM {abs(suggested):,.2f}  ")
                    item_suggest.setForeground(QColor('#95a5a6'))
                else:
                    item_suggest = QTableWidgetItem("Perfectly Balanced  ")
                    item_suggest.setForeground(QColor('#2ecc71'))

            item_suggest.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_value)
            self.table.setItem(row, 2, item_pct)
            self.table.setItem(row, 3, item_suggest)

        for i in range(len(assets_keys)): self.table.setRowHeight(i, 45)
        self.refresh_btn.setText("🔄 Refresh Market Data")
        self.refresh_btn.setEnabled(True)

    def plan_investment_dialog(self):
        cash, ok = QInputDialog.getDouble(self, "Capital Inflow Planning", "Enter total amount to invest (RM):", 
                                         value=self.current_cash_inflow, minValue=0.0, decimals=2)
        if ok and cash > 0:
            self.current_cash_inflow = cash
            self.refresh_data()
            
            reply = QMessageBox.question(self, 'Confirm Investment Plan', 
                                         'Have you successfully executed and funded these allocations?\nClick [Yes] to commit data to local storage and update your portfolio weights.',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.engine.execute_investment_plan(self.latest_rebalance_report)
                self.current_cash_inflow = 0.0 
                QMessageBox.information(self, "Success", "🎉 Investment data persisted and portfolio weights updated successfully!")
                self.refresh_data()

    def execute_pool_conversion(self):
        lots = self.engine.convert_maybank_pool_to_shares()
        if lots > 0:
            QMessageBox.information(self, "Conversion Successful", f"🎉 Successfully deducted cash pool and increased your Maybank holding by {lots * 100} shares!")
        else:
            QMessageBox.warning(self, "Insufficient Funds", "❌ Insufficient reservoir balance to purchase 1 board lot (100 shares) of Maybank yet.")
        self.refresh_data()

    def edit_asset_dialog(self):
        assets = ["VOO", "GLDM", "Maybank", "MMF", "EPF"]
        asset_name, ok1 = QInputDialog.getItem(self, "Core5 Configuration", "Select Asset Node:", assets, 0, False)
        if ok1 and asset_name:
            if asset_name in ["VOO", "GLDM", "Maybank"]: prompt = f"Update total share volume for {asset_name} (Shares):"
            elif asset_name == "MMF": prompt = "Update total principal balance for MMF (RM):"
            else: prompt = "Update total ledger balance for EPF (RM):"
            new_value, ok2 = QInputDialog.getDouble(self, f"Adjust {asset_name}", prompt, decimals=4, minValue=0.0)
            if ok2:
                if asset_name == "VOO": self.engine.update_asset("VOO", shares=new_value)
                elif asset_name == "GLDM": self.engine.update_asset("GLDM", shares=new_value)
                elif asset_name == "Maybank": self.engine.update_asset("Maybank", shares=new_value)
                elif asset_name == "MMF": self.engine.update_asset("MMF", principal=new_value, start_date=datetime.now().strftime("%Y-%m-%d"))
                elif asset_name == "EPF": self.engine.update_asset("EPF", balance=new_value)
                self.refresh_data()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
