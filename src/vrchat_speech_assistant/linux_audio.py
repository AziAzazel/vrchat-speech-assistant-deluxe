"""PipeWire/PulseAudio routing without changing system defaults or using root."""
import json
import shutil
import subprocess
from PySide6 import QtWidgets
from vrchat_speech_assistant.platform_support import external_process_env

SINK = 'vrcsa_deluxe'
SOURCE = 'vrcsa_deluxe_mic'
DESCRIPTION = 'VRChat_Speech_Deluxe'


def pulse(*args):
    if not shutil.which('pactl'):
        raise RuntimeError('pactl is missing. Install PulseAudio utilities (pulseaudio-utils), then reopen this dialog.')
    result = subprocess.run(['pactl', *args], capture_output=True, text=True, timeout=5,
                            env=external_process_env())
    if result.returncode:
        raise RuntimeError('Cannot contact the user PipeWire/PulseAudio server, or the requested module is unavailable.')
    return result.stdout.strip()


class VirtualMicrophone:
    def __init__(self):
        self.owned = []

    def create(self):
        sinks = json.loads(pulse('-f', 'json', 'list', 'sinks'))
        sources = json.loads(pulse('-f', 'json', 'list', 'sources'))
        if any(item.get('name') == SINK for item in sinks):
            if any(item.get('name') == SOURCE for item in sources):
                return  # Reuse a previous session's route; do not claim ownership.
            raise RuntimeError('The virtual sink name is already in use without its microphone. Remove that route manually first.')
        if any(item.get('name') == SOURCE for item in sources):
            raise RuntimeError('The virtual microphone name is already in use.')
        created = []
        try:
            sink_args = f'sink_name={SINK} sink_properties=device.description={DESCRIPTION}'
            index = pulse('load-module', 'module-null-sink', sink_args)
            created.append((index, 'module-null-sink', sink_args))
            source_args = f'master={SINK}.monitor source_name={SOURCE} source_properties=device.description={DESCRIPTION}_Microphone'
            index = pulse('load-module', 'module-remap-source', source_args)
            created.append((index, 'module-remap-source', source_args))
        except Exception:
            self.owned.extend(created)
            self.remove()
            raise
        self.owned.extend(created)

    def remove(self):
        # Older pactl JSON omits module indices. The stable short format includes
        # ID, name and arguments on both PulseAudio and PipeWire-Pulse.
        modules = {}
        for line in pulse('list', 'short', 'modules').splitlines():
            fields = line.split('\t')
            if len(fields) >= 3 and fields[0].isdigit():
                modules[fields[0]] = {'name': fields[1], 'argument': fields[2]}
        for index, name, argument in reversed(self.owned):
            module = modules.get(index)
            if module and module.get('name') == name and module.get('argument') == argument:
                pulse('unload-module', index)
        self.owned.clear()


class LinuxAudioDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Linux audio routing / virtual microphone')
        self.resize(620, 350)
        self.window = parent
        if parent.linux_virtual_mic is None:
            parent.linux_virtual_mic = VirtualMicrophone()
        layout = QtWidgets.QVBoxLayout(self)
        note = QtWidgets.QLabel(
            'Create a virtual output and microphone in your current PipeWire/PulseAudio session. '
            'Choose “VRChat_Speech_Deluxe” as Speech output, and “VRChat_Speech_Deluxe_Microphone” '
            'as the VRChat microphone. Keep your real microphone as this app’s recognition input. '
            'Use pavucontrol or qpwgraph if a client needs per-stream routing. '
            'No system default device is changed. The route lasts until removed or you log out.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.auto = QtWidgets.QCheckBox('Ensure this virtual microphone exists when starting Deluxe')
        self.auto.setChecked(parent.config['LINUX_AUDIO'].getboolean('autostart'))
        self.auto.toggled.connect(self.save)
        layout.addWidget(self.auto)
        self.status = QtWidgets.QLabel('Ready. pactl and a running user audio server are required.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        for title, callback in [('Create / reuse virtual microphone', self.create),
                                ('Remove route created by this instance', self.remove)]:
            button = QtWidgets.QPushButton(title)
            button.clicked.connect(callback)
            layout.addWidget(button)
        close = QtWidgets.QPushButton('Close')
        close.clicked.connect(self.accept)
        layout.addWidget(close)

    def save(self):
        self.window.config['LINUX_AUDIO']['autostart'] = str(self.auto.isChecked())
        self.window.save_config()

    def create(self):
        try:
            self.window.linux_virtual_mic.create()
            self.status.setText('Route ready. Refreshing devices; select the virtual output in Speech settings and its microphone in VRChat.')
            self.window.refresh_devices()
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
            self.status.setText(str(error) if isinstance(error, RuntimeError) else 'Could not configure audio routing. Check the user audio server.')

    def remove(self):
        try:
            self.window.linux_virtual_mic.remove()
            self.status.setText('Removed only modules created by this instance. Reused routes are left in place.')
            self.window.refresh_devices()
        except Exception:
            self.status.setText('Could not remove the route. Check it in your audio controls.')
