from abc import ABC, abstractmethod

from System_Integrations.classes.requests.zabbix.dataclasses import Item, Read

class ISnowProductLinks(ABC):
    
    @classmethod #TODO test if this works
    def auth(self):
        # TODO implement default authentication
        pass

    @classmethod
    def get_accounts(self):
        pass

    @classmethod
    def get_most_recent_read(self):
        pass

    @classmethod
    def get_most_recent_read_trend(self):
        pass

    @classmethod
    def process_items_product_links(self, items:list[Item]):
        pass

    @classmethod
    def process_history_total_traffic(self, reads:list[Read]):
        pass

    @classmethod
    def process_trend_total_traffic(self, reads:list[Read]):
        pass

    @classmethod
    def post_total_traffic_reads(self, reads:list[Read]):
        pass

    @classmethod
    def post_total_traffic_reads_trends(self, reads:list[Read]):
        pass