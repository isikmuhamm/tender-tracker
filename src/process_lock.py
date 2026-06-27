import os
import sys
import ctypes
import uuid
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
        self.owner_token = uuid.uuid4().hex
        self.acquired = False

    def acquire(self) -> bool:
        """Kilidi almaya çalışır. Başarılı ise True döner."""
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if ":" in content:
                    pid_str, _ = content.split(":", 1)
                    pid = int(pid_str)
                else:
                    pid = int(content)
                
                if not is_process_running(pid):
                    try:
                        os.remove(self.lock_path)
                    except Exception:
                        pass
            except Exception:
                pass

        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding="utf-8") as f:
                f.write(f"{os.getpid()}:{self.owner_token}")
            self.acquired = True
            return True
        except FileExistsError:
            return False
        except Exception:
            return False

    def release(self):
        """Eğer kilidi bu nesne almışsa serbest bırakır (dosyayı siler)."""
        try:
            if os.path.exists(self.lock_path):
                with open(self.lock_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if ":" in content:
                    _, token = content.split(":", 1)
                    if token == self.owner_token:
                        os.remove(self.lock_path)
                        self.acquired = False
                else:
                    try:
                        pid = int(content)
                        if pid == os.getpid():
                            os.remove(self.lock_path)
                            self.acquired = False
                    except ValueError:
                        pass
        except Exception:
            pass
