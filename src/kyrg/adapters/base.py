from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

OutPutT = TypeVar("OutPutT")
ClientT = TypeVar("ClientT")

class APIAdapterBase(ABC, Generic[OutPutT]):
    URL = ""
    PROVIDER = ""
    
    @abstractmethod
    def _request(self) -> Any:
        pass
    
    @abstractmethod
    def _normalize_response(self, response: Any) -> OutPutT:
        pass
    
    def run(self) -> OutPutT:
        response = self._request()
        return self._normalize_response(response)
    
    
class APIAdapterSDKBase(APIAdapterBase[OutPutT], Generic[OutPutT, ClientT]):
    def __init__(self, client: ClientT):
        self.client = client
    