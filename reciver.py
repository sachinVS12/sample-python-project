# import paho.mqtt.client as mqtt
# import struct
# import numpy as np
# import json
# import time

# BROKER = "192.168.1.231"
# TOPIC = "sarayu/d1/topic1"

# # ----- MQTT Callbacks -----
# def on_connect(client, userdata, flags, rc):
#     print(f"Connected to MQTT broker with result code {rc}")
#     client.subscribe(TOPIC)
#     print(f"Subscribed to topic: {TOPIC}")

# def on_message(client, userdata, msg):
#     try:
#         payload = msg.payload
#         num_uint16 = len(payload) // 2
        
#         # Check if we have enough data for header
#         if num_uint16 < 100:
#             print(f"Warning: Insufficient data. Expected at least 100 uint16 values, got {num_uint16}")
#             return
            
#         data = np.frombuffer(payload, dtype='<H')  # Little-endian uint16

#         # ----- Parse header -----
#         header = data[:100]
        
#         # Correct way to combine two 16-bit values into 32-bit
#         # frame_index = header[0] | (header[1] << 16)  # If header[1] is high word
#         # frame_index = header[0] + (header[1] << 16)  # Alternative
#         frame_index = struct.unpack('<I', header[:2].tobytes())[0]  # Most reliable way
        
#         num_channels = header[2]
#         sample_rate = header[3]
#         samples_per_channel = header[4]
#         num_tacho_channels = header[6]
        
#         # Calculate expected total samples
#         expected_total_samples = 100 + (samples_per_channel * num_channels) + (samples_per_channel * num_tacho_channels)
        
#         if len(data) < expected_total_samples:
#             print(f"Warning: Data length mismatch. Expected {expected_total_samples} samples, got {len(data)}")
#             return

#         # ----- Parse interleaved samples -----
#         start = 100
#         end = start + (samples_per_channel * num_channels)
#         interleaved = data[start:end]

#         # ----- Parse tacho data -----
#         tacho_data = []
#         tacho_start = end
        
#         for i in range(num_tacho_channels):
#             tacho_end = tacho_start + samples_per_channel
#             if tacho_end <= len(data):
#                 tacho_channel_data = data[tacho_start:tacho_end]
#                 tacho_data.append(tacho_channel_data)
#                 tacho_start = tacho_end

#         # Reshape interleaved data if needed
#         if num_channels > 0 and samples_per_channel > 0:
#             try:
#                 # Reshape to [samples_per_channel, num_channels]
#                 reshaped_data = interleaved.reshape((samples_per_channel, num_channels), order='C')
#                 # Transpose to [num_channels, samples_per_channel] if needed
#                 # channel_data = reshaped_data.T
#             except ValueError as e:
#                 print(f"Warning: Could not reshape data: {e}")
#                 reshaped_data = interleaved

#         # ----- Convert to JSON-friendly format -----
#         json_data = {
#             "timestamp": time.time(),
#             "frame_index": int(frame_index),
#             "num_channels": int(num_channels),
#             "sample_rate": int(sample_rate),
#             "samples_per_channel": int(samples_per_channel),
#             "num_tacho_channels": int(num_tacho_channels),
#             "total_samples_received": int(len(data)),
#             "data_preview": {
#                 "interleaved_samples_first_10": interleaved[:10].tolist() if len(interleaved) > 10 else interleaved.tolist(),
#                 "interleaved_samples_last_10": interleaved[-10:].tolist() if len(interleaved) > 10 else [],
#             }
#         }
        
#         # Add tacho data preview if available
#         if tacho_data:
#             for i, tacho_channel in enumerate(tacho_data):
#                 if len(tacho_channel) > 0:
#                     json_data[f"tacho_channel_{i}_preview"] = {
#                         "first_10": tacho_channel[:10].tolist() if len(tacho_channel) > 10 else tacho_channel.tolist(),
#                         "last_10": tacho_channel[-10:].tolist() if len(tacho_channel) > 10 else []
#                     }

#         print(f"\n{'='*50}")
#         print(f"Frame Index: {frame_index}")
#         print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(json_data['timestamp']))}")
#         print(f"Channels: {num_channels}, Samples per channel: {samples_per_channel}")
#         print(f"Sample Rate: {sample_rate} Hz")
#         print(f"Tacho Channels: {num_tacho_channels}")
#         print(f"Total data points received: {len(data)}")
#         print(f"{'='*50}")
        
#         # For debugging: print the full header
#         # print("Header (first 10 values):", header[:10].tolist())
#         # print(f"Header[0]: {header[0]}, Header[1]: {header[1]}")
        
#     except Exception as e:
#         print(f"Error parsing message: {e}")
#         import traceback
#         traceback.print_exc()

# # ----- MQTT Client Setup -----
# def main():
#     client = mqtt.Client()
#     client.on_connect = on_connect
#     client.on_message = on_message
    
