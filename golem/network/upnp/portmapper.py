from abc import ABC, abstractmethod
from typing import Dict


class IPortMapper(ABC):

    @property
    @abstractmethod
    def available(self) -> bool:
        pass

    @property
    @abstractmethod
    def mapping(self) -> Dict[str, Dict[int, int]]:
        pass

    @abstractmethod
    def discover(self) -> None:
        pass

    @abstractmethod
    def create_mapping(self,
                       local_port: int,
                       external_port: int = None,
                       protocol: str = 'TCP',
                       lease_duration: int = None) -> None:
        pass

    @abstractmethod
    def remove_mapping(self,
                       external_port: int,
                       protocol: str) -> None:
        pass

    @abstractmethod
    def quit(self) -> None:
        pass
