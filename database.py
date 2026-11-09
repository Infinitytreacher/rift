# SPDX-FileCopyrightText: 2026 Siddhant Tiwari
# SPDX-License-Identifier: AGPL-3.0-only
# RIFT is distributed without warranty. See LICENSE and COPYRIGHT.md.


"""
SQLite Database Module for IoT Anonymous Feedback System
Handles connection setup, schema creation, and CRUD operations.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Database file path
DATABASE_PATH = os.environ.get(
    "RIFT_DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "feedback_system.db")
)


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    Ensures proper connection handling and cleanup.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """
    Initialize the database with the required schema.
    Creates tables if they don't exist.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                transcript_text TEXT
            )
        """)
        
        # Create Topics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                topic_name TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Create Feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 10),
                submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
            )
        """)
        
        conn.commit()
        print("Database initialized successfully.")


# ==================== Session Operations ====================

def create_session(transcript_text: str) -> int:
    """
    Create a new lecture session with transcript.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (transcript_text, timestamp) VALUES (?, ?)",
            (transcript_text, datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid


def get_latest_session() -> Optional[Dict[str, Any]]:
    """
    Get the most recent session.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, timestamp, transcript_text 
            FROM sessions 
            ORDER BY session_id DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None


def get_session_by_id(session_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a session by its ID.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_id, timestamp, transcript_text FROM sessions WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


# ==================== Topic Operations ====================

def create_topics(session_id: int, topic_names: List[str]) -> List[int]:
    """
    Create multiple topics for a session.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        topic_ids = []
        for topic_name in topic_names:
            cursor.execute(
                "INSERT INTO topics (session_id, topic_name) VALUES (?, ?)",
                (session_id, topic_name)
            )
            topic_ids.append(cursor.lastrowid)
        conn.commit()
        return topic_ids


def get_topics_by_session(session_id: int) -> List[Dict[str, Any]]:
    """
    Get all topics for a specific session.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT topic_id, session_id, topic_name FROM topics WHERE session_id = ?",
            (session_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_latest_topics() -> List[Dict[str, Any]]:
    """
    Get all topics from the most recent session.
    Fixed: Removed LIMIT 5 to allow for the dynamic 5-10 topic bounds.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT topic_id, session_id, topic_name 
            FROM topics 
            WHERE session_id = (SELECT MAX(session_id) FROM sessions)
            ORDER BY topic_id ASC
        """)
        return [dict(row) for row in cursor.fetchall()]


# ==================== Feedback Operations ====================

def submit_feedback(topic_id: int, rating: int) -> int:
    """
    Submit a feedback rating for a topic.
    """
    if not 1 <= rating <= 10:
        raise ValueError("Rating must be between 1 and 10")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (topic_id, rating, submitted_at) VALUES (?, ?, ?)",
            (topic_id, rating, datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid


def submit_bulk_feedback(feedback_data: List[Dict[str, int]]) -> List[int]:
    """
    Submit multiple feedback ratings at once.
    """
    feedback_ids = []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for item in feedback_data:
            if not 1 <= item['rating'] <= 10:
                raise ValueError(f"Rating must be between 1 and 10, got {item['rating']}")
            cursor.execute(
                "INSERT INTO feedback (topic_id, rating, submitted_at) VALUES (?, ?, ?)",
                (item['topic_id'], item['rating'], datetime.now().isoformat())
            )
            feedback_ids.append(cursor.lastrowid)
        conn.commit()
    return feedback_ids


def get_feedback_by_topic(topic_id: int) -> List[Dict[str, Any]]:
    """
    Get all feedback for a specific topic.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT feedback_id, topic_id, rating, submitted_at FROM feedback WHERE topic_id = ?",
            (topic_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


# ==================== Statistics Operations ====================

def get_dashboard_stats() -> List[Dict[str, Any]]:
    """
    Calculate mean and variance of ratings per topic for the latest session.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                t.topic_id,
                t.topic_name,
                COUNT(f.rating) as response_count,
                AVG(f.rating) as avg_rating,
                COALESCE(
                    SUM((f.rating - sub.avg_rating) * (f.rating - sub.avg_rating)) / COUNT(f.rating),
                    0
                ) as variance
            FROM topics t
            LEFT JOIN feedback f ON t.topic_id = f.topic_id
            INNER JOIN (
                SELECT t2.topic_id, AVG(f2.rating) as avg_rating
                FROM topics t2
                LEFT JOIN feedback f2 ON t2.topic_id = f2.topic_id
                GROUP BY t2.topic_id
            ) sub ON t.topic_id = sub.topic_id
            WHERE t.session_id = (SELECT MAX(session_id) FROM sessions)
            GROUP BY t.topic_id
            ORDER BY t.topic_id ASC
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'topic_id': row['topic_id'],
                'topic_name': row['topic_name'],
                'response_count': row['response_count'] or 0,
                'avg_rating': round(row['avg_rating'], 2) if row['avg_rating'] is not None else None,
                'variance': round(row['variance'], 2) if row['variance'] is not None else 0
            })
        return results


def get_topic_stats(topic_id: int) -> Optional[Dict[str, Any]]:
    """
    Get statistics for a specific topic.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                t.topic_id,
                t.topic_name,
                COUNT(f.rating) as response_count,
                AVG(f.rating) as avg_rating,
                MIN(f.rating) as min_rating,
                MAX(f.rating) as max_rating
            FROM topics t
            LEFT JOIN feedback f ON t.topic_id = f.topic_id
            WHERE t.topic_id = ?
            GROUP BY t.topic_id
        """, (topic_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'topic_id': row['topic_id'],
                'topic_name': row['topic_name'],
                'response_count': row['response_count'] or 0,
                'avg_rating': round(row['avg_rating'], 2) if row['avg_rating'] is not None else None,
                'min_rating': row['min_rating'],
                'max_rating': row['max_rating']
            }
        return None


# ==================== Utility Functions ====================

def clear_all_data():
    """
    Clear all data from the database (for testing purposes).
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM feedback")
        cursor.execute("DELETE FROM topics")
        cursor.execute("DELETE FROM sessions")
        conn.commit()


def database_exists() -> bool:
    """
    Check if the database file exists.
    """
    return os.path.exists(DATABASE_PATH)


# Initialize database on module import
if __name__ == "__main__":
    init_database()
    print("Database initialization complete.")
