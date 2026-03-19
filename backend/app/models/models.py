"""
SQLAlchemy models for Tender AI Assistant.
Uses SQLAlchemy 2.0 with DeclarativeBase.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tender(Base):
    """
    Tender document model.
    Stores uploaded tender documents and their status.
    """
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis", back_populates="tender", cascade="all, delete-orphan"
    )
    scores: Mapped[list["Score"]] = relationship(
        "Score", back_populates="tender", cascade="all, delete-orphan"
    )
    proposals: Mapped[list["Proposal"]] = relationship(
        "Proposal", back_populates="tender", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tender(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class Analysis(Base):
    """
    Analysis model.
    Stores AI-generated analysis and risks for a tender.
    """
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risks: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, tender_id={self.tender_id})>"


class Score(Base):
    """
    Score model.
    Stores detailed evaluation scores for a tender with reasons.
    Updated for Decision Support System with 3-component scoring.
    """
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False
    )
    # Component scores (0-100 each, weighted for final score)
    budget_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-40 points
    complexity_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-30 points
    competition_score: Mapped[int] = mapped_column(Integer, default=0)  # 0-30 points
    # Final score (0-100) and decision
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    decision: Mapped[str] = mapped_column(String(20), default="REVIEW")  # GO, REVIEW, REJECT
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender", back_populates="scores")

    def __repr__(self) -> str:
        return f"<Score(id={self.id}, tender_id={self.tender_id}, total={self.total_score}, decision={self.decision})>"


class Proposal(Base):
    """
    Proposal model.
    Stores generated proposals for a tender.
    """
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    tender: Mapped["Tender"] = relationship("Tender", back_populates="proposals")

    def __repr__(self) -> str:
        return f"<Proposal(id={self.id}, tender_id={self.tender_id})>"
