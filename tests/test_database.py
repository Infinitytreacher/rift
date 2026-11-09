# SPDX-FileCopyrightText: 2026 Siddhant Tiwari
# SPDX-License-Identifier: AGPL-3.0-only
"""Database tests use synthetic data in a temporary database only."""

import pytest

import database


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", str(tmp_path / "synthetic.db"))
    database.init_database()


def test_empty_database():
    assert database.get_latest_session() is None
    assert database.get_latest_topics() == []
    assert database.get_dashboard_stats() == []


def test_session_topics_and_population_variance():
    session = database.create_session("Synthetic lecture transcript for testing.")
    topic_ids = database.create_topics(session, ["Synthetic Topic A", "Synthetic Topic B"])
    database.submit_bulk_feedback([
        {"topic_id": topic_ids[0], "rating": 4},
        {"topic_id": topic_ids[0], "rating": 8},
    ])
    assert database.get_session_by_id(session)["transcript_text"].startswith("Synthetic")
    stats = database.get_dashboard_stats()
    assert stats[0]["response_count"] == 2
    assert stats[0]["avg_rating"] == 6
    assert stats[0]["variance"] == 4
    assert stats[1]["response_count"] == 0
    assert stats[1]["avg_rating"] is None
    assert stats[1]["variance"] == 0


def test_only_latest_session_appears_in_dashboard():
    old = database.create_session("Synthetic old session.")
    database.create_topics(old, ["Old Synthetic Topic"])
    new = database.create_session("Synthetic new session.")
    database.create_topics(new, ["New Synthetic Topic"])
    assert [t["topic_name"] for t in database.get_latest_topics()] == ["New Synthetic Topic"]
    assert [t["topic_name"] for t in database.get_dashboard_stats()] == ["New Synthetic Topic"]


@pytest.mark.parametrize("rating", [0, 11])
def test_invalid_rating_rejected(rating):
    session = database.create_session("Synthetic session.")
    topic = database.create_topics(session, ["Synthetic Topic"])[0]
    with pytest.raises(ValueError):
        database.submit_feedback(topic, rating)
    assert database.get_feedback_by_topic(topic) == []


def test_bulk_invalid_rating_rolls_back():
    session = database.create_session("Synthetic session.")
    topic = database.create_topics(session, ["Synthetic Topic"])[0]
    with pytest.raises(ValueError):
        database.submit_bulk_feedback([
            {"topic_id": topic, "rating": 5},
            {"topic_id": topic, "rating": 11},
        ])
    assert database.get_feedback_by_topic(topic) == []
