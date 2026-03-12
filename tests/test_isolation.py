"""
Tests for data isolation in multi-user mode.
"""

import pytest
import threading
import time

from backend.state import VectorStoreManager


class TestVectorStoreManagerLegacy:
    """Test legacy mode functionality."""

    def test_set_legacy(self):
        """Test setting legacy vectorstore."""
        manager = VectorStoreManager()
        
        manager.set_legacy("fake_vs", "test.pdf", 10)
        
        vs, filename, chunks = manager.get_legacy()
        assert vs == "fake_vs"
        assert filename == "test.pdf"
        assert chunks == 10

    def test_is_legacy_ready(self):
        """Test checking if legacy is ready."""
        manager = VectorStoreManager()
        
        assert manager.is_legacy_ready() is False
        
        manager.set_legacy("vs", "file.pdf", 5)
        
        assert manager.is_legacy_ready() is True

    def test_get_legacy_when_not_set(self):
        """Test getting legacy when not set returns None."""
        manager = VectorStoreManager()
        
        result = manager.get_legacy()
        
        assert result is None


class TestVectorStoreManagerUser:
    """Test user-specific vectorstore functionality."""

    def test_set_user_vectorstore(self):
        """Test setting vectorstore for a user."""
        manager = VectorStoreManager()
        
        manager.set_user_vectorstore("user1", "doc1", "vs_user1_doc1")
        
        vs = manager.get_user_vectorstore("user1", "doc1")
        assert vs == "vs_user1_doc1"

    def test_get_user_vectorstore_not_found(self):
        """Test getting non-existent user vectorstore."""
        manager = VectorStoreManager()
        
        vs = manager.get_user_vectorstore("user1", "doc1")
        
        assert vs is None

    def test_user_isolation(self):
        """Test that users have isolated vectorstores."""
        manager = VectorStoreManager()
        
        # User 1 uploads doc1
        manager.set_user_vectorstore("user1", "doc1", "vs_user1_doc1")
        
        # User 2 uploads doc1 - completely separate
        manager.set_user_vectorstore("user2", "doc1", "vs_user2_doc1")
        
        # User 1's data should be unchanged
        assert manager.get_user_vectorstore("user1", "doc1") == "vs_user1_doc1"
        
        # User 2's data should be correct
        assert manager.get_user_vectorstore("user2", "doc1") == "vs_user2_doc1"

    def test_multiple_documents_per_user(self):
        """Test that a user can have multiple documents."""
        manager = VectorStoreManager()
        
        # User 1 has 3 documents
        manager.set_user_vectorstore("user1", "doc1", "vs1")
        manager.set_user_vectorstore("user1", "doc2", "vs2")
        manager.set_user_vectorstore("user1", "doc3", "vs3")
        
        assert manager.get_user_vectorstore("user1", "doc1") == "vs1"
        assert manager.get_user_vectorstore("user1", "doc2") == "vs2"
        assert manager.get_user_vectorstore("user1", "doc3") == "vs3"

    def test_get_user_documents(self):
        """Test getting list of user's documents."""
        manager = VectorStoreManager()
        
        manager.set_user_vectorstore("user1", "doc1", "vs1")
        manager.set_user_vectorstore("user1", "doc2", "vs2")
        manager.set_user_vectorstore("user2", "doc1", "vs3")
        
        user1_docs = manager.get_user_documents("user1")
        
        assert len(user1_docs) == 2
        assert "doc1" in user1_docs
        assert "doc2" in user1_docs


class TestVectorStoreManagerDelete:
    """Test deletion functionality."""

    def test_delete_user_vectorstore(self):
        """Test deleting a specific user document."""
        manager = VectorStoreManager()
        
        manager.set_user_vectorstore("user1", "doc1", "vs1")
        assert manager.get_user_vectorstore("user1", "doc1") == "vs1"
        
        result = manager.delete_user_vectorstore("user1", "doc1")
        
        assert result is True
        assert manager.get_user_vectorstore("user1", "doc1") is None

    def test_delete_non_existent_vectorstore(self):
        """Test deleting non-existent vectorstore returns False."""
        manager = VectorStoreManager()
        
        result = manager.delete_user_vectorstore("user1", "doc999")
        
        assert result is False

    def test_clear_user_data(self):
        """Test clearing all data for a user."""
        manager = VectorStoreManager()
        
        manager.set_user_vectorstore("user1", "doc1", "vs1")
        manager.set_user_vectorstore("user1", "doc2", "vs2")
        manager.set_user_vectorstore("user2", "doc1", "vs3")
        
        deleted_count = manager.clear_user_data("user1")
        
        assert deleted_count == 2
        assert manager.get_user_vectorstore("user1", "doc1") is None
        assert manager.get_user_vectorstore("user1", "doc2") is None
        # user2 should be unaffected
        assert manager.get_user_vectorstore("user2", "doc1") == "vs3"


class TestThreadSafety:
    """Test thread safety of VectorStoreManager."""

    def test_concurrent_access(self):
        """Test concurrent read/write access."""
        manager = VectorStoreManager()
        errors = []
        
        def writer(user_id: str, doc_id: str):
            try:
                for i in range(50):
                    manager.set_user_vectorstore(user_id, doc_id, f"vs_{i}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        def reader(user_id: str, doc_id: str):
            try:
                for i in range(50):
                    manager.get_user_vectorstore(user_id, doc_id)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(3):
            t1 = threading.Thread(target=writer, args=(f"user{i}", "doc1"))
            t2 = threading.Thread(target=reader, args=(f"user{i}", "doc1"))
            threads.extend([t1, t2])
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0


class TestStoreCount:
    """Test store count functionality."""

    def test_get_store_count(self):
        """Test getting total store count."""
        manager = VectorStoreManager()
        
        assert manager.get_store_count() == 0
        
        manager.set_user_vectorstore("user1", "doc1", "vs1")
        manager.set_user_vectorstore("user1", "doc2", "vs2")
        manager.set_user_vectorstore("user2", "doc1", "vs3")
        
        assert manager.get_store_count() == 3

    def test_get_store_count_after_delete(self):
        """Test store count after deletion."""
        manager = VectorStoreManager()
        
        manager.set_user_vectorstore("user1", "doc1", "vs1")
        manager.set_user_vectorstore("user1", "doc2", "vs2")
        
        assert manager.get_store_count() == 2
        
        manager.delete_user_vectorstore("user1", "doc1")
        
        assert manager.get_store_count() == 1
