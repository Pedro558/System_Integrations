import json
from typing import Tuple
from System_Integrations.classes.strategies.SyncSnowNetbox import BaseSync
from commons.utils.parser import get_value
from .Result import Result

class SyncContext():
    data_a = []
    data_b = []

    new = {"data_a": [], "data_b": []}
    update  = {"data_a": [], "data_b": []}
    delete = {"data_a": [], "data_b": []}
    result = {
        "result_a": Result(new=[], update=[], delete=[], all=[]), 
        "result_b": Result(new=[], update=[], delete=[], all=[]) 
    } 
    corr_a = [] # list of tuble (item, result)
    corr_b = [] # list of tuble (item, result)

    def __init__(self, strategy: BaseSync, data_a:list= [], data_b:list= []) -> None:
        self._strategy = strategy
        self.data_a = data_a
        self.data_b = data_b
        self.clear()

    @property
    def strategy(self) -> BaseSync:
        return self._strategy

    @strategy.setter
    def strategy(self, strategy: BaseSync) -> None:
        self._strategy:BaseSync = strategy
        self.clear()

    def clear(self) -> None:
        self.new = {"data_a": [], "data_b": []}
        self.update  = {"data_a": [], "data_b": []}
        self.delete = {"data_a": [], "data_b": []}
        self.result = {
            "result_a": Result(new=[], update=[], delete=[], all=[]), 
            "result_b": Result(new=[], update=[], delete=[], all=[]) 
        } 
        self.corr_a = []
        self.corr_b = []

    def compare(self, extraInfo: dict = {}) -> Result:
        self.new, self.update, self.delete = self._strategy.compare(data_a=self.data_a, data_b=self.data_b, extraInfo=extraInfo)

        return self.new, self.update, self.delete

    def sync_all(self, baseUrl:str, headers: dict) -> Tuple:
        """
            ***ATTENTION***: this function will also perform deletion. Be sure to use it only when needed. 
        """
        self.sync_new(baseUrl, headers)
        self.sync_update(baseUrl, headers)
        self.sync_delete(baseUrl, headers)

        return self.result
    
    def sync_new(self, baseUrl:str, headers: dict) -> list:
        if self._strategy.has_new(self.new):
            results = self._strategy.sync_new(baseUrl, self.new, headers)
            self.result["result_a"].new = get_value(results, lambda x: x["result_a"], [])
            self.result["result_b"].new = get_value(results, lambda x: x["result_b"], [])
            self.corr_a

        return {
            "result_a": self.result["result_a"].new, 
            "result_b": self.result["result_b"].new 
        }
    
    def sync_update(self, baseUrl:str, headers: dict) -> list:
        if self._strategy.has_update(self.update):
            results = self._strategy.sync_update(baseUrl, self.update, headers)
            self.result["result_a"].update = get_value(results, lambda x: x["result_a"], [])
            self.result["result_b"].update = get_value(results, lambda x: x["result_b"], [])

        return {
            "result_a": self.result["result_a"].update, 
            "result_b": self.result["result_b"].update 
        }
    
    def sync_delete(self, baseUrl:str, headers: dict) -> list:
        if self._strategy.has_delete(self.delete):
            results = self._strategy.sync_delete(baseUrl, self.update, headers)
            self.result["result_a"].delete = get_value(results, lambda x: x["result_a"], [])
            self.result["result_b"].delete = get_value(results, lambda x: x["result_b"], [])

        return {
            "result_a": self.result["result_a"].delete, 
            "result_b": self.result["result_b"].delete 
        }

    # TODO DELETE LATER
    def get_content_to_show_old(self, payload, result):
        was_successful = lambda result: 200 <= result.status_code and result.status_code <= 299

        aContentToShow = [self._strategy.get_display_string(item) for item in payload]
        if was_successful(result):
            return [f"{content} OK" for content in aContentToShow]
        else:
            resultJson = None
            try:
                resultJson = result.json()
            except:
                pass

            for index, content in enumerate(aContentToShow):
                content = f"{content} ERROR"
                if resultJson:
                    content += f" => {resultJson[index]}"

                aContentToShow[index] = content

        return aContentToShow
    
    # TODO DELETE LATER
    def _display_results_old(self):
        if len(self.result.all) == 0:
            print("Already synced.")
            return

        if len(self.result.new) > 0:
            aContentToShow = self.get_content_to_show(self.new, self.result.new[-1])
            print(f"\nCreate ({len(aContentToShow)}): {self.result.new[-1].status_code} {self.result.new[-1].reason}")
            for item in aContentToShow:
                print(f"    {item}")

        if len(self.result.update) > 0:
            aContentToShow = self.get_content_to_show(self.update, self.result.update[-1])
            print(f"\nUpdate ({len(aContentToShow)}): {self.result.update[-1].status_code} {self.result.update[-1].reason}")
            for item in aContentToShow:
                print(f"    {item}")

        if len(self.result.delete) > 0:
            aContentToShow = self.get_content_to_show(self.delete, self.result.delete[-1])
            print(f"\nDelete ({len(aContentToShow)}): {self.result.delete[-1].status_code} {self.result.delete[-1].reason}")
            for item in aContentToShow:
                print(f"    {item}")

    def _print_results_summary(self, result):
        if len(result) == 0: return ""
        success = []
        failed = []
        [success.append(x) if x.ok else failed.append(x) for x in result]
        return f"({len(success)} OK, {len(failed)} FAILED)"

    def get_content_to_show(self, items, results, get_display):
        contentReturn = []
        
        for res in results:
            if res is None: continue
            data = json.loads(res.request.body)
            data = data if isinstance(data, list) else [data]
            contentReturn.append((
                [get_display(x) for x in data],
                res
            ))

        return contentReturn


    def display_results(self):
        direction_config = {
            BaseSync.SyncType.target: { 
                "symbol": "==>", 
                "description": "One Sided" 
            },
            BaseSync.SyncType.time: { 
                "symbol": "<==>", 
                "description": "Bidirectional (last modified)"
            },
        }

        tab_char = "  "
        tab_number = 2
        tab = lambda: tab_char * tab_number
        def default_print_item(corr):
            for i, data in enumerate(corr):
                content, result = data

                oneRequestPerItem = len(content) == 1

                if oneRequestPerItem:
                    # this means that for each item that was a http call
                    # in this case, we want to show something like this:
                    # (OK - 200) ITEM 1
                    # (OK - 200) ITEM 2
                    # (FORBIDDEN - 403) ITEM 3
                    # -> {'error': 'missing authorization header'}
                    print(tab(), f"({result.status_code} {result.reason}) - ", content[0])
                else:
                    # this means that for many items where grouped into a single http call
                    # in this case, we want to show something like this:
                    # (OK - 200) REQUEST 1
                    #   ITEM 1
                    #   ITEM 2
                    # (FORBIDDEN - 403) REQUEST 2
                    # -> {'error': 'missing authorization header'}
                    #   ITEM 3
                    print(tab(), f"({result.status_code} {result.reason}) - REQUEST {i + 1}")
                
                if not result.ok:
                    response = ""
                    try:
                        response = result.json()
                    except:
                        response = result.text
                    
                    print(tab(), tab(), "Response")
                    print(tab(), tab(), "   ╰──> ", response)
                    print(tab(), tab(), "Data sent")
                    print(tab(), tab(), "   ╰──> ", result.request.body)
                
                print()

                if not oneRequestPerItem: 
                    for item in content:
                        print(tab(), tab(),  item)
                    print()


        config = direction_config.get(self._strategy.syncType)
        symbol = config["symbol"] 
        description = config["description"] 
        print(f"{ description } -", self._strategy.system_a, symbol, self._strategy.system_b)
        print()

        if not self.result["result_a"].all and not self.result["result_b"].all:
            print(tab(), "Already synced.")
            print()


        if self.result["result_a"].all:
            print(tab(), self._strategy.system_b)
            created = self.result['result_a'].new
            updated = self.result['result_a'].update
            deleted = self.result['result_a'].delete
            tab_number += 1
            print(tab(), "Summary")
            tab_number += 1
            print(tab(), f"- Created ({len(created)}):", self._print_results_summary(created))
            print(tab(), f"- Updated ({len(updated)}):", self._print_results_summary(updated))
            print(tab(), f"- Deleted ({len(deleted)}):", self._print_results_summary(deleted))
            tab_number -= 2

            if created or updated or deleted:
                print()
                tab_number += 1
                print(tab(), "Details")
                print()

            if created: 
                print(tab(), f"Created ({len(created)})")
                tab_number += 1
                corr = self.get_content_to_show(self.new["data_a"], created, self._strategy.get_display_string_a)
                default_print_item(corr)
                tab_number -= 1
                # [default_print_item(*x) for x in self.get_content_to_show(self.new["data_a"], self.result["result_a"].new, self._strategy.get_display_string_a)]
                
            if updated: 
                print(tab(), f"Updated ({len(updated)})")
                tab_number += 1
                corr = self.get_content_to_show(self.update["data_a"], updated, self._strategy.get_display_string_a)
                default_print_item(corr)
                tab_number -= 1
                    
            if deleted: 
                print(tab(), f"Deleted ({len(deleted)})")
                tab_number += 1
                corr = self.get_content_to_show(self.delete["data_a"], deleted, self._strategy.get_display_string_a)
                default_print_item(corr)
                tab_number -= 1

            tab_number -= 1

        if self.result["result_b"].all:
            print(tab(), self._strategy.system_b)
            created = self.result['result_b'].new
            updated = self.result['result_b'].update
            deleted = self.result['result_b'].delete
            tab_number += 1
            print(tab(), "Summary")
            tab_number += 1
            print(tab(), f"- Created ({len(created)}):", self._print_results_summary(created))
            print(tab(), f"- Updated ({len(updated)}):", self._print_results_summary(updated))
            print(tab(), f"- Deleted ({len(deleted)}):", self._print_results_summary(deleted))
            tab_number -= 2

            if created or updated or deleted:
                print()
                tab_number += 1
                print(tab(), "Details")
                print()

            if created:
                print(tab(), f"Created ({len(created)})") 
                tab_number += 1
                corr = self.get_content_to_show(self.new["data_b"], created, self._strategy.get_display_string_b)
                default_print_item(corr)
                tab_number -= 1

            if updated: 
                print(tab(), f"Updated ({len(updated)})")
                tab_number += 1
                corr = self.get_content_to_show(self.update["data_b"], updated, self._strategy.get_display_string_b)
                default_print_item(corr)
                tab_number -= 1
                    
            if deleted: 
                print(tab(), f"Deleted ({len(deleted)})")
                tab_number += 1
                corr = self.get_content_to_show(self.delete["data_b"], deleted, self._strategy.get_display_string_b)
                default_print_item(corr)
                tab_number -= 1

            tab_number -= 1