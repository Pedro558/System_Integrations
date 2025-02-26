from typing import List
from commons.utils.parser import get_value

class SyncType:
    """
    target => Works as Source - Target
    time => Works based on latest modified
    """
    target = "target"
    time = "time"

class BaseSync():
    """
    Common logic to be used in the Snow and Netbox integration
    """
    system_a = "ServiceNow"
    system_b = "Netbox"
    
    def __init__(self, syncType=SyncType.target):
        self.syncType = syncType

    def check_if_it_has(self, arr):
        if self.syncType == SyncType.target: return len(arr["data_b"]) > 0 
        elif self.syncType == SyncType.time: return len(arr["data_a"]) > 0 or len(arr["data_b"]) > 0

    def has_new(self, new): return self.check_if_it_has(new)
    def has_update(self, update): return self.check_if_it_has(update)
    def has_delete(self, delete): return self.check_if_it_has(delete)

    # Default implementations
    def _extract_data_a(): raise NotImplementedError()
    def _extract_data_b(): raise NotImplementedError()

    def _map_new_a(self, item): return item # used in bidirectional compare
    def _map_new_b(self, item): return item # used in bidirectional compare
    def _map_update_b(self, baseItem, newItem): return {**newItem, "id":baseItem["id"]} # used in bidirectional compare
    def _map_update_b(self, baseItem, newItem): return {**newItem, "id":baseItem["id"]} # used in bidirectional compare

    def make_data_unique(self, lst): pass # used to make sure that lists that will be sync do not contain duplicates

    # def _map_new_target(self, item): return item # used in one sided compare
    # def _map_update_target(self, baseItem, newItem): return {**newItem, "id":baseItem["id"]} # used in one sided compare

    def sync_new(self, base_url="", data=[], headers={}): return
    def sync_udpate(self, base_url="", data=[], headers={}): return
    def sync_delete(self, base_url="", data=[], headers={}): return

    def get_display_string_a(self, item):
        raise NotImplementedError()

    def get_display_string_b(self, item):
        raise NotImplementedError()

    # def get_display_string_target(self, item):
    #     raise NotImplementedError()

    # Logic to execute the compare
    def compare(self, *args, **kwargs):
        if self.syncType == SyncType.target: 
            return self.compare_one_sideded(**kwargs)
        elif self.syncType == SyncType.time:
            return self.compare_bidirectional(**kwargs)

    def compare_one_sideded(self, data_a:List, data_b:List, extraInfo:dict = {}):
        new = {"data_a": [], "data_b": []}
        update = {"data_a": [], "data_b": []}
        delete = {"data_a": [], "data_b": []}

        extracted_a = self._extract_data_a(data_a)
        extracted_b = self._extract_data_b(data_b)

        for newItem in extracted_a:
            matches = list(filter(lambda x: x["extracted_info"] == newItem["extracted_info"], extracted_b))
            if len(matches) == 0:
                mappedItem = self._map_new_b(newItem["item"], data_b)
                new["data_b"] += [mappedItem]
            else: 
                mappedItem = self._map_update_b(newItem["item"], matches[0]["item"], data_b)
                has_updates = mappedItem != matches[0]["item"]
                if has_updates:
                    update["data_b"] += [mappedItem] # the scenario where more than one match is found is not treated

        for baseItem in extracted_b:
            matches = list(filter(lambda x: x["extracted_info"] == baseItem["extracted_info"], extracted_a))
            if len(matches) == 0:
                delete["data_b"] += [baseItem["item"]]

        # new = self.make_data_unique(new, data_b)
        # update = self.make_data_unique(update, data_b)
        # delete = self.make_data_unique(delete, data_b)
        return new, update, delete

    def compare_bidirectional(self, baseData:List, newData:List, extraInfo:dict = {}):
        raise NotImplementedError()
        

    def sync_new(self, items):
        """
        This function needs to return something, to assure that the list of items to operate will be 1 to 1 with the list of results
        """
        raise NotImplementedError()

    def sync_update(self, items):
        """
        This function needs to return something, to assure that the list of items to operate will be 1 to 1 with the list of results
        """
        raise NotImplementedError()

    def sync_delete(self, items):
        """
        This function needs to return something, to assure that the list of items to operate will be 1 to 1 with the list of results
        """
        raise NotImplementedError()