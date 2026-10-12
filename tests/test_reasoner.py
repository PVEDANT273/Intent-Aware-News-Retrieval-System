import json

import pytest


def make_response(content_str):
    return {"message": {"content": content_str}}


class TestExtract:
    def test_extract_shapes_groups(self, reasoner):
        data = reasoner.extract()
        assert len(data) == 3
        assert data[0]["group_id"] == 0
        assert data[0]["titles"] == ["Fed raises rates"]
        assert data[0]["sources"] == ["Reuters"]
        assert data[0]["number_of_articles"] == 1


class TestParseJson:
    def test_parses_fenced_json(self, reasoner):
        raw = '```json\n[{"group_id": 0, "rank": 1, "reason": "x"}]\n```'
        result = reasoner._parse_json(raw)
        assert result == [{"group_id": 0, "rank": 1, "reason": "x"}]

    def test_parses_bare_json(self, reasoner):
        raw = 'Sure, here: [{"group_id": 1, "rank": 1, "reason": "y"}] done.'
        result = reasoner._parse_json(raw)
        assert result[0]["group_id"] == 1

    def test_raises_on_no_json(self, reasoner):
        with pytest.raises(ValueError):
            reasoner._parse_json("no brackets here at all")

    def test_raises_on_malformed_json(self, reasoner):
        with pytest.raises(json.JSONDecodeError):
            reasoner._parse_json("[{not valid json}]")


class TestValidate:
    def test_drops_out_of_range_group_id(self, reasoner):
        ranked = [{"group_id": 99, "rank": 1, "reason": "bad"}]
        assert reasoner._validate(ranked) == []

    def test_drops_duplicate_group_id(self, reasoner):
        ranked = [
            {"group_id": 0, "rank": 1, "reason": "a"},
            {"group_id": 0, "rank": 2, "reason": "a-dup"},
        ]
        result = reasoner._validate(ranked)
        assert len(result) == 1

    def test_sorts_by_rank(self, reasoner):
        ranked = [
            {"group_id": 1, "rank": 3, "reason": "c"},
            {"group_id": 0, "rank": 1, "reason": "a"},
            {"group_id": 2, "rank": 2, "reason": "b"},
        ]
        result = reasoner._validate(ranked)
        assert [r["group_id"] for r in result] == [0, 2, 1]

    def test_rejects_non_list(self, reasoner):
        with pytest.raises(ValueError):
            reasoner._validate({"not": "a list"})

    def test_skips_items_missing_fields(self, reasoner):
        ranked = [{"group_id": 0}]  # no rank
        assert reasoner._validate(ranked) == []


class TestRank:
    def test_retries_on_malformed_then_succeeds(self, reasoner, mocker):
        mock_client = mocker.patch.object(reasoner, "client")
        mock_client.chat.side_effect = [
            make_response("not json"),
            make_response('[{"group_id": 0, "rank": 1, "reason": "ok"}]'),
        ]
        result = reasoner.rank()
        assert result == [{"group_id": 0, "rank": 1, "reason": "ok"}]
        assert mock_client.chat.call_count == 2

    def test_raises_after_max_retries(self, reasoner, mocker):
        mock_client = mocker.patch.object(reasoner, "client")
        mock_client.chat.return_value = make_response("still not json")
        with pytest.raises(RuntimeError):
            reasoner.rank()
        assert mock_client.chat.call_count == 3  # MAX_RETRIES

    def test_succeeds_on_first_try(self, reasoner, mocker):
        mock_client = mocker.patch.object(reasoner, "client")
        mock_client.chat.return_value = make_response(
            '[{"group_id": 2, "rank": 1, "reason": "layoffs matter"}]'
        )
        result = reasoner.rank()
        assert result == [{"group_id": 2, "rank": 1, "reason": "layoffs matter"}]
        assert mock_client.chat.call_count == 1


class TestBuild:
    def test_picks_longest_article_as_representative(self, reasoner):
        groups = [[
            {"title": "A", "content": "short", "description": ""},
            {"title": "B", "content": "a much longer article body here", "description": ""},
        ]]
        ranked = [{"group_id": 0, "rank": 1, "reason": "r"}]
        result = reasoner.build(ranked, groups)
        assert result[0]["representative_article"]["title"] == "B"

    def test_respects_top_n(self, reasoner, sample_groups):
        ranked = [
            {"group_id": 0, "rank": 1, "reason": "a"},
            {"group_id": 1, "rank": 2, "reason": "b"},
            {"group_id": 2, "rank": 3, "reason": "c"},
        ]
        result = reasoner.build(ranked, sample_groups, top_n=2)
        assert len(result) == 2
        assert result[0]["group_id"] == 0
        assert result[1]["group_id"] == 1

    def test_top_n_none_returns_all(self, reasoner, sample_groups):
        ranked = [
            {"group_id": 0, "rank": 1, "reason": "a"},
            {"group_id": 1, "rank": 2, "reason": "b"},
        ]
        result = reasoner.build(ranked, sample_groups, top_n=None)
        assert len(result) == 2

    def test_build_includes_all_articles(self, reasoner, sample_groups):
        ranked = [{"group_id": 1, "rank": 1, "reason": "x"}]
        result = reasoner.build(ranked, sample_groups)
        assert result[0]["all_articles"] == sample_groups[1]
