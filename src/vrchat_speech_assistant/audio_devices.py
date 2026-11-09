"""Fresh PortAudio enumeration so unplugged/reconnected devices are discovered."""


def get_devices(device_type):
    import pyaudio
    context = pyaudio.PyAudio()
    try:
        preferred = pyaudio.paMME if device_type == "input" else pyaudio.paWASAPI
        try:
            api = context.get_host_api_info_by_type(preferred)["index"]
        except OSError:
            api = None
        channel = "maxInputChannels" if device_type == "input" else "maxOutputChannels"
        devices = [context.get_device_info_by_index(i) for i in range(context.get_device_count())]
        devices = [d for d in devices if d.get(channel, 0) > 0 and "Microsoft Sound Mapper" not in d["name"]]
        matching = [d for d in devices if d.get("hostApi") == api]
        selected = matching or devices
        return sorted({d["name"]: d for d in selected}.values(), key=lambda d: d["name"])
    finally:
        context.terminate()
