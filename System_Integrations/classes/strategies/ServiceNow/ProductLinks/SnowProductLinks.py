
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.ISnowProductLinks import ISnowProductLinks


class SnowProductLinks(ISnowProductLinks):

    @classmethod #TODO test if this works
    def auth(self, *agrs):
        # TODO implement default authentication
        pass

    @classmethod
    def get_accounts(self, *agrs):
        pass

    @classmethod
    def get_most_recent_read(self, *agrs):
        pass

    @classmethod
    def get_most_recent_read_trend(self, *agrs):
        pass

    @classmethod
    def process_items_product_links(self, *agrs):
        pass

    @classmethod
    def process_history_total_traffic(self, *args):
        pass

    @classmethod
    def process_trend_total_traffic(self, *args):
        pass

    @classmethod
    def post_total_traffic_reads(self, *args):
        pass

    @classmethod
    def post_total_traffic_reads_trends(self, *args):
        pass