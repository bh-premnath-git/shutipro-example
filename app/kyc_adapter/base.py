from abc import ABC, abstractmethod
from typing import Dict, Any


class KYCProvider(ABC):
    @abstractmethod
    async def start_verification(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...
