import struct
import sys
import numpy as np
from collections import deque

import paho.mqtt.client as mqtt
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

# ---------------- CONFIG ----------------
BROKER = "192.168.1.231"
TOPIC = "sarayu/d1/topic1"

SAMPLE_RATE = 4096
SAMPLES_PER_FRAME = 4096
NUM_CHANNELS = 10
HEADER_LEN = 100

WINDOW_SECONDS = 1
WINDOW_SAMPLES = SAMPLE_RATE * WINDOW_SECONDS
# ---------------------------------------

# Rolling buffers (1 second per channel)
buffers = [
    deque(maxlen=WINDOW_SAMPLES)
    for _ in range(NUM_CHANNELS)
]

time_axis = np.arange(WINDOW_SAMPLES) / SAMPLE_RATE

# -------------- QT APP -----------------
app = QtWidgets.QApplication(sys.argv)

# White background and black axes globally
pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")

# Use GraphicsLayoutWidget
win = pg.GraphicsLayoutWidget(
    title="1-Second Window – 10 Channels"
)
win.resize(1800, 1200)  # larger window
win.show()

plots = []
curves = []

# Add 10 stacked plots
for ch in range(NUM_CHANNELS):
    p = win.addPlot(row=ch, col=0)
    p.setLabel("left", f"CH{ch}")
    p.setYRange(0, 65535)
    p.showGrid(x=True, y=True, alpha=0.3)

    # Hide bottom axis for all but last
    if ch < NUM_CHANNELS - 1:
        p.hideAxis("bottom")
    else:
        p.setLabel("bottom", "Time", units="s")

    curve = p.plot(
        time_axis,
        np.zeros(WINDOW_SAMPLES),
        pen=pg.mkPen(color=(0, 0, 255), width=1)
    )

    plots.append(p)
    curves.append(curve)

# -------------- MQTT -------------------
def on_message(client, userdata, msg):
    payload = msg.payload

    # Decode uint16
    values = struct.unpack(f"<{len(payload)//2}H", payload)

    # Skip header
    start = HEADER_LEN
    end = start + SAMPLES_PER_FRAME * NUM_CHANNELS
    signal_data = values[start:end]

    # De-interleave (sample-major)
    frame_channels = [[] for _ in range(NUM_CHANNELS)]

    for i in range(SAMPLES_PER_FRAME):
        base = i * NUM_CHANNELS
        for ch in range(NUM_CHANNELS):
            frame_channels[ch].append(signal_data[base + ch])

    # Append to rolling buffers
    for ch in range(NUM_CHANNELS):
        buffers[ch].extend(frame_channels[ch])

# Modern callback API
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.connect(BROKER)
client.subscribe(TOPIC)
client.loop_start()

# ----------- GUI UPDATE TIMER ----------
def update_plots():
    if len(buffers[0]) < WINDOW_SAMPLES:
        return

    for ch in range(NUM_CHANNELS):
        curves[ch].setData(time_axis, np.array(buffers[ch]))

timer = QtCore.QTimer()
timer.timeout.connect(update_plots)
timer.start(30)  # ~33 FPS

print("Receiving data… Close window to exit.")
sys.exit(app.exec_())
