from abc import ABC, abstractmethod

from System_Integrations.classes.requests.zabbix.dataclasses import EnumReadType, EnumSyncType

class IZbxDB(ABC):
    @classmethod #TODO test if this works
    def auth(self, *args):
        pass

    @classmethod
    def get_items_product_links(self, *args):
        return []

    @classmethod
    def get_history_total_traffic(self, *args):
        pass

    @classmethod
    def get_trend_total_traffic(self, *args):
        pass