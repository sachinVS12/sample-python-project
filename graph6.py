import sys
import struct
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
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

        self.win = pg.GraphicsLayoutWidget(
            title="MQTT 10CH + Tacho Scope (1s Window)"
        )
        self.win.resize(1400, 1100)
        self.win.show()

        self.plots = []
        self.curves = []

        # ---------- Analog Channels ----------
        for ch in range(10):
            p = self.win.addPlot(row=ch, col=0)
            p.setLabel("left", f"CH {ch+1}")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.enableAutoRange(y=True)
            p.setMinimumHeight(80)

            if ch > 0:
                p.setXLink(self.plots[0])

            curve = p.plot(pen=pg.mkPen((0, 0, 200), width=1))
            self.plots.append(p)
            self.curves.append(curve)

        # ---------- Tacho Frequency ----------
        tacho_freq_plot = self.win.addPlot(row=10, col=0)
        tacho_freq_plot.setLabel("left", "Tacho Freq (Hz)")
        tacho_freq_plot.showGrid(x=True, y=True, alpha=0.3)
        tacho_freq_plot.setMinimumHeight(80)
        tacho_freq_plot.setXLink(self.plots[0])

        tacho_freq_curve = tacho_freq_plot.plot(
            pen=pg.mkPen((200, 0, 0), width=2)
        )

        # ---------- Tacho Trigger ----------
        tacho_trig_plot = self.win.addPlot(row=11, col=0)
        tacho_trig_plot.setLabel("left", "Tacho Trigger")
        tacho_trig_plot.setLabel("bottom", "Time (s)")
        tacho_trig_plot.showGrid(x=True, y=True, alpha=0.3)
        tacho_trig_plot.setYRange(-0.2, 1.2)
        tacho_trig_plot.setMinimumHeight(80)
        tacho_trig_plot.setXLink(self.plots[0])

        tacho_trig_curve = tacho_trig_plot.plot(
            pen=pg.mkPen((0, 150, 0), width=2),
            stepMode=True
        )

        self.curves.extend([tacho_freq_curve, tacho_trig_curve])

        # ---------- Time Axis ----------
        self.t_axis = np.arange(SAMPLES) / SAMPLE_RATE
        
        # ---------- Sine wave parameters ----------
        # Each channel will have different frequency and phase for variety
        self.sine_freqs = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])  # Hz
        self.sine_phases = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]) * np.pi  # radians
        self.sine_amplitudes = np.array([1000, 800, 600, 500, 400, 300, 250, 200, 150, 100])  # amplitude scaling

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

        sys.exit(self.app.exec_())

    # ---------------- MQTT ----------------
    def on_connect(self, client, userdata, flags, rc):
        print("MQTT connected")
        client.subscribe(TOPIC)

    def on_message(self, client, userdata, msg):
        if len(msg.payload) != TOTAL_LEN * 2:
            print("Invalid payload length:", len(msg.payload))
            return

        # SIGNED 16-bit
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

        # Create sine waves from the original data for channels 1-10
        analog = np.zeros((SAMPLES, 10), dtype=np.float32)
        
        # Convert each channel's square wave to sine wave using the original data as phase reference
        for ch in range(10):
            if ch < 6:
                # First 6 channels from six_ch
                channel_data = six_ch[:, ch]
            else:
                # Next 4 channels from four_ch
                channel_data = four_ch[:, ch-6]
            
            # Extract amplitude and DC offset from the original signal
            original_signal = channel_data.astype(np.float32)
            
            # Calculate amplitude (peak-to-peak / 2)
            signal_range = np.max(original_signal) - np.min(original_signal)
            if signal_range > 0:
                amplitude = signal_range / 2
                dc_offset = np.mean(original_signal)
                
                # Normalize to [-1, 1] range
                normalized = (original_signal - dc_offset) / amplitude
                
                # Create sine wave with same frequency content
                # Use arctan2 to estimate phase from square wave
                # This converts square edges to smooth sine transitions
                angle = np.arcsin(np.clip(normalized, -1, 1))
                
                # Generate sine wave with estimated frequency
                # Use FFT to find dominant frequency
                fft_result = np.fft.rfft(original_signal)
                freqs = np.fft.rfftfreq(len(original_signal), d=1.0/SAMPLE_RATE)
                dominant_idx = np.argmax(np.abs(fft_result[1:])) + 1  # Skip DC
                dominant_freq = freqs[dominant_idx] if len(freqs) > dominant_idx else 10.0
                
                # Generate clean sine wave
                sine_wave = amplitude * np.sin(2 * np.pi * dominant_freq * self.t_axis + self.sine_phases[ch]) + dc_offset
                
                # Smooth the transition using a moving average for better sine appearance
                window_size = int(SAMPLE_RATE / (dominant_freq * 10))  # Adaptive window
                if window_size > 1:
                    sine_wave = np.convolve(sine_wave, np.ones(window_size)/window_size, mode='same')
                
                analog[:, ch] = sine_wave
            else:
                # If no signal variation, create default sine wave
                analog[:, ch] = self.sine_amplitudes[ch] * np.sin(
                    2 * np.pi * self.sine_freqs[ch] * self.t_axis + self.sine_phases[ch]
                )

        # Normalize trigger to 0 / 1
        tacho_trig = (tacho_trig > 0).astype(np.uint8)

        self.mutex.lock()
        self.latest = (
            analog.copy(),
            tacho_freq.copy(),
            tacho_trig.copy()
        )
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