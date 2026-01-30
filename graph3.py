# import sys
# import numpy as np
# import json
# import time
# import struct
# from collections import deque
# from datetime import datetime
# from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
#                              QHBoxLayout, QLabel, QPushButton, QComboBox, 
#                              QSpinBox, QGroupBox, QGridLayout)
# from PyQt5.QtCore import QTimer, Qt
# import pyqtgraph as pg
# import paho.mqtt.client as mqtt

# # MQTT Configuration
# BROKER = "192.168.1.231"
# TOPIC = "sarayu/d1/topic1"

# class RealTimePlotter(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("Real-Time Data Plotter - 1 Second Window")
#         self.setGeometry(100, 100, 1400, 800)
        
#         # Data buffers for 1-second window (2 frames of 0.5 seconds each)
#         self.frame_buffer1 = None  # First 0.5-second frame
#         self.frame_buffer2 = None  # Second 0.5-second frame
#         self.current_frame = None  # Current frame being received
        
#         # Plot data buffers
#         self.time_data = deque(maxlen=1000)  # Time axis for 1 second
#         self.channel_data = {}  # Dictionary to store channel data
#         self.tacho_data = {}    # Dictionary to store tacho data
        
#         # Sample rate and frame information
#         self.sample_rate = 1000  # Default, will be updated from data
#         self.samples_per_frame = 0  # Will be updated from data
#         self.num_channels = 0
#         self.num_tacho_channels = 0
#         self.samples_per_second = 0
        
#         # Frame tracking
#         self.frame_count = 0
#         self.last_frame_index = -1
#         self.expected_frame_index = 0
        
#         # Initialize UI
#         self.init_ui()
#         self.init_plots()
        
#         # Initialize MQTT
#         self.init_mqtt()
        
#         # Timer for updating plots
#         self.update_timer = QTimer()
#         self.update_timer.timeout.connect(self.update_plots)
#         self.update_timer.start(100)  # Update every 100ms
        
#         # Buffer for display data
#         self.display_buffer = deque(maxlen=1000)
#         self.display_tacho_buffer = deque(maxlen=1000)
        
#     def init_ui(self):
#         # Central widget
#         central_widget = QWidget()
#         self.setCentralWidget(central_widget)
        
#         # Main layout
#         main_layout = QVBoxLayout(central_widget)
        
#         # Control panel
#         control_group = QGroupBox("Controls")
#         control_layout = QGridLayout()
        
#         # Status labels
#         self.status_label = QLabel("Status: Disconnected")
#         self.frame_label = QLabel("Frame: 0")
#         self.sample_rate_label = QLabel("Sample Rate: N/A")
#         self.time_window_label = QLabel("Time Window: 1.0 sec")
        
#         # Channel selection
#         self.channel_combo = QComboBox()
#         self.channel_combo.addItem("All Channels")
#         self.channel_combo.currentIndexChanged.connect(self.update_plot_selection)
        
#         # Tacho channel selection
#         self.tacho_combo = QComboBox()
#         self.tacho_combo.addItem("No Tacho")
#         self.tacho_combo.currentIndexChanged.connect(self.update_plot_selection)
        
#         # Add widgets to control layout
#         control_layout.addWidget(QLabel("Status:"), 0, 0)
#         control_layout.addWidget(self.status_label, 0, 1)
#         control_layout.addWidget(QLabel("Current Frame:"), 0, 2)
#         control_layout.addWidget(self.frame_label, 0, 3)
        
#         control_layout.addWidget(QLabel("Sample Rate:"), 1, 0)
#         control_layout.addWidget(self.sample_rate_label, 1, 1)
#         control_layout.addWidget(QLabel("Time Window:"), 1, 2)
#         control_layout.addWidget(self.time_window_label, 1, 3)
        
#         control_layout.addWidget(QLabel("Data Channel:"), 2, 0)
#         control_layout.addWidget(self.channel_combo, 2, 1)
#         control_layout.addWidget(QLabel("Tacho Channel:"), 2, 2)
#         control_layout.addWidget(self.tacho_combo, 2, 3)
        
#         # Clear button
#         clear_btn = QPushButton("Clear Plots")
#         clear_btn.clicked.connect(self.clear_plots)
        
#         control_layout.addWidget(clear_btn, 3, 0, 1, 4)
        
#         control_group.setLayout(control_layout)
#         main_layout.addWidget(control_group)
        
