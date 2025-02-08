from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QCheckBox, QLabel, QHBoxLayout
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
from epics import PV
import sys
import numpy as np

class EnvironmentPlot(QWidget):
    def __init__(self):
        super().__init__()

        # Main layout
        layout = QVBoxLayout()

        # Create main plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('bottom', "Time (s)")
        self.plot_widget.showGrid(x=True, y=True)

        # Main plot item
        self.main_plot = self.plot_widget.getPlotItem()

        # Create secondary ViewBoxes
        self.fiber_viewbox = pg.ViewBox()
        self.vibration_viewbox = pg.ViewBox()
        self.power_viewbox = pg.ViewBox()

        # Add ViewBoxes to left side
        self.main_plot.scene().addItem(self.fiber_viewbox)
        self.main_plot.scene().addItem(self.vibration_viewbox)
        self.main_plot.scene().addItem(self.power_viewbox)

        # Attach ViewBoxes to left
        self.fiber_axis = pg.AxisItem('left')
        self.fiber_axis.setLabel("Fiber Temp (°C)", color='b')
        self.main_plot.layout.addItem(self.fiber_axis, 2, 1)
        self.fiber_axis.linkToView(self.fiber_viewbox)

        self.vibration_axis = pg.AxisItem('left')
        self.vibration_axis.setLabel("Vibration (mm/s)", color='g')
        self.main_plot.layout.addItem(self.vibration_axis, 2, 2)
        self.vibration_axis.linkToView(self.vibration_viewbox)

        self.power_axis = pg.AxisItem('left')
        self.power_axis.setLabel("Power Stability (%)", color='m')
        self.main_plot.layout.addItem(self.power_axis, 2, 3)
        self.power_axis.linkToView(self.power_viewbox)

        layout.addWidget(self.plot_widget)

        # Checkbox and Label Section
        self.checkboxes = {}
        self.labels = {}
        param_names = ["Lab Temp", "Fiber Temp", "Vibration", "Power Stability"]
        colors = {'Lab Temp': 'r', 'Fiber Temp': 'b', 'Vibration': 'g', 'Power Stability': 'm'}

        checkbox_layout = QHBoxLayout()
        for param in param_names:
            cb = QCheckBox(param)
            cb.setChecked(True)
            cb.stateChanged.connect(self.toggle_plot)
            cb.setStyleSheet(f"color: {colors[param]}")
            lbl = QLabel("0.00")  # Placeholder for live values
            lbl.setStyleSheet(f"color: {colors[param]}")
            self.checkboxes[param] = cb
            self.labels[param] = lbl
            checkbox_layout.addWidget(cb)
            checkbox_layout.addWidget(lbl)
        layout.addLayout(checkbox_layout)

        # Auto-Scale Button
        self.auto_scale_button = QPushButton("Auto-Scale Axes")
        self.auto_scale_button.clicked.connect(self.auto_scale)
        layout.addWidget(self.auto_scale_button)

        # Reset Button
        self.reset_button = QPushButton("Reset View")
        self.reset_button.clicked.connect(self.reset_view)
        layout.addWidget(self.reset_button)

        self.setLayout(layout)

        # EPICS PVs
        self.temp_lab_pv = PV("SIM:TEMP:LAB")
        self.temp_fiber_pv = PV("SIM:TEMP:FIBER")
        self.vibration_pv = PV("SIM:VIBRATION:EXT")
        self.power_stability_pv = PV("SIM:POWER:STABILITY")

        # Timer for updating values
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_values)
        self.timer.start(1000)  # Update every second

        # Initialize Data Storage
        self.time_data = []
        self.temp_lab_data = []
        self.temp_fiber_data = []
        self.vibration_data = []
        self.power_stability_data = []
        self.max_time_window = 300  # 5-minute rolling window

        # Create Plots
        self.temp_lab_plot = self.main_plot.plot([], [], pen=pg.mkPen('r', width=2))
        self.temp_fiber_plot = pg.PlotCurveItem([], [], pen=pg.mkPen('b', width=2))
        self.vibration_plot = pg.PlotCurveItem([], [], pen=pg.mkPen('g', width=2))
        self.power_stability_plot = pg.PlotCurveItem([], [], pen=pg.mkPen('m', width=2))

        # Attach Plots to ViewBoxes
        self.fiber_viewbox.addItem(self.temp_fiber_plot)
        self.vibration_viewbox.addItem(self.vibration_plot)
        self.power_viewbox.addItem(self.power_stability_plot)

        # Connect view resizing
        self.main_plot.vb.sigResized.connect(self.update_views)

    def update_values(self):
        """Retrieve and update PV values"""
        temp_lab = self.temp_lab_pv.get() or 0.0
        temp_fiber = self.temp_fiber_pv.get() or 0.0
        vibration = self.vibration_pv.get() or 0.0
        power_stability = self.power_stability_pv.get() or 1.0

        # Update Labels
        self.labels["Lab Temp"].setText(f"{temp_lab:.2f} °C")
        self.labels["Fiber Temp"].setText(f"{temp_fiber:.2f} °C")
        self.labels["Vibration"].setText(f"{vibration:.2f} mm/s")
        self.labels["Power Stability"].setText(f"{power_stability:.2f} %")

        # Append Data
        if len(self.time_data) >= self.max_time_window:
            self.time_data.pop(0)
            self.temp_lab_data.pop(0)
            self.temp_fiber_data.pop(0)
            self.vibration_data.pop(0)
            self.power_stability_data.pop(0)

        self.time_data.append(len(self.time_data))
        self.temp_lab_data.append(temp_lab)
        self.temp_fiber_data.append(temp_fiber)
        self.vibration_data.append(vibration)
        self.power_stability_data.append(power_stability)

        # Update Plots
        if self.checkboxes["Lab Temp"].isChecked():
            self.temp_lab_plot.setData(self.time_data, self.temp_lab_data)
        if self.checkboxes["Fiber Temp"].isChecked():
            self.temp_fiber_plot.setData(self.time_data, self.temp_fiber_data)
        if self.checkboxes["Vibration"].isChecked():
            self.vibration_plot.setData(self.time_data, self.vibration_data)
        if self.checkboxes["Power Stability"].isChecked():
            self.power_stability_plot.setData(self.time_data, self.power_stability_data)

    def toggle_plot(self):
        """Show or hide plots based on checkboxes"""
        self.temp_lab_plot.setVisible(self.checkboxes["Lab Temp"].isChecked())
        self.temp_fiber_plot.setVisible(self.checkboxes["Fiber Temp"].isChecked())
        self.vibration_plot.setVisible(self.checkboxes["Vibration"].isChecked())
        self.power_stability_plot.setVisible(self.checkboxes["Power Stability"].isChecked())

    def update_views(self):
        """Update linked view boxes when main plot is resized"""
        self.fiber_viewbox.setGeometry(self.main_plot.vb.sceneBoundingRect())
        self.vibration_viewbox.setGeometry(self.main_plot.vb.sceneBoundingRect())
        self.power_viewbox.setGeometry(self.main_plot.vb.sceneBoundingRect())

    def auto_scale(self):
        """Auto-scale the plot to fit current data ranges"""
        self.main_plot.enableAutoRange()
        self.fiber_viewbox.enableAutoRange()
        self.vibration_viewbox.enableAutoRange()
        self.power_viewbox.enableAutoRange()

    def reset_view(self):
        """Reset zoom and panning"""
        self.main_plot.enableAutoRange()
        self.fiber_viewbox.enableAutoRange()
        self.vibration_viewbox.enableAutoRange()
        self.power_viewbox.enableAutoRange()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Environment Plot")
    window.setCentralWidget(EnvironmentPlot())
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec_())
