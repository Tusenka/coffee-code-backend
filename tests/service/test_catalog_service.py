import pytest


class TestCatalogService:
    @pytest.mark.positive
    def test_list_skills(self, catalog_service):
        result = catalog_service.list_skills()

        assert result.skills

    @pytest.mark.positive
    def test_list_timezones(self, catalog_service):
        result = catalog_service.list_timezones()

        assert result.timezones

    @pytest.mark.positive
    def test_list_goals(self, catalog_service):
        result = catalog_service.list_goals()

        assert result.goals

    @pytest.mark.positive
    def test_list_quants_default(self, catalog_service):
        result = catalog_service.list_quants()

        assert result.intervals
        for quant in result.intervals:
            assert 0 <= quant.day < 7
            assert 0 <= quant.hour < 24

    @pytest.mark.positive
    def test_list_quants_with_timezone(self, catalog_service):
        result = catalog_service.list_quants(timezone="Europe/Moscow")

        assert result.intervals
        for quant in result.intervals:
            assert 0 <= quant.hour < 24
