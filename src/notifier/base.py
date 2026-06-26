from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseNotifier(ABC):
    """
    Tüm bildirim kanalları (Email, Telegram vb.) için temel soyut sınıf.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def send_notification(self, tenders: List[Dict[str, Any]]) -> bool:
        """
        İhaleleri ilgili kanaldan gönderir. Başarı durumunu boolean olarak döner.
        """
        pass