#         # Plot layout
#         plot_widget = QWidget()
#         plot_layout = QHBoxLayout(plot_widget)
        
#         # Create plot widgets
#         self.data_plot = pg.PlotWidget(title="Data Channels - 1 Second Window")
#         self.data_plot.setLabel('left', 'Amplitude')
#         self.data_plot.setLabel('bottom', 'Time', 's')
#         self.data_plot.showGrid(x=True, y=True, alpha=0.3)
#         self.data_plot.addLegend()
        
#         self.tacho_plot = pg.PlotWidget(title="Tacho Signals")
#         self.tacho_plot.setLabel('left', 'Value')
#         self.tacho_plot.setLabel('bottom', 'Time', 's')
#         self.tacho_plot.showGrid(x=True, y=True, alpha=0.3)
#         self.tacho_plot.addLegend()
        
#         plot_layout.addWidget(self.data_plot)
#         plot_layout.addWidget(self.tacho_plot)
        
#         main_layout.addWidget(plot_widget)
        
#         # Data curves dictionary
#         self.data_curves = {}
#         self.tacho_curves = {}
        
#     def init_plots(self):
#         # Initialize with some default curves
#         self.data_curves['ch0'] = self.data_plot.plot(pen='r', name='Channel 0')
#         self.data_curves['ch1'] = self.data_plot.plot(pen='g', name='Channel 1')
#         self.data_curves['ch2'] = self.data_plot.plot(pen='b', name='Channel 2')
        
#         self.tacho_curves['tacho0'] = self.tacho_plot.plot(pen='y', name='Tacho Freq')
#         self.tacho_curves['tacho1'] = self.tacho_plot.plot(pen='m', name='Tacho Trig')
        
#     def init_mqtt(self):
#         self.client = mqtt.Client()
#         self.client.on_connect = self.on_connect
#         self.client.on_message = self.on_message
        
#         # Connect in a separate thread to avoid blocking
#         self.client.connect_async(BROKER, 1883, 60)
#         self.client.loop_start()
        
#     def on_connect(self, client, userdata, flags, rc):
#         if rc == 0:
#             self.status_label.setText("Status: Connected")
#             client.subscribe(TOPIC)
#             print(f"Connected to MQTT broker and subscribed to {TOPIC}")
#         else:
#             self.status_label.setText(f"Status: Connection failed ({rc})")
            
#     def on_message(self, client, userdata, msg):
#         try:
#             payload = msg.payload
#             data = np.frombuffer(payload, dtype='<H')  # Little-endian uint16
            
#             if len(data) < 100:
#                 return
                
#             # Parse header
#             header = data[:100]
            
#             # Calculate frame index from first two uint16 values
#             frame_index = struct.unpack('<I', header[:2].tobytes())[0]
#             num_channels = int(header[2])
#             sample_rate = int(header[3])
#             samples_per_channel = int(header[4])
#             num_tacho_channels = int(header[6])
            
#             # Update sample rate if changed
#             if self.sample_rate != sample_rate:
#                 self.sample_rate = sample_rate
#                 self.samples_per_second = sample_rate
#                 self.sample_rate_label.setText(f"Sample Rate: {sample_rate} Hz")
                
#             # Calculate total samples for this frame (0.5 seconds)
#             total_samples = samples_per_channel
            
#             # Parse data channels
#             start_idx = 100
#             end_idx = start_idx + (samples_per_channel * num_channels)
            
#             if end_idx > len(data):
#                 return
                
#             # Get interleaved data and reshape
#             interleaved = data[start_idx:end_idx]
            
#             # Reshape to separate channels
#             if num_channels > 0 and samples_per_channel > 0:
#                 try:
#                     # Reshape to [num_channels, samples_per_channel]
#                     channel_data = interleaved.reshape((num_channels, samples_per_channel))
                    
#                     # Parse tacho data if available
#                     tacho_data = []
#                     if num_tacho_channels > 0:
#                         tacho_start = end_idx
#                         for i in range(num_tacho_channels):
#                             tacho_end = tacho_start + samples_per_channel
#                             if tacho_end <= len(data):
#                                 tacho_channel = data[tacho_start:tacho_end]
#                                 tacho_data.append(tacho_channel)
#                                 tacho_start = tacho_end
                    
#                     # Process the frame
#                     self.process_frame(frame_index, channel_data, tacho_data, 
#                                       sample_rate, samples_per_channel)
                    
