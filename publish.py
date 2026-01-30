import math
import struct
import paho.mqtt.publish as publish
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtWidgets import QApplication
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class MQTTPublisher(QObject):
    def __init__(self, broker, topics):
        super().__init__()
        self.broker = broker
        self.topics = topics if isinstance(topics, list) else [topics]

        # Fixed frequencies (NO SWEEP)
        self.signal_frequency = 20
        self.tacho_fixed_freq = 10

        # Signal parameters
        self.amplitude = 1.0
        self.offset = 32768
        self.sample_rate = 4096
        self.samples_per_channel = 4096
        self.time_per_message = 0.5
        self.current_time = 0.0

        # Channels
        self.num_signal_channels = 10   # 6 + 4
        self.num_tacho_channels = 2

        # Timer → 0.5 s
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_message)
        self.timer.start(500)

        logging.info("MQTT Publisher running (NO SWEEP)")


    def publish_message(self):
        try:
            # ----- Header frame: always 10 10 -----
            header_frame = 10

            amplitude_scaled = (self.amplitude * 0.5) / (3.3 / 65535)

            # ----- Generate base sine (FIXED frequency) -----
            base_data = []
            for i in range(self.samples_per_channel):
                t = self.current_time + (i / self.sample_rate)
                value = self.offset + amplitude_scaled * math.sin(
                    2 * math.pi * self.signal_frequency * t
                )
                base_data.append(int(round(value)))

            self.current_time += self.time_per_message

            # ----- Interleave 6 + 4 -----
            interleaved = []
            for i in range(self.samples_per_channel):
                for _ in range(6):
                    interleaved.append(base_data[i])
                for _ in range(4):
                    interleaved.append(base_data[i])

            # ----- Tacho channels (FIXED frequency) -----
            tacho_freq = [self.tacho_fixed_freq] * self.samples_per_channel
            tacho_trigger = [0] * self.samples_per_channel

            triggers = self.tacho_fixed_freq
            if triggers > 0:
                step = self.samples_per_channel // triggers
                for i in range(triggers):
                    idx = i * step
                    if idx < self.samples_per_channel:
                        tacho_trigger[idx] = 1

            # ----- Header -----
            header = [
                header_frame,
                header_frame,
                self.num_signal_channels,
                self.sample_rate,
                4096,
                self.samples_per_channel,
                self.num_tacho_channels,
                0, 0, 0
            ]

            while len(header) < 100:
                header.append(0)

            # ----- Build message -----
            message = (
                header +
                interleaved +
                tacho_freq +
                tacho_trigger
            )

            expected_len = (
                100 +
                self.samples_per_channel * self.num_signal_channels +
                self.samples_per_channel * self.num_tacho_channels
            )

            if len(message) != expected_len:
                logging.error(f"Length mismatch {len(message)} != {expected_len}")
                return

            # ----- Pack & publish -----
            binary = struct.pack(f"<{len(message)}H", *message)

            for topic in self.topics:
                publish.single(topic, binary, hostname=self.broker, qos=1)

            logging.info(
                f"Published header=10 10, "
                f"signal_freq={self.signal_frequency} Hz, "
                f"tacho_freq={self.tacho_fixed_freq}"
            )

        except Exception as e:
            logging.error(f"Publish error: {e}")


if __name__ == "__main__":
    app = QApplication([])

    broker = "192.168.1.231"
    topics = ["sarayu/d1/topic1"]

    publisher = MQTTPublisher(broker, topics)
    app.exec_()
