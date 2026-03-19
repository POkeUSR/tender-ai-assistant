"""
Global application state management.
Provides thread-safe vectorstore management for multi-user support.
"""

import threading
from typing import Dict, Any, Optional, Tuple


class VectorStoreManager:
    """
    Thread-safe manager for vectorstores.
    Supports both legacy (single user) and multi-user modes.
    """
    
    def __init__(self):
        self._stores: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._legacy_store: Optional[Tuple[Any, str, int, str]] = None  # (vs, filename, chunks, raw_text)
    
    def set_legacy(self, vs: Any, filename: str, n_chunks: int, raw_text: str = "") -> None:
        """
        Set the legacy vectorstore (for single-user mode compatibility).
        
        Args:
            vs: The vectorstore object
            filename: Name of the indexed file
            n_chunks: Number of chunks in the vectorstore
            raw_text: Raw text from the document
        """
        with self._lock:
            self._legacy_store = (vs, filename, n_chunks, raw_text)
    
    def get_legacy(self) -> Optional[Tuple[Any, str, int, str]]:
        """
        Get the legacy vectorstore.
        
        Returns:
            Tuple of (vectorstore, filename, chunks_count, raw_text) or None
        """
        with self._lock:
            return self._legacy_store
    
    def get_raw_text(self) -> str:
        """
        Get raw text from the legacy store.
        
        Returns:
            Raw text string
        """
        with self._lock:
            return self._legacy_store[3] if self._legacy_store else ""
    
    def is_legacy_ready(self) -> bool:
        """Check if legacy vectorstore is initialized."""
        return self._legacy_store is not None
    
    def set_user_vectorstore(
        self, 
        user_id: str, 
        doc_id: str, 
        vs: Any
    ) -> None:
        """
        Set vectorstore for a specific user and document.
        
        Args:
            user_id: User ID
            doc_id: Document ID
            vs: The vectorstore object
        """
        key = f"{user_id}:{doc_id}"
        with self._lock:
            self._stores[key] = vs
    
    def get_user_vectorstore(
        self, 
        user_id: str, 
        doc_id: str
    ) -> Optional[Any]:
        """
        Get vectorstore for a specific user and document.
        
        Args:
            user_id: User ID
            doc_id: Document ID
            
        Returns:
            The vectorstore object or None if not found
        """
        key = f"{user_id}:{doc_id}"
        with self._lock:
            return self._stores.get(key)
    
    def delete_user_vectorstore(self, user_id: str, doc_id: str) -> bool:
        """
        Delete vectorstore for a specific user and document.
        
        Args:
            user_id: User ID
            doc_id: Document ID
            
        Returns:
            True if deleted, False if not found
        """
        key = f"{user_id}:{doc_id}"
        with self._lock:
            if key in self._stores:
                del self._stores[key]
                return True
            return False
    
    def clear_user_data(self, user_id: str) -> int:
        """
        Clear all vectorstores for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of vectorstores deleted
        """
        with self._lock:
            keys_to_delete = [
                k for k in self._stores.keys() 
                if k.startswith(f"{user_id}:")
            ]
            for key in keys_to_delete:
                del self._stores[key]
            return len(keys_to_delete)
    
    def get_user_documents(self, user_id: str) -> list[str]:
        """
        Get list of document IDs for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of document IDs
        """
        with self._lock:
            return [
                k.split(":")[1] 
                for k in self._stores.keys() 
                if k.startswith(f"{user_id}:")
            ]
    
    def get_store_count(self) -> int:
        """Get total number of stored vectorstores."""
        with self._lock:
            return len(self._stores)


# Global vectorstore manager instance
vectorstore_manager = VectorStoreManager()


# Legacy functions (for backward compatibility)
def set_vectorstore(vs: Any, filename: str, n_chunks: int, raw_text: str = "") -> None:
    """
    Set the legacy vectorstore (single-user mode).
    
    Args:
        vs: The vectorstore object
        filename: Name of the indexed file
        n_chunks: Number of chunks
        raw_text: Raw text from the document
    """
    vectorstore_manager.set_legacy(vs, filename, n_chunks, raw_text)


def get_raw_text() -> str:
    """
    Get raw text from the legacy store.
    
    Returns:
        Raw text string
    """
    return vectorstore_manager.get_raw_text()


def get_vectorstore() -> Optional[Any]:
    """
    Get the legacy vectorstore.
    
    Returns:
        The vectorstore object or None
    """
    legacy = vectorstore_manager.get_legacy()
    return legacy[0] if legacy else None


def get_legacy_filename() -> Optional[str]:
    """Get the legacy vectorstore filename."""
    legacy = vectorstore_manager.get_legacy()
    return legacy[1] if legacy else None


def get_legacy_chunks_count() -> int:
    """Get the legacy vectorstore chunks count."""
    legacy = vectorstore_manager.get_legacy()
    return legacy[2] if legacy else 0


def is_ready() -> bool:
    """Check if legacy vectorstore is ready."""
    return vectorstore_manager.is_legacy_ready()


# New functions for multi-user mode
def get_user_vectorstore(user_id: str, doc_id: str) -> Optional[Any]:
    """
    Get vectorstore for a specific user and document.
    
    Args:
        user_id: User ID
        doc_id: Document ID
        
    Returns:
        The vectorstore or None
    """
    return vectorstore_manager.get_user_vectorstore(user_id, doc_id)


def set_user_vectorstore(user_id: str, doc_id: str, vs: Any) -> None:
    """
    Set vectorstore for a user and document.
    
    Args:
        user_id: User ID
        doc_id: Document ID
        vs: The vectorstore object
    """
    vectorstore_manager.set_user_vectorstore(user_id, doc_id, vs)


def delete_user_vectorstore(user_id: str, doc_id: str) -> bool:
    """
    Delete vectorstore for a user and document.
    
    Args:
        user_id: User ID
        doc_id: Document ID
        
    Returns:
        True if deleted
    """
    return vectorstore_manager.delete_user_vectorstore(user_id, doc_id)


def clear_user_data(user_id: str) -> int:
    """
    Clear all data for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Number of vectorstores deleted
    """
    return vectorstore_manager.clear_user_data(user_id)
