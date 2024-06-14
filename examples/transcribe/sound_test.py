import sounddevice as sd

try:
    devices = sd.query_devices()
    if not devices:
        print("No audio devices found.")
    else:
        print(devices)
except Exception as e:
    print(f"Error: {e}")