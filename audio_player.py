import atexit
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading

_active_players = []


def _cleanup_all():
    for player in list(_active_players):
        player.stop()


atexit.register(_cleanup_all)


if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes

    CTRL_C_EVENT = 0
    CTRL_BREAK_EVENT = 1
    CTRL_CLOSE_EVENT = 2
    CTRL_LOGOFF_EVENT = 5
    CTRL_SHUTDOWN_EVENT = 6

    HANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    def _console_ctrl_handler(event):
        if event in (CTRL_C_EVENT, CTRL_BREAK_EVENT, CTRL_CLOSE_EVENT,
                     CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT):
            _cleanup_all()
        return False

    _handler_ref = HANDLER_ROUTINE(_console_ctrl_handler)
    ctypes.windll.kernel32.SetConsoleCtrlHandler(_handler_ref, True)

else:
    import signal

    def _signal_cleanup(signum, frame):
        _cleanup_all()
        sys.exit(0)

    for _sig in (signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(_sig, _signal_cleanup)
        except (ValueError, OSError):
            pass


class AudioPlayer:
    def __init__(self, video_path: str):
        self.video_path = video_path
        self._proc = None
        self._tmp_wav = None

        if shutil.which("ffmpeg") is None or shutil.which("ffplay") is None:
            raise EnvironmentError(
                "ffmpeg/ffplay not found on PATH. Install ffmpeg and try again."
            )

    def _extract_audio(self) -> str:
        fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        command = [
            "ffmpeg", "-y",
            "-i", self.video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100", "-ac", "2",
            wav_path,
        ]
        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        self._tmp_wav = wav_path
        return wav_path

    def play_async(self):
        wav_path = self._extract_audio()

        _active_players.append(self)

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        self._proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", wav_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        def _wait_for_exit():
            self._proc.wait()

        thread = threading.Thread(target=_wait_for_exit, daemon=True)
        thread.start()
        return thread

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        if self._tmp_wav and os.path.exists(self._tmp_wav):
            try:
                os.remove(self._tmp_wav)
            except OSError:
                pass
        if self in _active_players:
            _active_players.remove(self)