#                 except Exception as e:
#                     print(f"Error reshaping data: {e}")
                    
#         except Exception as e:
#             print(f"Error processing MQTT message: {e}")
            
#     def process_frame(self, frame_index, channel_data, tacho_data, sample_rate, samples_per_frame):
#         # Update frame counter
#         self.frame_count += 1
#         self.frame_label.setText(f"Frame: {self.frame_count}")
        
#         # Calculate time axis for this 0.5-second frame
#         frame_duration = samples_per_frame / sample_rate  # Should be 0.5 seconds
#         time_axis = np.linspace(0, frame_duration, samples_per_frame, endpoint=False)
        
#         # Check if we have a complete 1-second window
#         if frame_index % 2 == 0:
#             # Even frame - store as first half
#             self.frame_buffer1 = {
#                 'time': time_axis,
#                 'channels': channel_data,
#                 'tacho': tacho_data,
#                 'frame_index': frame_index
#             }
#         else:
#             # Odd frame - store as second half
#             self.frame_buffer2 = {
#                 'time': time_axis + 0.5,  # Offset by 0.5 seconds
#                 'channels': channel_data,
#                 'tacho': tacho_data,
#                 'frame_index': frame_index
#             }
            
#             # When we have both frames, merge them
#             if self.frame_buffer1 is not None:
#                 self.merge_and_buffer_frames()
    
#     def merge_and_buffer_frames(self):
#         try:
#             # Merge time axes
#             time_merged = np.concatenate([self.frame_buffer1['time'], self.frame_buffer2['time']])
            
#             # Merge channel data
#             channels_merged = []
#             num_channels = min(self.frame_buffer1['channels'].shape[0], 
#                              self.frame_buffer2['channels'].shape[0])
            
#             for ch in range(num_channels):
#                 ch_data = np.concatenate([
#                     self.frame_buffer1['channels'][ch],
#                     self.frame_buffer2['channels'][ch]
#                 ])
#                 channels_merged.append(ch_data)
            
#             # Merge tacho data if available
#             tacho_merged = []
#             if (self.frame_buffer1['tacho'] and self.frame_buffer2['tacho']):
#                 num_tacho = min(len(self.frame_buffer1['tacho']), len(self.frame_buffer2['tacho']))
#                 for t in range(num_tacho):
#                     tacho_data = np.concatenate([
#                         self.frame_buffer1['tacho'][t],
#                         self.frame_buffer2['tacho'][t]
#                     ])
#                     tacho_merged.append(tacho_data)
            
#             # Update display buffers
#             self.display_buffer = {
#                 'time': time_merged,
#                 'channels': channels_merged,
#                 'tacho': tacho_merged,
#                 'frame_start': self.frame_buffer1['frame_index'],
#                 'frame_end': self.frame_buffer2['frame_index']
#             }
            
#             # Update channel selection if needed
#             self.update_channel_selection(num_channels, len(tacho_merged))
            
#         except Exception as e:
#             print(f"Error merging frames: {e}")
            
#     def update_channel_selection(self, num_channels, num_tacho):
#         # Update data channel combo
#         current_channels = self.channel_combo.count()
#         if current_channels != (num_channels + 1):  # +1 for "All Channels"
#             self.channel_combo.clear()
#             self.channel_combo.addItem("All Channels")
#             for i in range(num_channels):
#                 self.channel_combo.addItem(f"Channel {i}")
        
#         # Update tacho channel combo
#         current_tacho = self.tacho_combo.count()
#         if current_tacho != (num_tacho + 1):  # +1 for "No Tacho"
#             self.tacho_combo.clear()
#             self.tacho_combo.addItem("No Tacho")
#             for i in range(num_tacho):
#                 self.tacho_combo.addItem(f"Tacho {i}")
                
#     def update_plot_selection(self):
#         # This will be called when channel selection changes
#         pass
        
#     def update_plots(self):
#         if not hasattr(self, 'display_buffer') or not self.display_buffer:
#             return
            
#         # Get the selected channel
#         selected_channel = self.channel_combo.currentIndex() - 1  # -1 for "All Channels"
#         selected_tacho = self.tacho_combo.currentIndex() - 1  # -1 for "No Tacho"
        
