        mock_usa_client.mock_award_search(items, page_size=10)

        search = mock_usa_client.awards.search().contracts()
        results = list(search)

        assert len(results) == 5

    def test_explicit_limit_overrides_default(self, mock_usa_client, client_config):
        """Explicit limit() should override the default config limit."""
        client_config(default_result_limit=5)

        items = [{"Award ID": f"AWD-{i}"} for i in range(20)]
        mock_usa_client.mock_award_search(items, page_size=10)

        search = mock_usa_client.awards.search().contracts().limit(10)
        results = list(search)

        # Explicit limit of 10 should override default of 5
        assert len(results) == 10

    def test_no_default_limit_when_config_is_none(self, mock_usa_client, client_config):
        """When default_result_limit is None, all items should be returned."""
        client_config(default_result_limit=None)

        items = [{"Award ID": f"AWD-{i}"} for i in range(20)]
        mock_usa_client.mock_award_search(items, page_size=10)

        search = mock_usa_client.awards.search().contracts()
        results = list(search)

        # All 20 items should be returned
        assert len(results) == 20

    def test_default_limit_stops_pagination_early(self, mock_usa_client, client_config):
        """Default limit should stop pagination before fetching all pages."""
        client_config(default_result_limit=5)

        # 20 items with page_size=3 would normally require 7 pages
        items = [{"Award ID": f"AWD-{i}"} for i in range(20)]
        mock_usa_client.mock_award_search(items, page_size=3)

        search = mock_usa_client.awards.search().contracts()
        results = list(search)

        assert len(results) == 5

        # Should have fetched only 2 pages (3 + 3 = 6 items available, limited to 5)
        request_count = mock_usa_client.get_request_count(
            MockUSASpendingClient.Endpoints.AWARD_SEARCH
        )
        assert request_count == 2


