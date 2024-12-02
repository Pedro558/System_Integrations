
from System_Integrations.classes.strategies.ServiceNow.ProductLinks.ISnowProductLinks import ISnowProductLinks


class SnowProductLinks(ISnowProductLinks):

    def auth(self, *args):
        return super().auth(*args)

    def get_accounts(self, *args):
        return super().get_accounts(*args)

    def get_most_recent_read(self, *args):
        return super().get_most_recent_read(*args)

    def get_most_recent_read_trend(self, *args):
        return super().get_most_recent_read_trend(*args)

    def process_items_product_links(self, *args):
        return super().process_items_product_links(*args)

    def process_history_total_traffic(self, *args):
        return super().process_history_total_traffic(*args)

    def process_trend_total_traffic(self, *args):
        return super().process_trend_total_traffic(*args)

    def post_total_traffic_reads(self, *args):
        return super().post_total_traffic_reads(*args)

    def post_total_traffic_reads_trends(self, *args):
        return super().post_total_traffic_reads_trends(*args)