#         # Update data plot
#         if selected_channel == -1:  # Show all channels
#             for i, curve in enumerate(self.data_curves.values()):
#                 if i < len(self.display_buffer['channels']):
#                     # Downsample for display if needed (show about 10 cycles)
#                     data = self.display_buffer['channels'][i]
#                     if len(data) > 1000:
#                         # Simple downsampling for display
#                         indices = np.linspace(0, len(data)-1, 1000, dtype=int)
#                         plot_data = data[indices]
#                         plot_time = self.display_buffer['time'][indices]
#                     else:
#                         plot_data = data
#                         plot_time = self.display_buffer['time']
                    
#                     curve.setData(plot_time, plot_data)
#                 else:
#                     curve.setData([], [])
#         else:  # Show selected channel
#             if selected_channel < len(self.display_buffer['channels']):
#                 data = self.display_buffer['channels'][selected_channel]
#                 if len(data) > 1000:
#                     indices = np.linspace(0, len(data)-1, 1000, dtype=int)
#                     plot_data = data[indices]
#                     plot_time = self.display_buffer['time'][indices]
#                 else:
#                     plot_data = data
#                     plot_time = self.display_buffer['time']
                    
#                 # Show only selected channel
#                 for i, curve in enumerate(self.data_curves.values()):
#                     if i == 0:
#                         curve.setData(plot_time, plot_data)
#                     else:
#                         curve.setData([], [])
        
#         # Update tacho plot
#         if selected_tacho >= 0 and selected_tacho < len(self.display_buffer['tacho']):
#             tacho_data = self.display_buffer['tacho'][selected_tacho]
#             if len(tacho_data) > 1000:
#                 indices = np.linspace(0, len(tacho_data)-1, 1000, dtype=int)
#                 plot_tacho = tacho_data[indices]
#                 plot_time = self.display_buffer['time'][indices]
#             else:
#                 plot_tacho = tacho_data
#                 plot_time = self.display_buffer['time']
                
#             # Show tacho data
#             for i, curve in enumerate(self.tacho_curves.values()):
#                 if i == 0:
#                     curve.setData(plot_time, plot_tacho)
#                 else:
#                     curve.setData([], [])
#         else:
#             # Clear tacho plot
#             for curve in self.tacho_curves.values():
#                 curve.setData([], [])
        
#         # Update plot titles with frame information
#         if hasattr(self.display_buffer, 'frame_start'):
#             self.data_plot.setTitle(f"Data Channels - Frames {self.display_buffer['frame_start']} to {self.display_buffer['frame_end']}")
#             self.tacho_plot.setTitle(f"Tacho Signals - Frames {self.display_buffer['frame_start']} to {self.display_buffer['frame_end']}")
            
#     def clear_plots(self):
#         # Clear all curves
#         for curve in self.data_curves.values():
#             curve.setData([], [])
#         for curve in self.tacho_curves.values():
#             curve.setData([], [])
        
#         # Clear buffers
#         self.frame_buffer1 = None
#         self.frame_buffer2 = None
#         self.display_buffer = {}
#         self.frame_count = 0
#         self.frame_label.setText("Frame: 0")
        
#     def closeEvent(self, event):
#         # Clean up MQTT connection
#         if hasattr(self, 'client'):
#             self.client.loop_stop()
#             self.client.disconnect()
#         event.accept()

# def main():
#     app = QApplication(sys.argv)
#     app.setStyle('Fusion')
    
#     # Set dark theme for better visibility
#     pg.setConfigOptions(antialias=True)
    
#     window = RealTimePlotter()
#     window.show()
    
#     sys.exit(app.exec_())

# if __name__ == "__main__":
#     main()







import sys
import numpy as np
import paho.mqtt.client as mqtt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QLabel, QScrollArea, QHBoxLayout, QSizePolicy)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from pyqtgraph import PlotWidget, mkPen
import pyqtgraph as pg
import signal

BROKER = "192.168.1.231"
TOPIC = "sarayu/d1/topic1"

