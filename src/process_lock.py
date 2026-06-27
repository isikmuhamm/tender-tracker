import os
import sys
import ctypes
from src.database import get_data_path

def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

class ProcessLock:
    """Prosesler arası (Dashboard ve CLI Daemon) çakışmayı önleyen dosya kilidi."""
    def __init__(self, name="scan"):
        self.lock_path = get_data_path(f"tender_tracker_{name}.lock")

    def acquire(self) -> bool:
        """Kilidi almaya çalışır. Başarılı ise True döner."""
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r") as f:
                    pid = int(f.read().strip())
                if not is_process_running(pid):
                    os.remove(self.lock_path)
            except Exception:
                pass

        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except FileExistsError:
            return False
        except Exception:
            return False

    def release(self):
        """Kilidi serbest bırakır (dosyayı siler)."""
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except Exception:
            pass
