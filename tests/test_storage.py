"""Tests for storage layer — ConversationDB, MemoryDB, UserProfile."""

import pytest
from pathlib import Path

from browser_agent.storage.conversation_db import ConversationDB
from browser_agent.storage.memory_db import MemoryDB
from browser_agent.storage.user_profile import UserProfile


class TestConversationDB:
    @pytest.fixture()
    def db(self, tmp_path):
        db = ConversationDB(tmp_path / "conv.db")
        yield db
        db.close()

    def test_create_thread(self, db):
        thread = db.create_thread("Test Thread")
        assert thread.title == "Test Thread"
        assert thread.thread_id

    def test_list_threads(self, db):
        db.create_thread("Thread 1")
        db.create_thread("Thread 2")
        threads = db.list_threads()
        assert len(threads) == 2

    def test_add_and_get_messages(self, db):
        thread = db.create_thread("Chat")
        db.add_message(thread.thread_id, "user", "Hello")
        db.add_message(thread.thread_id, "assistant", "Hi there!")
        messages = db.get_messages(thread.thread_id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"

    def test_delete_thread(self, db):
        thread = db.create_thread("To Delete")
        db.delete_thread(thread.thread_id)
        threads = db.list_threads()
        assert len(threads) == 0

    def test_update_thread_title(self, db):
        thread = db.create_thread("Old Title")
        db.update_thread_title(thread.thread_id, "New Title")
        threads = db.list_threads()
        assert threads[0].title == "New Title"

    def test_search_messages(self, db):
        thread = db.create_thread("Search Test")
        db.add_message(thread.thread_id, "user", "Find the python bug")
        db.add_message(thread.thread_id, "assistant", "The issue is in main.py")
        results = db.search_messages("python")
        assert len(results) >= 1


class TestMemoryDB:
    @pytest.fixture()
    def db(self, tmp_path):
        db = MemoryDB(tmp_path / "memory.db")
        yield db
        db.close()

    def test_remember_and_recall(self, db):
        db.remember("User prefers dark mode", "preference")
        results = db.recall("dark mode")
        assert len(results) >= 1
        assert "dark mode" in results[0].fact

    def test_remember_deduplicates(self, db):
        db.remember("User's name is John", "personal")
        db.remember("User's name is John", "personal")
        all_entries = db.get_all()
        assert len(all_entries) == 1

    def test_categories(self, db):
        db.remember("Likes pizza", "preference")
        db.remember("john@example.com", "credential")
        prefs = db.get_by_category("preference")
        creds = db.get_by_category("credential")
        assert len(prefs) == 1
        assert len(creds) == 1

    def test_invalid_category_defaults_to_other(self, db):
        entry = db.remember("Some fact", "invalid_category")
        assert entry.category == "other"

    def test_forget(self, db):
        entry = db.remember("Temporary fact", "other")
        db.forget(entry.id)
        results = db.get_all()
        assert len(results) == 0

    def test_format_for_prompt_empty(self, db):
        result = db.format_for_prompt()
        assert result == ""

    def test_format_for_prompt_with_data(self, db):
        db.remember("User is a developer", "personal")
        result = db.format_for_prompt()
        assert "developer" in result
        assert "remember" in result.lower()


class TestUserProfile:
    @pytest.fixture()
    def profile(self, tmp_path):
        p = UserProfile(tmp_path / "profile.db")
        yield p
        p.close()

    def test_set_and_get(self, profile):
        profile.set("full_name", "John Doe")
        assert profile.get("full_name") == "John Doe"

    def test_get_nonexistent_field(self, profile):
        result = profile.get("nonexistent_key_xyz")
        assert result == ""

    def test_format_for_prompt(self, profile):
        profile.set("full_name", "Jane")
        profile.set("email", "jane@example.com")
        result = profile.format_for_prompt()
        assert "Jane" in result
        assert "jane@example.com" in result
