import sys
import time
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QWidget, QListWidget, QLineEdit, QLabel, QHBoxLayout
)
import pyqtgraph as pg
from epics import PV

class PVPlotter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPICS PV Data Browser")
        self.resize(800, 600)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout()
        
        self.pv_input = QLineEdit()
        self.pv_input.setPlaceholderText("Enter PV name")
        self.add_pv_button = QPushButton("Add PV")
        self.remove_pv_button = QPushButton("Remove Selected PV")
        
        self.pv_list = QListWidget()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("bottom", "Time (s)")
        self.plot_widget.setLabel("left", "PV Value")

        self.start_button = QPushButton("Start Plotting")
        self.stop_button = QPushButton("Stop Plotting")

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        self.layout.addWidget(self.pv_input)
        self.layout.addWidget(self.add_pv_button)
        self.layout.addWidget(self.remove_pv_button)
        self.layout.addWidget(self.pv_list)
        self.layout.addWidget(self.plot_widget)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)
        
        self.central_widget.setLayout(self.layout)
        
        self.add_pv_button.clicked.connect(self.add_pv)
        self.remove_pv_button.clicked.connect(self.remove_pv)
        self.start_button.clicked.connect(self.start_plotting)
        self.stop_button.clicked.connect(self.stop_plotting)
        
        self.pv_objects = {}  # Stores PV instances
        self.data_buffers = {}  # Stores PV data
        self.curves = {}  # Stores plot curves
        self.time_start = time.time()
        self.last_update = {}  # Stores last update time for each PV

        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)

    def add_pv(self):
        pv_name = self.pv_input.text().strip()
        if pv_name and pv_name not in self.pv_objects:
            self.pv_objects[pv_name] = PV(pv_name, callback=self.pv_callback)
            self.data_buffers[pv_name] = {"x": [], "y": []}
            self.curves[pv_name] = self.plot_widget.plot([], [], pen=pg.intColor(len(self.curves)))
            self.pv_list.addItem(pv_name)
            self.last_update[pv_name] = 0  # Initialize last update time
            self.start_button.setEnabled(True)
        self.pv_input.clear()

    def remove_pv(self):
        selected_item = self.pv_list.currentItem()
        if selected_item:
            pv_name = selected_item.text()
            self.pv_list.takeItem(self.pv_list.row(selected_item))
            self.pv_objects.pop(pv_name, None)
            self.data_buffers.pop(pv_name, None)
            self.curves[pv_name].clear()
            self.curves.pop(pv_name, None)
            self.last_update.pop(pv_name, None)
            if not self.pv_objects:
                self.start_button.setEnabled(False)

    def pv_callback(self, pvname=None, value=None, **kwargs):
        """ Updates data buffers when a PV value changes, but throttles updates. """
        if pvname in self.data_buffers:
            current_time = time.time()
            elapsed_time = current_time - self.time_start
            
            # Ensure we only update every 0.5s to avoid spamming the plot
            if current_time - self.last_update[pvname] < 0.5:
                return
            
            self.last_update[pvname] = current_time  # Update last callback time
            self.data_buffers[pvname]["x"].append(elapsed_time)
            self.data_buffers[pvname]["y"].append(value)
            
            # Limit buffer to avoid memory overflow
            if len(self.data_buffers[pvname]["x"]) > 500:
                self.data_buffers[pvname]["x"].pop(0)
                self.data_buffers[pvname]["y"].pop(0)

            # Debug output to verify values are received
            print(f"PV {pvname} updated: Time={elapsed_time:.2f}, Value={value}")

    def start_plotting(self):
        """ Starts the periodic update of the plot. """
        print("Starting plot update...")
        self.timer.start(500)  # Refresh plot every 500ms
        self.stop_button.setEnabled(True)
        self.start_button.setEnabled(False)
    
    def stop_plotting(self):
        """ Stops updating the plot. """
        print("Stopping plot update...")
        self.timer.stop()
        self.stop_button.setEnabled(False)
        self.start_button.setEnabled(True)
    
    def update_plot(self):
        """ Refreshes the plot with new data at a controlled rate. """
        for pv_name, curve in self.curves.items():
            if self.data_buffers[pv_name]["x"]:
                curve.setData(self.data_buffers[pv_name]["x"], self.data_buffers[pv_name]["y"])
        
        # Auto-scale Y-axis to fit the data
        all_values = [val for pv in self.data_buffers.values() for val in pv["y"]]
        if all_values:
            self.plot_widget.setYRange(min(all_values) - 1, max(all_values) + 1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PVPlotter()
    window.show()
    sys.exit(app.exec_())

"""
import wx
import numpy as np
import time
import threading
from epics import PV
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

class EPICSDataBrowser(wx.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(900, 600))
        
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Create Matplotlib Figure
        self.figure = Figure()
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(panel, -1, self.figure)

        # Input for PVs
        self.pv_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.pv_input.Bind(wx.EVT_TEXT_ENTER, self.add_pv)

        # Add PV Button
        self.add_pv_btn = wx.Button(panel, label="Add PV")
        self.add_pv_btn.Bind(wx.EVT_BUTTON, self.add_pv)

        # Remove PV Button
        self.remove_pv_btn = wx.Button(panel, label="Remove Selected PV")
        self.remove_pv_btn.Bind(wx.EVT_BUTTON, self.remove_pv)

        # List of PVs
        self.pv_list = wx.ListBox(panel, style=wx.LB_SINGLE)

        # Start and Stop Buttons
        self.start_btn = wx.Button(panel, label="Start Plotting")
        self.start_btn.Bind(wx.EVT_BUTTON, self.start_plot)

        self.stop_btn = wx.Button(panel, label="Stop Plotting")
        self.stop_btn.Bind(wx.EVT_BUTTON, self.stop_plot)
        self.stop_btn.Disable()

        # Layout
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.pv_input, 1, wx.EXPAND | wx.ALL, 5)
        hbox.Add(self.add_pv_btn, 0, wx.ALL, 5)
        hbox.Add(self.remove_pv_btn, 0, wx.ALL, 5)

        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(self.pv_list, 0, wx.EXPAND | wx.ALL, 5)
        vbox.Add(self.canvas, 1, wx.EXPAND)
        vbox.Add(self.start_btn, 0, wx.ALL | wx.EXPAND, 5)
        vbox.Add(self.stop_btn, 0, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(vbox)

        # Data storage
        self.pvs = {}  # Stores PV objects
        self.data = {}  # Stores PV data
        self.start_time = time.time()
        self.running = False
        self.thread = None

    def add_pv(self, event):
#       Add a PV to track
        pv_name = self.pv_input.GetValue().strip()
        if pv_name and pv_name not in self.pvs:
            self.pvs[pv_name] = PV(pv_name)
            self.data[pv_name] = {"time": [], "value": []}
            self.pv_list.Append(pv_name)
        self.pv_input.SetValue("")

    def remove_pv(self, event):
#Remove selected PV
        selection = self.pv_list.GetSelection()
        if selection != wx.NOT_FOUND:
            pv_name = self.pv_list.GetString(selection)
            del self.pvs[pv_name]
            del self.data[pv_name]
            self.pv_list.Delete(selection)

    def start_plot(self, event):
#Start the live plotting thread
        self.running = True
        self.start_btn.Disable()
        self.stop_btn.Enable()
        self.thread = threading.Thread(target=self.update_plot)
        self.thread.start()

    def stop_plot(self, event):
#Stop the live plotting thread
        self.running = False
        self.start_btn.Enable()
        self.stop_btn.Disable()

    def update_plot(self):
#Retrieve EPICS data and update the plot
        while self.running:
            current_time = time.time() - self.start_time
            
            for pv_name, pv in self.pvs.items():
                value = pv.get() or 0.0  # Fetch PV value
                self.data[pv_name]["time"].append(current_time)
                self.data[pv_name]["value"].append(value)

                # Keep only last 300s (5 min) of data
                if len(self.data[pv_name]["time"]) > 300:
                    self.data[pv_name]["time"].pop(0)
                    self.data[pv_name]["value"].pop(0)

            wx.CallAfter(self.refresh_plot)
            time.sleep(1)

    def refresh_plot(self):
#Refresh the plot with new data
        self.axes.clear()
        for pv_name, pv_data in self.data.items():
            self.axes.plot(pv_data["time"], pv_data["value"], label=pv_name)
        
        self.axes.set_xlabel("Time (s)")
        self.axes.set_ylabel("PV Value")
        self.axes.legend()
        self.canvas.draw()

if __name__ == "__main__":
    app = wx.App(False)
    frame = EPICSDataBrowser(None, "EPICS PV Data Browser")
    frame.Show()
    app.MainLoop()
"""
