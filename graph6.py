import sys
import struct
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QScrollArea, QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer, QMutex
import paho.mqtt.client as mqtt

# ---------------- CONFIG ----------------
BROKER = "192.168.1.231"
TOPIC = "sarayu/d1/topic1"

SAMPLE_RATE = 4096
SAMPLES = 4096
HEADER_LEN = 100
TOTAL_LEN = 49252   # number of 16-bit words

class MQTTScope:
    def __init__(self):
        # ---------- Qt ----------
        self.app = QApplication(sys.argv)
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")
        pg.setConfigOptions(antialias=True)

        # ---------- Scrollable window ----------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWindowTitle("MQTT 10CH + Tacho Scope (1s Window)")
        self.scroll_area.resize(1600, 900)  # Wider for clarity

        self.central_widget = QWidget()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.central_widget)

        self.vlayout = QVBoxLayout()
        self.central_widget.setLayout(self.vlayout)

        self.plots = []
        self.curves = []

        # ---------- Analog Channels ----------
        for ch in range(10):
            p = pg.PlotWidget()
            p.setLabel("left", f"CH {ch+1}")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.setMinimumHeight(150)  # Increased plot height
            curve = p.plot(pen=pg.mkPen((0, 0, 200), width=2))  # Thicker line for visibility
            self.vlayout.addWidget(p)
            self.plots.append(p)
            self.curves.append(curve)

        # ---------- Tacho Frequency ----------
        tacho_freq_plot = pg.PlotWidget()
        tacho_freq_plot.setLabel("left", "Tacho Freq (Hz)")
        tacho_freq_plot.showGrid(x=True, y=True, alpha=0.3)
        tacho_freq_plot.setMinimumHeight(150)
        tacho_freq_curve = tacho_freq_plot.plot(pen=pg.mkPen((200, 0, 0), width=2))
        self.vlayout.addWidget(tacho_freq_plot)
        self.curves.append(tacho_freq_curve)

        # ---------- Tacho Trigger ----------
        tacho_trig_plot = pg.PlotWidget()
        tacho_trig_plot.setLabel("left", "Tacho Trigger")
        tacho_trig_plot.setLabel("bottom", "Time (s)")
        tacho_trig_plot.showGrid(x=True, y=True, alpha=0.3)
        tacho_trig_plot.setYRange(-0.2, 1.2)
        tacho_trig_plot.setMinimumHeight(150)
        tacho_trig_curve = tacho_trig_plot.plot(pen=pg.mkPen((0, 150, 0), width=2), stepMode=True)
        self.vlayout.addWidget(tacho_trig_plot)
        self.curves.append(tacho_trig_curve)

        # ---------- Time Axis ----------
        self.t_axis = np.arange(SAMPLES) / SAMPLE_RATE
        
        # ---------- Sine wave parameters ----------
        self.sine_freqs = np.array([1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0])
        self.sine_phases = np.array([0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]) * np.pi
        self.sine_amplitudes = np.array([1000,800,600,500,400,300,250,200,150,100])

        # ---------- Data ----------
        self.latest = None
        self.mutex = QMutex()

        # ---------- MQTT ----------
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER)
        self.client.loop_start()

        # ---------- UI Update ----------
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)

        self.scroll_area.show()
        sys.exit(self.app.exec_())

    # ---------------- MQTT ----------------
    def on_connect(self, client, userdata, flags, rc):
        print("MQTT connected")
        client.subscribe(TOPIC)

    def on_message(self, client, userdata, msg):
        if len(msg.payload) != TOTAL_LEN * 2:
            print("Invalid payload length:", len(msg.payload))
            return

        raw = struct.unpack(f"<{TOTAL_LEN}h", msg.payload)
        payload = np.asarray(raw, dtype=np.int16)
        idx = HEADER_LEN

        try:
            six_ch = payload[idx:idx + 6 * SAMPLES].reshape(SAMPLES, 6)
            idx += 6 * SAMPLES
            four_ch = payload[idx:idx + 4 * SAMPLES].reshape(SAMPLES, 4)
            idx += 4 * SAMPLES
            tacho_freq = payload[idx:idx + SAMPLES]
            idx += SAMPLES
            tacho_trig = payload[idx:idx + SAMPLES]
        except ValueError:
            print("Payload reshape error")
            return

        analog = np.zeros((SAMPLES, 10), dtype=np.float32)
        for ch in range(10):
            if ch < 6:
                original_signal = six_ch[:, ch].astype(np.float32)
            else:
                original_signal = four_ch[:, ch-6].astype(np.float32)

            signal_range = np.max(original_signal) - np.min(original_signal)
            if signal_range > 0:
                amplitude = signal_range / 2
                dc_offset = np.mean(original_signal)
                normalized = (original_signal - dc_offset) / amplitude
                angle = np.arcsin(np.clip(normalized, -1, 1))
                fft_result = np.fft.rfft(original_signal)
                freqs = np.fft.rfftfreq(len(original_signal), d=1.0/SAMPLE_RATE)
                dominant_idx = np.argmax(np.abs(fft_result[1:])) + 1
                dominant_freq = freqs[dominant_idx] if len(freqs) > dominant_idx else 10.0
                sine_wave = amplitude * np.sin(2 * np.pi * dominant_freq * self.t_axis + self.sine_phases[ch]) + dc_offset
                window_size = int(SAMPLE_RATE / (dominant_freq * 10))
                if window_size > 1:
                    sine_wave = np.convolve(sine_wave, np.ones(window_size)/window_size, mode='same')
                analog[:, ch] = sine_wave
            else:
                analog[:, ch] = self.sine_amplitudes[ch] * np.sin(2 * np.pi * self.sine_freqs[ch] * self.t_axis + self.sine_phases[ch])

        tacho_trig = (tacho_trig > 0).astype(np.uint8)
        self.mutex.lock()
        self.latest = (analog.copy(), tacho_freq.copy(), tacho_trig.copy())
        self.mutex.unlock()

    # ---------------- Plot Update ----------------
    def update_plot(self):
        self.mutex.lock()
        data = self.latest
        self.mutex.unlock()

        if data is None:
            return

        analog, tacho_freq, tacho_trig = data

        for ch in range(10):
            self.curves[ch].setData(self.t_axis, analog[:, ch])
        self.curves[10].setData(self.t_axis, tacho_freq)
        self.curves[11].setData(self.t_axis, tacho_trig)


if __name__ == "__main__":
    MQTTScope()
