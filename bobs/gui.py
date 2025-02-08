from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLCDNumber, QPushButton, QProgressBar, QHBoxLayout, QSizePolicy, QCheckBox, QDoubleSpinBox
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap
import pyqtgraph as pg
from epics import PV
import sys
import os
import numpy as np

class PhaseDriftGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phase Drift Monitor")
        self.setGeometry(100, 100, 1000, 700)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        layout = QVBoxLayout()
        
        # Phase Error Display
        self.phase_error_label = QLabel("Phase Error:")
        self.phase_error_display = QLCDNumber()
        layout.addWidget(self.phase_error_label)
        layout.addWidget(self.phase_error_display)
        
        # Correction Display
        self.pll_control_label = QLabel("PLL Correction:")
        self.pll_control_display = QLCDNumber()
        layout.addWidget(self.pll_control_label)
        layout.addWidget(self.pll_control_display)
        
        # Drift Deviation Progress Bar
        self.drift_label = QLabel("Drift Deviation:")
        self.drift_bar = QProgressBar()
        self.drift_bar.setMaximum(100)
        layout.addWidget(self.drift_label)
        layout.addWidget(self.drift_bar)
        
        # PID Controls
        pid_layout = QHBoxLayout()
        
        self.kp_label = QLabel("Kp:")
        self.kp_input = QDoubleSpinBox()
        self.kp_input.setRange(0, 10)
        self.kp_input.setValue(0.1)
        self.kp_input.setSingleStep(0.01)
        self.kp_input.valueChanged.connect(self.update_pid)
        
        self.ki_label = QLabel("Ki:")
        self.ki_input = QDoubleSpinBox()
        self.ki_input.setRange(0, 10)
        self.ki_input.setValue(0.01)
        self.ki_input.setSingleStep(0.01)
        self.ki_input.valueChanged.connect(self.update_pid)
        
        self.kd_label = QLabel("Kd:")
        self.kd_input = QDoubleSpinBox()
        self.kd_input.setRange(0, 10)
        self.kd_input.setValue(0.01)
        self.kd_input.setSingleStep(0.01)
        self.kd_input.valueChanged.connect(self.update_pid)
        
        pid_layout.addWidget(self.kp_label)
        pid_layout.addWidget(self.kp_input)
        pid_layout.addWidget(self.ki_label)
        pid_layout.addWidget(self.ki_input)
        pid_layout.addWidget(self.kd_label)
        pid_layout.addWidget(self.kd_input)
        
        layout.addLayout(pid_layout)
        
        # Start/Stop PID Button
        self.pid_button = QPushButton("Start PID")
        self.pid_button.clicked.connect(self.toggle_pid)
        layout.addWidget(self.pid_button)
        
        # EPICS PVs
        self.phase_error_pv = PV("SIM:PHASE:ERROR")
        self.pll_control_pv = PV("SIM:PLL:CONTROL")
        self.drift_deviation_pv = PV("SIM:DRIFT:DEVIATION")
        self.temp_lab_pv = PV("SIM:TEMP:LAB")
        self.temp_fiber_pv = PV("SIM:TEMP:FIBER")
        self.noise_pv = PV("SIM:NOISE")
        
        # Timer to update values
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_values)
        self.timer.start(1000)  # Update every second
        
        self.central_widget.setLayout(layout)
        self.pid_running = False
        self.start_time = 0
    
    def toggle_pid(self):
        """Start or stop the PID loop."""
        if self.pid_running:
            self.pid_button.setText("Start PID")
        else:
            self.pid_button.setText("Stop PID")
        
        self.pid_running = not self.pid_running
    
    def update_values(self):
        """Update the displayed PV values."""
        phase_error = self.phase_error_pv.get() or 0.0
        self.phase_error_display.display(phase_error)
    
    def update_pid(self):
        pass  # Integrate PID update logic

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhaseDriftGUI()
    window.show()
    sys.exit(app.exec_())
