from System_Integrations.classes.strategies.SyncSnowNetbox.SyncCustomer import SyncCustomer


class TestMergeNicknames:
    def test_merge_nicknames_with_duplicates(self):
        sync_customer = SyncCustomer()

        item_a = {
            "u_nickname": "nickname_a1,nickname_a2"
        }
        item_b = {
            "custom_fields": {
                "config_name": "nickname_a1,nickname_b1"
            }
        }

        expected_result = "nickname_a1,nickname_b1,nickname_a2"
        result = sync_customer._merge_nicknames(item_a, item_b)
        assert result == expected_result

    def test_merge_nicknames_empty_item_a(self):
        sync_customer = SyncCustomer()

        item_a = {
            "u_nickname": ""
        }
        item_b = {
            "custom_fields": {
                "config_name": "nickname_b1,nickname_b2"
            }
        }

        expected_result = "nickname_b1,nickname_b2"
        result = sync_customer._merge_nicknames(item_a, item_b)
        assert result == expected_result

    def test_merge_nicknames_empty_item_b(self):
        sync_customer = SyncCustomer()

        item_a = {
            "u_nickname": "nickname_a1,nickname_a2"
        }
        item_b = {
            "custom_fields": {
                "config_name": ""
            }
        }

        expected_result = "nickname_a1,nickname_a2"
        result = sync_customer._merge_nicknames(item_a, item_b)
        assert result == expected_result

    def test_merge_nicknames_both_empty(self):
        sync_customer = SyncCustomer()

        item_a = {
            "u_nickname": ""
        }
        item_b = {
            "custom_fields": {
                "config_name": ""
            }
        }

        expected_result = ""
        result = sync_customer._merge_nicknames(item_a, item_b)
        assert result == expected_result


class TestBuildNickname:
    def test_build_nickname_with_nickname(self):
        sync_customer = SyncCustomer()
        item_a = {"name": "Test Name", "u_nickname": "Test Nickname", "number": "123"}
        result = sync_customer._build_nickname(item_a)
        assert result == "Test Nickname"

    def test_build_nickname_without_nickname(self):
        sync_customer = SyncCustomer()
        item_a = {"name": "Test Name", "number": "123"}
        result = sync_customer._build_nickname(item_a)
        assert result == "Test Name"

    def test_build_nickname_with_item_b(self):
        sync_customer = SyncCustomer()
        item_a = {"name": "Test Name", "number": "123"}
        item_b = {"custom_fields": {"config_name": "Config Nickname"}}
        result = sync_customer._build_nickname(item_a, item_b)
        assert result == "Config Nickname"

    def test_build_nickname_with_city(self):
        sync_customer = SyncCustomer()
        item_a = {"name": "Test Name", "number": "123", "city": "Test City", "account_parent": True}
        result = sync_customer._build_nickname(item_a)
        assert result == "Test Name Test City"

    def test_build_nickname_with_state(self):
        sync_customer = SyncCustomer()
        item_a = {"name": "Test Name", "number": "123", "state": "Test State", "account_parent": True}
        result = sync_customer._build_nickname(item_a)
        assert result == "Test Name Test State"

    def test_build_nickname_with_country(self):
        sync_customer = SyncCustomer()
        item_a = {"name": "Test Name", "number": "123", "country": "Test Country", "account_parent": True}
        result = sync_customer._build_nickname(item_a)
        assert result == "Test Name Test Country"

    def test_build_nickname_with_number(self):
        sync_customer = SyncCustomer()
        item_a = {"name": "Test Name", "number": "123"}
        result = sync_customer._build_nickname(item_a)
        assert result == "Test Name" 

    def test_build_nickname_with_no_city_state_country(self):
        sync_customer = SyncCustomer()

        item_a = {
            "name": "CustomerName",
            "u_nickname": "nickname_a1",
            "number": "123",
            "account_parent": True
        }

        expected_result = "nickname_a1"
        result = sync_customer._build_nickname(item_a)
        assert result == expected_result

    def test_build_nickname_without_account_parent(self):
        sync_customer = SyncCustomer()

        item_a = {
            "name": "CustomerName",
            "u_nickname": "nickname_a1",
            "number": "123",
            "account_parent": False
        }

        expected_result = "nickname_a1"
        result = sync_customer._build_nickname(item_a)
        assert result == expected_result

# class TestMakeDataUnique:
#     def test_make_data_unique_with_duplicates(self):
#         sync_customer = SyncCustomer()

#         lst = {
#             "data_b": [
#                 {"name": "Customer1", "slug": "customer1", "custom_fields": {"number": "001"}},
#                 {"name": "Customer1", "slug": "customer1", "custom_fields": {"number": "002"}},
#                 {"name": "Customer2", "slug": "customer2", "custom_fields": {"number": "003"}},
#                 {"name": "Customer2", "slug": "customer2", "custom_fields": {"number": "004"}},
#             ]
#         }

#         expected_result = {
#             "data_b": [
#                 {"name": "Customer1 (001)", "slug": "customer1-001", "custom_fields": {"number": "001"}},
#                 {"name": "Customer1 (002)", "slug": "customer1-002", "custom_fields": {"number": "002"}},
#                 {"name": "Customer2 (003)", "slug": "customer2-003", "custom_fields": {"number": "003"}},
#                 {"name": "Customer2 (004)", "slug": "customer2-004", "custom_fields": {"number": "004"}},
#             ]
#         }

#         result = sync_customer.make_data_unique(lst)
#         assert result == expected_result

#     def test_make_data_unique_without_duplicates(self):
#         sync_customer = SyncCustomer()

#         lst = {
#             "data_b": [
#                 {"name": "Customer1", "slug": "customer1", "custom_fields": {"number": "001"}},
#                 {"name": "Customer2", "slug": "customer2", "custom_fields": {"number": "002"}},
#                 {"name": "Customer3", "slug": "customer3", "custom_fields": {"number": "003"}},
#             ]
#         }

#         expected_result = {
#             "data_b": [
#                 {"name": "Customer1", "slug": "customer1", "custom_fields": {"number": "001"}},
#                 {"name": "Customer2", "slug": "customer2", "custom_fields": {"number": "002"}},
#                 {"name": "Customer3", "slug": "customer3", "custom_fields": {"number": "003"}},
#             ]
#         }

#         result = sync_customer.make_data_unique(lst)
#         assert result == expected_result

#     def test_make_data_unique_empty_list(self):
#         sync_customer = SyncCustomer()

#         lst = {
#             "data_b": []
#         }

#         expected_result = {
#             "data_b": []
#         }

#         result = sync_customer.make_data_unique(lst)
#         assert result == expected_result

#     def test_make_data_unique_single_item(self):
#         sync_customer = SyncCustomer()

#         lst = {
#             "data_b": [
#                 {"name": "Customer1", "slug": "customer1", "custom_fields": {"number": "001"}}
#             ]
#         }

#         expected_result = {
#             "data_b": [
#                 {"name": "Customer1", "slug": "customer1", "custom_fields": {"number": "001"}}
#             ]
#         }

#         result = sync_customer.make_data_unique(lst)
#         assert result == expected_result