class MQTTHandler(QObject):
    """Handles MQTT communication in a separate thread"""
    data_received = pyqtSignal(object, object, object, int)  # interleaved, tacho_freq, tacho_trigger, frame_index
    
    def __init__(self):
        super().__init__()
        self.sample_rate = 0
        self.num_channels = 0
        self.samples_per_channel = 0
        self.current_frame_index = -1
        self.running = True
        
    def start(self):
        """Start MQTT client"""
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        
        # Connect in background thread
        try:
            self.mqtt_client.connect_async(BROKER, 1883, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"Failed to start MQTT: {e}")
            
    def stop(self):
        """Stop MQTT client"""
        self.running = False
        if hasattr(self, 'mqtt_client'):
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            
    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        print(f"Connected to MQTT broker with result code {rc}")
        if rc == 0:
            client.subscribe(TOPIC)
            print(f"Subscribed to topic: {TOPIC}")
            
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        if not self.running:
            return
            
        try:
            payload = msg.payload
            data = np.frombuffer(payload, dtype='<H')
            
            if len(data) < 100:
                return
                
            # Parse header
            header = data[:100]
            
            # Frame index (32-bit from two 16-bit values)
            frame_index = int(header[0]) + (int(header[1]) << 16)
            
            num_channels = int(header[2])
            sample_rate = int(header[3])
            samples_per_channel = int(header[4])
            num_tacho_channels = int(header[6])
            
            # Parse interleaved samples
            total_samples = samples_per_channel * num_channels
            start = 100
            end = start + total_samples
            
            if len(data) < end:
                return
                
            interleaved = data[start:end].astype(np.float32)
            
            # Parse tacho data
            start = end
            end = start + samples_per_channel
            tacho_freq = data[start:end].astype(np.float32)
            
            start = end
            end = start + samples_per_channel
            tacho_trigger = data[start:end].astype(np.float32)
            
            # Emit signal for GUI thread
            self.data_received.emit(interleaved, tacho_freq, tacho_trigger, frame_index)
            
            # Update internal state
            self.sample_rate = sample_rate
            self.num_channels = num_channels
            self.samples_per_channel = samples_per_channel
            self.current_frame_index = frame_index
            
        except Exception as e:
            print(f"Error processing MQTT message: {e}")

