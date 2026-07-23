"""PR-1.3 — pure, deterministic credit-serial generation."""

from services.issuance_state import make_serial


class TestMakeSerial:
    def test_format_is_project_vintage_zero_padded_sequence(self):
        assert make_serial("proj-a", 2026, 1) == "proj-a-2026-000001"

    def test_zero_padded_to_six_digits(self):
        assert make_serial("proj-a", 2026, 42) == "proj-a-2026-000042"

    def test_sequence_beyond_six_digits_not_truncated(self):
        assert make_serial("proj-a", 2026, 1234567) == "proj-a-2026-1234567"

    def test_deterministic_same_inputs_same_serial(self):
        first = make_serial("proj-a", 2026, 7)
        second = make_serial("proj-a", 2026, 7)
        assert first == second

    def test_distinct_across_sequence(self):
        serials = {make_serial("proj-a", 2026, i) for i in range(1, 51)}
        assert len(serials) == 50

    def test_distinct_across_projects(self):
        assert make_serial("proj-a", 2026, 1) != make_serial("proj-b", 2026, 1)

    def test_distinct_across_vintage(self):
        assert make_serial("proj-a", 2026, 1) != make_serial("proj-a", 2027, 1)
