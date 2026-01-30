import paho.mqtt.client as mqtt
import struct
import numpy as np
import json

BROKER = "192.168.1.231"
TOPIC = "sarayu/d1/topic1"

# ----- MQTT Callbacks -----
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload
        num_uint16 = len(payload) // 2
        data = np.frombuffer(payload, dtype='<H')  # Little-endian uint16

        # ----- Parse header -----
        header = data[:100]
        frame_index = header[0] + header[1] * 65535
        num_channels = header[2]
        sample_rate = header[3]
        samples_per_channel = header[4]
        num_tacho_channels = header[6]

        # ----- Parse interleaved samples -----
        start = 100
        end = start + samples_per_channel * num_channels
        interleaved = data[start:end]

        # ----- Parse tacho data -----
        start = end
        end = start + samples_per_channel
        tacho_freq = data[start:end]

        start = end
        end = start + samples_per_channel
        tacho_trigger = data[start:end]

        # ----- Convert to JSON-friendly format -----
        json_data = {
            "frame_index": int(frame_index),
            "num_channels": int(num_channels),
            "sample_rate": int(sample_rate),
            "samples_per_channel": int(samples_per_channel),
            "num_tacho_channels": int(num_tacho_channels),
            "interleaved_samples": interleaved[:20].tolist(),  # first 20 for brevity
            "tacho_frequency": tacho_freq[:20].tolist(),
            "tacho_trigger": tacho_trigger[:20].tolist()
        }

        print(json.dumps(json_data, indent=2))
    except Exception as e:
        print("Error parsing message:", e)

# ----- MQTT Client Setup -----
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER)
client.loop_forever()





# import paho.mqtt.client as mqtt
# import struct
# import numpy as np
# import json
# import queue
# import threading

# # ================= CONFIG =================
# BROKER = "192.168.1.231"
# TOPIC = "sarayu/d1/topic1"

# # ================= QUEUE FOR THREADING =================
# msg_queue = queue.Queue()

# # ----- MQTT Callbacks -----
# def on_connect(client, userdata, flags, rc):
#     if rc == 0:
#         print("Connected to MQTT broker")
#         client.subscribe(TOPIC)
#     else:
#         print(f"Connection failed with code {rc}")

# def on_message(client, userdata, msg):
#     # Put payload into queue for processing
#     msg_queue.put(msg.payload)

# # ----- MESSAGE PROCESSING THREAD -----
# def process_messages():
#     while True:
#         payload = msg_queue.get()
#         try:
#             num_uint16 = len(payload) // 2
#             data = np.frombuffer(payload, dtype='<H')  # Little-endian uint16

#             # ----- Parse header -----
#             header = data[:100]
#             frame_index = header[0] + header[1] * 65535
#             num_channels = header[2]
#             sample_rate = header[3]
#             samples_per_channel = header[4]
#             num_tacho_channels = header[6]

#             # ----- Parse interleaved samples -----
#             start = 100
#             end = start + samples_per_channel * num_channels
#             interleaved = data[start:end]

#             # ----- Parse tacho data -----
#             start = end
#             end = start + samples_per_channel
#             tacho_freq = data[start:end]

#             start = end
#             end = start + samples_per_channel
#             tacho_trigger = data[start:end]

#             # ----- Convert to JSON-friendly format (small preview only) -----
#             json_data = {
#                 "frame_index": int(frame_index),
#                 "num_channels": int(num_channels),
#                 "sample_rate": int(sample_rate),
#                 "samples_per_channel": int(samples_per_channel),
#                 "num_tacho_channels": int(num_tacho_channels),
#                 "interleaved_samples_preview": interleaved[:5].tolist(),  # first 5 only
#                 "tacho_frequency_preview": tacho_freq[:5].tolist(),
#                 "tacho_trigger_preview": tacho_trigger[:5].tolist()
#             }

#             print(f"Frame {frame_index} received | Samples per channel: {samples_per_channel}")
#             # Uncomment the next line if you want full JSON output (slower)
#             # print(json.dumps(json_data, indent=2))

#         except Exception as e:
#             print("Error parsing message:", e)

# # ================= MQTT CLIENT SETUP =================
# client = mqtt.Client()
# client.on_connect = on_connect
# client.on_message = on_message

# # ================= START PROCESSING THREAD =================
# threading.Thread(target=process_messages, daemon=True).start()

# # ================= CONNECT AND LOOP =================
# client.connect(BROKER)
# client.loop_forever()
