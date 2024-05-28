from .ISnowTicketProcessingStrategy import ISnowTicketProcessingStrategy

class ServiceNowTicketProcessingContext():
    """
    The Context defines the interface of interest to clienxts.
    """

    def __init__(self, strategy: ISnowTicketProcessingStrategy) -> None:
        """
        Usually, the Context accepts a strategy through the constructor, but
        also provides a setter to change it at runtime.
        """

        self._strategy = strategy

    @property
    def strategy(self) -> ISnowTicketProcessingStrategy:
        """
        The Context maintains a reference to one of the Strategy objects. The
        Context does not know the concrete class of a strategy. It should work
        with all strategies via the Strategy interface.
        """

        return self._strategy

    @strategy.setter
    def strategy(self, strategy: ISnowTicketProcessingStrategy) -> None:
        """
        Usually, the Context allows replacing a Strategy object at runtime.
        """

        self._strategy = strategy

    def get_auth(self):
        return self._strategy.get_auth()
    
    def fetch_list(self) -> list[dict]:
        return self._strategy.fetch_list()

    def processing(self) -> list[dict]:
        return self._strategy.processing()

    def post(self) -> list[dict]:
        return self._strategy.post()

    def post_evidence(self) -> list[dict]:
        return self._strategy.post_evidence()

    def show_results(self) -> list[dict]:
        return self._strategy.show_results()

    def show_evidence_results(self) -> list[dict]:
        return self._strategy.show_evidence_results()