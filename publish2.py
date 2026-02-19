# import math
# import struct
# import paho.mqtt.publish as publish
# from PyQt5.QtCore import QTimer, QObject
# from PyQt5.QtWidgets import QApplication
# import logging

# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s - %(levelname)s - %(message)s')


# class MQTTPublisher(QObject):
#     def __init__(self, broker, topics):
#         super().__init__()

#         self.broker = broker
#         self.topics = topics if isinstance(topics, list) else [topics]

#         # Frequencies
#         self.signal_frequency = 5
#         self.tacho_fixed_freq = 10

#         # Signal parameters
#         self.amplitude = 1.0
#         self.offset = 32768
#         self.sample_rate = 4096
#         self.samples = 4096
#         self.time_per_message = 0.5
#         self.current_time = 0.0

#         # Channels
#         self.num_6ch = 6
#         self.num_4ch = 4
#         self.num_tacho_channels = 2

#         # Timer (0.5 s)
#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.publish_message)
#         self.timer.start(500)

#         logging.info("MQTT Publisher started (FIXED PAYLOAD MAP)")


#     def publish_message(self):
#         try:
#             HEADER_LEN = 100
#             TOTAL_LEN = 49252

#             # ---------------- HEADER (0–99) ----------------
#             header = [
#                 10, 10,                   # frame
#                 self.num_6ch + self.num_4ch,
#                 self.sample_rate,
#                 4096,
#                 self.samples,
#                 self.num_tacho_channels,
#                 0, 0, 0
#             ]
#             header += [0] * (HEADER_LEN - len(header))

#             # ---------------- BASE SINE ----------------
#             amplitude_scaled = (self.amplitude * 0.5) / (3.3 / 65535)

#             base = []
#             for i in range(self.samples):
#                 t = self.current_time + i / self.sample_rate
#                 val = self.offset + amplitude_scaled * math.sin(
#                     2 * math.pi * self.signal_frequency * t
#                 )
#                 base.append(int(round(val)))

#             self.current_time += self.time_per_message

#             # ---------------- 6-CHANNEL INTERLEAVED ----------------
#             data_6ch = []
#             for s in base:
#                 data_6ch.extend([s] * self.num_6ch)

#             # indices 100 – 24675
#             assert len(data_6ch) == 24576

#             # ---------------- 4-CHANNEL INTERLEAVED ----------------
#             data_4ch = []
#             for s in base:
#                 data_4ch.extend([s] * self.num_4ch)

#             # indices 24676 – 41059
#             assert len(data_4ch) == 16384

#             # ---------------- TACHO FREQUENCY ----------------
#             tacho_freq = [self.tacho_fixed_freq] * self.samples
#             # indices 41060 – 45155

#             # ---------------- TACHO TRIGGER ----------------
#             tacho_trigger = [0] * self.samples
#             step = self.samples // self.tacho_fixed_freq

#             for i in range(self.tacho_fixed_freq):
#                 idx = i * step
#                 if idx < self.samples:
#                     tacho_trigger[idx] = 1

#             # indices 45156 – 49251

#             # ---------------- BUILD MESSAGE ----------------
#             message = (
#                 header +
#                 data_6ch +
#                 data_4ch +
#                 tacho_freq +
#                 tacho_trigger
#             )

#             if len(message) != TOTAL_LEN:
#                 logging.error(f"Payload length error: {len(message)} != {TOTAL_LEN}")
#                 return

#             # ---------------- PACK & PUBLISH ----------------
#             binary = struct.pack(f"<{TOTAL_LEN}H", *message)

#             for topic in self.topics:
#                 publish.single(topic, binary, hostname=self.broker, qos=1)

#             logging.info(
#                 f"Published OK | "
#                 f"Signal={self.signal_frequency}Hz | "
#                 f"Tacho={self.tacho_fixed_freq}Hz | "
#                 f"Len={TOTAL_LEN}"
#             )

#         except Exception as e:
#             logging.error(f"Publish error: {e}")