class ChannelPlotWidget(QWidget):
    """Custom widget for a single channel plot with title and stats"""
    def __init__(self, channel_num, channel_type="CH", parent=None):
        super().__init__(parent)
        self.channel_num = channel_num
        self.channel_type = channel_type  # "CH" for regular, "TACHO_F" for frequency, "TACHO_T" for trigger
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Set size policy - Fixed height but expand horizontally
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(180)  # Slightly smaller for more channels on screen
        self.setMaximumHeight(180)
        
        # Create horizontal layout for title and stats
        header_layout = QHBoxLayout()
        
        # Determine title text and color based on channel type
        if channel_type == "CH":
            title_text = f"CH {channel_num + 1:02d}"
            title_bg = "#2c3e50"  # Dark blue
            title_color = "white"
        elif channel_type == "TACHO_F":
            title_text = "TACHO FREQ"
            title_bg = "#c0392b"  # Dark red
            title_color = "white"
        else:  # TACHO_T
            title_text = "TACHO TRIG"
            title_bg = "#27ae60"  # Dark green
            title_color = "white"
        
        # Title with fixed width
        self.title_label = QLabel(title_text)
        self.title_label.setStyleSheet(f"""
            font-weight: bold; 
            font-size: 12px; 
            color: {title_color};
            background-color: {title_bg};
            padding: 4px 8px;
            border-radius: 3px;
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFixedWidth(90)
        header_layout.addWidget(self.title_label)
        
        # Stats label
        self.stats_label = QLabel("Min: -- | Max: -- | Mean: --")
        self.stats_label.setStyleSheet("font-size: 10px; color: #555; padding: 3px;")
        self.stats_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header_layout.addWidget(self.stats_label)
        
        layout.addLayout(header_layout)
        
        # Plot widget with fixed height
        self.plot_widget = PlotWidget()
        self.plot_widget.setLabel('left', '')
        self.plot_widget.setLabel('bottom', '')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        # Fixed height for plot area
        self.plot_widget.setMinimumHeight(120)
        self.plot_widget.setMaximumHeight(120)
        
        # Remove axis labels to save space
        self.plot_widget.getAxis('left').setStyle(showValues=False)
        self.plot_widget.getAxis('bottom').setStyle(showValues=False)
        
        # Set plot styling
        self.plot_widget.setBackground('#f8f8f8')
        self.plot_widget.setMouseEnabled(x=False, y=False)  # Disable zoom/pan for consistency
        
        layout.addWidget(self.plot_widget)
        
        # Initialize curve with different colors based on channel type
        if channel_type == "CH":
            colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', 
                     '#1abc9c', '#d35400', '#34495e', '#e67e22', '#16a085']
            color = colors[channel_num % len(colors)]
        elif channel_type == "TACHO_F":
            color = '#c0392b'  # Red for frequency
        else:  # TACHO_T
            color = '#27ae60'  # Green for trigger
            
        self.curve = self.plot_widget.plot([], [], pen=mkPen(color=color, width=1.5))
        
        # Store data
        self.data = np.array([])
        self.time_data = np.array([])
        
    def update_plot(self, time_data, channel_data):
        """Update the plot with new data"""
        self.time_data = time_data
        self.data = channel_data
        
        # Update the curve
        self.curve.setData(time_data, channel_data)
        
        # Update stats
        if len(channel_data) > 0:
            min_val = np.min(channel_data)
            max_val = np.max(channel_data)
            mean_val = np.mean(channel_data)
            
            # Format stats based on channel type
            if self.channel_type == "TACHO_F":
                self.stats_label.setText(
                    f"Min: {min_val:8.1f} Hz | Max: {max_val:8.1f} Hz | Mean: {mean_val:8.1f} Hz"
                )
            elif self.channel_type == "TACHO_T":
                self.stats_label.setText(
                    f"Min: {min_val:8.1f} | Max: {max_val:8.1f} | Mean: {mean_val:8.1f}"
                )
            else:
                self.stats_label.setText(
                    f"Min: {min_val:8.2f} | Max: {max_val:8.2f} | Mean: {mean_val:8.2f}"
                )
            
            # Auto-scale Y axis
            data_range = max_val - min_val
            if data_range > 0:
                padding = data_range * 0.1
                self.plot_widget.setYRange(min_val - padding, max_val + padding)
            else:
                self.plot_widget.setYRange(-1, 1)

class MQTTGraphApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Data buffer for 1 second window
        self.sample_rate = 0
        self.buffer_size = 0
        self.current_buffer_size = 1000
        
        # Buffers for all channels including tacho
        self.time_buffer = np.array([])
        self.channel_buffers = []  # Regular channels
        self.tacho_freq_buffer = np.array([])
        self.tacho_trigger_buffer = np.array([])
        
        self.num_channels = 0
        self.samples_per_channel = 0
        self.current_frame_index = -1
        self.running = True
        self.last_update_time = 0
        self.update_count = 0
        
        # List to store all plot widgets (regular + tacho)
        self.all_plot_widgets = []
        
        # Setup MQTT handler
        self.mqtt_handler = MQTTHandler()
        self.mqtt_handler.data_received.connect(self.on_data_received)
        
        # Setup UI
        self.init_ui()
        
        # Start MQTT
        self.mqtt_handler.start()
        
        # Setup update timer for GUI
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(100)  # Update every 100ms
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("MQTT Real-time Data Viewer - All Channels")
        self.setGeometry(50, 50, 1200, 800)
        
        # Create central widget with scroll area
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Status bar at top (fixed height)
        self.create_status_bar(main_layout)
        
        # Create scroll area for ALL plots (regular + tacho) stacked vertically
        self.create_all_plots_area(main_layout)
        
    def create_status_bar(self, parent_layout):
        """Create status bar with information"""
        status_widget = QWidget()
        status_widget.setFixedHeight(60)
        status_widget.setStyleSheet("""
            background-color: #34495e; 
            color: white;
            border-bottom: 2px solid #2c3e50;
        """)
        
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(15, 5, 15, 5)
        status_layout.setSpacing(20)
        
        # Create status labels
        self.lbl_frame = QLabel("Frame: --")
        self.lbl_rate = QLabel("Rate: -- Hz")
        self.lbl_channels = QLabel("Channels: --")
        self.lbl_window = QLabel("Window: -- s")
        self.lbl_update = QLabel("Update: -- Hz")
        
        # Style the labels
        status_style = """
            font-weight: bold; 
            font-size: 11px; 
            color: white;
            padding: 2px;
        """
        
        labels = [self.lbl_frame, self.lbl_rate, self.lbl_channels, 
                 self.lbl_window, self.lbl_update]
        
        for label in labels:
            label.setStyleSheet(status_style)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add all labels
        for label in labels:
            status_layout.addWidget(label)
        
        status_layout.addStretch(1)
        
        parent_layout.addWidget(status_widget)
        
    def create_all_plots_area(self, parent_layout):
        """Create scroll area for ALL plots stacked vertically"""
        # Create scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                border-radius: 5px;
                min-height: 20px;
            }
        """)
        
        # Create container widget for all plots
        self.plots_container = QWidget()
        self.plots_layout = QVBoxLayout(self.plots_container)
        self.plots_layout.setContentsMargins(5, 5, 5, 5)
        self.plots_layout.setSpacing(2)  # Very small spacing
        
        # Add placeholder label
        placeholder = QLabel("Waiting for MQTT data...")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("font-size: 14px; color: #7f8c8d; padding: 40px;")
        placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.plots_layout.addWidget(placeholder)
        
        self.scroll_area.setWidget(self.plots_container)
        parent_layout.addWidget(self.scroll_area, 1)  # Take all available space
        
    def setup_all_plots(self, num_channels):
        """Setup plots for all channels (regular + tacho) stacked vertically"""
        # Clear existing layout
        while self.plots_layout.count():
            item = self.plots_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Clear plot widgets list
        self.all_plot_widgets.clear()
        
        # Create regular channel plots
        for i in range(num_channels):
            channel_plot = ChannelPlotWidget(i, channel_type="CH")
            self.plots_layout.addWidget(channel_plot)
            self.all_plot_widgets.append(("CH", i, channel_plot))
            
            # Add separator
            if i < num_channels - 1:
                self.add_separator()
        
        # Add separator between regular and tacho channels
        if num_channels > 0:
            self.add_separator(thicker=True)
        
        # Create tacho frequency plot
        tacho_freq_plot = ChannelPlotWidget(0, channel_type="TACHO_F")
        self.plots_layout.addWidget(tacho_freq_plot)
        self.all_plot_widgets.append(("TACHO_F", 0, tacho_freq_plot))
        
        # Add separator between tacho channels
        self.add_separator()
        
        # Create tacho trigger plot
        tacho_trigger_plot = ChannelPlotWidget(0, channel_type="TACHO_T")
        self.plots_layout.addWidget(tacho_trigger_plot)
        self.all_plot_widgets.append(("TACHO_T", 0, tacho_trigger_plot))
        
        # Add stretch at the end
        self.plots_layout.addStretch(1)
        
        # Update window title
        total_channels = num_channels + 2  # +2 for tacho channels
        self.setWindowTitle(f"MQTT Viewer - {num_channels} Channels + 2 Tacho")
        
    def add_separator(self, thicker=False):
        """Add a separator line between plots"""
        separator = QWidget()
        if thicker:
            separator.setFixedHeight(3)
            separator.setStyleSheet("background-color: #95a5a6;")
        else:
            separator.setFixedHeight(1)
            separator.setStyleSheet("background-color: #ecf0f1;")
        self.plots_layout.addWidget(separator)
        
    def on_data_received(self, interleaved_samples, tacho_freq, tacho_trigger, frame_index):
        """Handle new data from MQTT thread"""
        if not self.running:
            return
            
        # Initialize buffers on first message
        if self.sample_rate == 0 and self.mqtt_handler.sample_rate > 0:
            self.initialize_buffers(self.mqtt_handler.sample_rate, 
                                  self.mqtt_handler.num_channels,
                                  self.mqtt_handler.samples_per_channel)
            
            # Setup all plots (regular + tacho)
            self.setup_all_plots(self.num_channels)
        
        # Update buffers if initialized
        if self.sample_rate > 0 and len(self.channel_buffers) > 0:
            self.update_buffers(interleaved_samples, tacho_freq, tacho_trigger, 
                               self.mqtt_handler.samples_per_channel,
                               self.mqtt_handler.num_channels, frame_index)
        
    def initialize_buffers(self, sample_rate, num_channels, samples_per_channel):
        """Initialize data buffers for 1 second window"""
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.samples_per_channel = samples_per_channel
        
        # Calculate buffer size for 1 second
        self.buffer_size = sample_rate
        self.current_buffer_size = min(self.buffer_size, 4096)
        
        # Initialize time array for 1 second window
        self.time_buffer = np.linspace(0, 1, self.current_buffer_size)
        
        # Initialize channel buffers
        self.channel_buffers = []
        for i in range(num_channels):
            self.channel_buffers.append(np.zeros(self.current_buffer_size))
            
        # Initialize tacho buffers
        self.tacho_freq_buffer = np.zeros(self.current_buffer_size)
        self.tacho_trigger_buffer = np.zeros(self.current_buffer_size)
        
        print(f"Initialized: {sample_rate}Hz, {num_channels} channels, buffer: {self.current_buffer_size}")
        
    def update_buffers(self, interleaved_samples, tacho_freq, tacho_trigger, 
                      samples_per_channel, num_channels, frame_index):
        """Update rolling buffers with new data"""
        # Reshape interleaved data to channel-wise
        if num_channels > 0 and len(interleaved_samples) >= samples_per_channel * num_channels:
            try:
                channel_data = interleaved_samples.reshape((samples_per_channel, num_channels))
                
                # Update each channel buffer
                for ch in range(min(num_channels, len(self.channel_buffers))):
                    new_samples = channel_data[:, ch]
                    
                    # Update buffer
                    buffer_len = len(self.channel_buffers[ch])
                    sample_len = len(new_samples)
                    
                    if sample_len >= buffer_len:
                        self.channel_buffers[ch] = new_samples[-buffer_len:]
                    else:
                        self.channel_buffers[ch] = np.concatenate([
                            self.channel_buffers[ch][sample_len:],
                            new_samples
                        ])
            except Exception as e:
                print(f"Error updating channel buffers: {e}")
                return
        
        # Update tacho buffers
        if len(tacho_freq) > 0:
            buffer_len = len(self.tacho_freq_buffer)
            sample_len = len(tacho_freq)
            
            if sample_len >= buffer_len:
                self.tacho_freq_buffer = tacho_freq[-buffer_len:]
            else:
                self.tacho_freq_buffer = np.concatenate([
                    self.tacho_freq_buffer[sample_len:],
                    tacho_freq
                ])
        
        if len(tacho_trigger) > 0:
            buffer_len = len(self.tacho_trigger_buffer)
            sample_len = len(tacho_trigger)
            
            if sample_len >= buffer_len:
                self.tacho_trigger_buffer = tacho_trigger[-buffer_len:]
            else:
                self.tacho_trigger_buffer = np.concatenate([
                    self.tacho_trigger_buffer[sample_len:],
                    tacho_trigger
                ])
        
        self.current_frame_index = frame_index
        
        # Update status labels
        self.lbl_frame.setText(f"Frame: {frame_index}")
        self.lbl_rate.setText(f"Rate: {self.sample_rate} Hz")
        self.lbl_channels.setText(f"Channels: {self.num_channels}")
        
        if self.sample_rate > 0:
            actual_time_window = self.current_buffer_size / self.sample_rate
            self.lbl_window.setText(f"Window: {actual_time_window:.3f} s")
            
    def update_plots(self):
        """Update all plots with current buffer data"""
        if not self.running or self.sample_rate == 0 or len(self.channel_buffers) == 0:
            return
            
        try:
            # Update all plot widgets
            for channel_type, channel_num, plot_widget in self.all_plot_widgets:
                if channel_type == "CH" and channel_num < len(self.channel_buffers):
                    # Regular channel
                    plot_widget.update_plot(self.time_buffer, self.channel_buffers[channel_num])
                elif channel_type == "TACHO_F":
                    # Tacho frequency
                    plot_widget.update_plot(self.time_buffer, self.tacho_freq_buffer)
                elif channel_type == "TACHO_T":
                    # Tacho trigger
                    plot_widget.update_plot(self.time_buffer, self.tacho_trigger_buffer)
            
            # Calculate and display update rate
            self.update_count += 1
            current_time = QTimer.currentTime().msecsSinceStartOfDay() / 1000.0
            
            if self.last_update_time > 0:
                dt = current_time - self.last_update_time
                if dt >= 1.0:  # Update rate every second
                    update_rate = self.update_count / dt
                    self.lbl_update.setText(f"Update: {update_rate:.1f} Hz")
                    self.update_count = 0
                    self.last_update_time = current_time
            else:
                self.last_update_time = current_time
                
        except Exception as e:
            print(f"Error updating plots: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.running = False
        self.timer.stop()
        self.mqtt_handler.stop()
        event.accept()

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    print("\nCtrl+C pressed. Exiting...")
    QApplication.quit()

def main():
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    app = QApplication(sys.argv)
    
    # Enable Ctrl+C handling in Qt
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)
    
    window = MQTTGraphApp()
    window.showMaximized()  # Start maximized
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        window.close()
        app.quit()

if __name__ == "__main__":
    main()