#     # Optional: Add reconnection settings
#     client.reconnect_delay_set(min_delay=1, max_delay=120)
    
#     try:
#         print(f"Connecting to MQTT broker at {BROKER}...")
#         client.connect(BROKER, 1883, 60)
#         print("Starting MQTT loop...")
#         client.loop_forever()
#     except KeyboardInterrupt:
#         print("\nDisconnecting from MQTT broker...")
#         client.disconnect()
#     except Exception as e:
#         print(f"Failed to connect to MQTT broker: {e}")

# if __name__ == "__main__":
#     main()



import paho.mqtt.client as mqtt
import struct
import numpy as np
import json
import time

BROKER = "192.168.1.231"
TOPIC = "sarayu/d1/topic1"

# Track frame index for monitoring
last_frame_index = -1
last_received_time = time.time()

# ----- MQTT Callbacks -----
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    if rc == 0:
        client.subscribe(TOPIC)
        print(f"Subscribed to topic: {TOPIC}")
    else:
        print(f"Connection failed with result code {rc}")

def on_message(client, userdata, msg):
    global last_frame_index, last_received_time
    
    try:
        payload = msg.payload
        data = np.frombuffer(payload, dtype='<H')  # Little-endian uint16
        
        # ----- Parse header -----
        # Header is first 100 uint16 values
        if len(data) < 100:
            print(f"Error: Message too short. Expected at least 100 uint16, got {len(data)}")
            return
            
        header = data[:100]
        
        # Frame index: Combine two 16-bit values into 32-bit
        # header[0] = lower 16 bits
        # header[1] = upper 16 bits
        frame_index = int(header[0]) + (int(header[1]) << 16)
        
        num_channels = int(header[2])
        sample_rate = int(header[3])
        samples_per_channel = int(header[4])
        num_tacho_channels = int(header[6])
        
        # Calculate total samples expected
        total_samples = samples_per_channel * num_channels
        total_tacho_samples = samples_per_channel * 2  # Assuming 2 tacho channels as per your code
        
        # Check if we have enough data
        expected_total = 100 + total_samples + total_tacho_samples
        if len(data) < expected_total:
            print(f"Error: Expected {expected_total} uint16, got {len(data)}")
            return
        
        # ----- Parse interleaved samples -----
        start = 100
        end = start + total_samples
        interleaved = data[start:end]
        
        # Reshape if you want channel-wise data
        # channels_data = interleaved.reshape((samples_per_channel, num_channels), order='F')
        
        # ----- Parse tacho data -----
        start = end
        end = start + samples_per_channel
        tacho_freq = data[start:end]
        
        start = end
        end = start + samples_per_channel
        tacho_trigger = data[start:end]
        
        # ----- Calculate timing -----
        current_time = time.time()
        time_since_last = current_time - last_received_time
        last_received_time = current_time
        
        # Check if frame index is sequential
        frame_gap = frame_index - last_frame_index
        if last_frame_index != -1 and frame_gap != 1:
            print(f"Warning: Frame gap detected! Expected {last_frame_index + 1}, got {frame_index}")
        
        last_frame_index = frame_index
        
        # ----- Prepare JSON data -----
        # Only include first few samples for brevity
        sample_limit = min(20, samples_per_channel)
        
        json_data = {
            "frame_index": frame_index,
            "num_channels": num_channels,
            "sample_rate": sample_rate,
            "samples_per_channel": samples_per_channel,
            "num_tacho_channels": num_tacho_channels,
            "time_since_last_frame": round(time_since_last, 3),
            "frame_gap": frame_gap if last_frame_index != -1 else 0,
            "data_shape": {
                "total_samples": total_samples,
                "interleaved_samples": len(interleaved),
                "tacho_samples": len(tacho_freq)
            },
            "interleaved_samples_first_channel": interleaved[:sample_limit].tolist(),
            "tacho_frequency": tacho_freq[:sample_limit].tolist(),
            "tacho_trigger": tacho_trigger[:sample_limit].tolist()
        }
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"Frame Index: {frame_index}")
        print(f"Channels: {num_channels}, Samples per channel: {samples_per_channel}")
        print(f"Sample Rate: {sample_rate} Hz")
        print(f"Time since last: {time_since_last:.3f}s")
        print(f"Frame gap: {frame_gap}")
        print(f"{'='*50}")
        
        # Print full JSON for debugging (uncomment if needed)
        # print(json.dumps(json_data, indent=2))
        
    except Exception as e:
        print(f"Error parsing message: {e}")
        import traceback
        traceback.print_exc()

# ----- MQTT Client Setup -----
def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Optional: Add reconnection logic
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    print(f"Connecting to MQTT broker at {BROKER}...")
    
    try:
        client.connect(BROKER, 1883, 60)
        print("Starting MQTT loop...")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nDisconnecting from MQTT broker...")
        client.disconnect()
    except Exception as e:
        print(f"Failed to connect to broker: {e}")

if __name__ == "__main__":
    main()