# if __name__ == "__main__":
#     app = QApplication([])

#     broker = "192.168.1.231"
#     topics = ["sarayu/d1/topic1"]

#     publisher = MQTTPublisher(broker, topics)
#     app.exec_()


#sample code
import math
import struct
import paho.mqtt.publish as publish
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtWidgets import QApplication
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class MQTTPublisher(QObject):
    def __init__(self, broker, topics): 
        super().__init__()

        self.broker = broker
        self.topics = topics if isinstance(topics, list) else [topics]

        # Frequencies
        self.signal_frequency = 10
        self.tacho_fixed_freq = 10

        # Signal parameters
        self.amplitude = 1.0
        self.offset = 32768
        self.sample_rate = 4096
        self.samples = 4096
        self.time_per_message = 0.5
        self.current_time = 0.0

        # Channels
        self.num_6ch = 6
        self.num_4ch = 4
        self.num_tacho_channels = 2

        # Header toggle (1,1) <-> (2,2)
        self.header_toggle = True

        # Timer (0.5 s)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_message)
        self.timer.start(500)

        logging.info("MQTT Publisher started (HEADER TOGGLE MODE)")


    def publish_message(self):
        try:
            HEADER_LEN = 100
            TOTAL_LEN = 49252

            # ---------------- HEADER (0–99) ----------------
            if self.header_toggle:
                frame_a, frame_b = 1, 1
            else:
                frame_a, frame_b = 2, 2

            self.header_toggle = not self.header_toggle

            header = [
                frame_a, frame_b,
                self.num_6ch + self.num_4ch,
                self.sample_rate,
                4096,
                self.samples,
                self.num_tacho_channels,
                0, 0, 0
            ]
            header += [0] * (HEADER_LEN - len(header))

            # ---------------- BASE SINE ----------------
            amplitude_scaled = (self.amplitude * 0.5) / (3.3 / 65535)

            base = []
            for i in range(self.samples):
                t = self.current_time + i / self.sample_rate
                val = self.offset + amplitude_scaled * math.sin(
                    2 * math.pi * self.signal_frequency * t
                )
                base.append(int(round(val)))

            self.current_time += self.time_per_message

            # ---------------- 6-CHANNEL INTERLEAVED ----------------
            data_6ch = []
            for s in base:
                data_6ch.extend([s] * self.num_6ch)

            # ---------------- 4-CHANNEL INTERLEAVED ----------------
            data_4ch = []
            for s in base:
                data_4ch.extend([s] * self.num_4ch)

            # ---------------- TACHO FREQUENCY ----------------
            tacho_freq = [self.tacho_fixed_freq] * self.samples

            # ---------------- TACHO TRIGGER ----------------
            tacho_trigger = [0] * self.samples
            step = self.samples // self.tacho_fixed_freq

            for i in range(self.tacho_fixed_freq):
                idx = i * step
                if idx < self.samples:
                    tacho_trigger[idx] = 1

            # ---------------- BUILD MESSAGE ----------------
            message = (
                header +
                data_6ch +
                data_4ch +
                tacho_freq +
                tacho_trigger
            )

            if len(message) != TOTAL_LEN:
                logging.error(f"Payload length error: {len(message)} != {TOTAL_LEN}")
                return

            # ---------------- PACK & PUBLISH ----------------
            binary = struct.pack(f"<{TOTAL_LEN}H", *message)

            for topic in self.topics:
                publish.single(topic, binary, hostname=self.broker, qos=1)

            logging.info(
                f"Published OK | "
                f"Header=({frame_a},{frame_b}) | "
                f"Signal={self.signal_frequency}Hz | "
                f"Tacho={self.tacho_fixed_freq}Hz"
            )

        except Exception as e:
            logging.error(f"Publish error: {e}")


if __name__ == "__main__":
    app = QApplication([])

    broker = "192.168.1.231"
    topics = ["sarayu/d1/topic1"]

    publisher = MQTTPublisher(broker, topics)
    app.exec_()
