from abc import ABC, abstractmethod

class ISnowTicketProcessingStrategy(ABC):    
    @abstractmethod
    def get_auth(self) -> list[dict]:
        pass

    @abstractmethod
    def fetch_list(self) -> list[dict]:
        pass

    @abstractmethod
    def processing(self) -> list[dict]:
        pass

    @abstractmethod
    def post(self) -> list[dict]:
        pass

    @abstractmethod
    def post_evidence(self) -> list[dict]:
        pass

    @abstractmethod
    def show_results(self) -> list[dict]:
        pass

    @abstractmethod
    def show_evidence_results(self) -> list[dict]:
        pass