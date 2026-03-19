"""
Pipeline Service - Orchestrates the full AI analysis pipeline for tenders.
Coordinates data extraction, risk analysis, scoring, and proposal generation.
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Tender, Analysis, Score, Proposal
from app.services.ai_service import get_ai_service
from app.schemas.tender import TenderRisks, TenderScore, TenderProposal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineService:
    """
    Service class for running the complete tender analysis pipeline.
    Orchestrates AI extraction, risk analysis, scoring, and proposal generation.
    """
    
    def __init__(self):
        """Initialize pipeline service with AI service."""
        self.ai_service = get_ai_service()
        logger.info("PipelineService: initialized")
    
    async def run_pipeline(self, tender_id: int, db: AsyncSession) -> dict:
        """
        Run the complete analysis pipeline for a tender.
        
        Steps:
        1. Load tender from DB
        2. Extract data from raw text
        3. Analyze risks
        4. Calculate score
        5. Generate proposal
        6. Update tender status with decision engine
        
        Args:
            tender_id: ID of the tender to process
            db: Database session
            
        Returns:
            Dictionary with pipeline results and status
        """
        logger.info(f"PipelineService: Starting pipeline for tender_id={tender_id}")
        
        result = {
            "tender_id": tender_id,
            "status": "started",
            "steps_completed": [],
            "errors": []
        }
        
        # Step 1: Load tender
        try:
            tender = await self._load_tender(tender_id, db)
            if not tender:
                result["status"] = "error"
                result["errors"].append(f"Tender with id={tender_id} not found")
                return result
            result["steps_completed"].append("load")
            logger.info(f"PipelineService: Tender loaded - {tender.filename}")
        except Exception as e:
            logger.error(f"PipelineService: Error loading tender: {e}")
            result["status"] = "error"
            result["errors"].append(f"Error loading tender: {str(e)}")
            return result
        
        # Step 2: Extract data
        extracted_data = None
        try:
            raw_text = tender.raw_text or ""
            if not raw_text:
                raise ValueError("Tender has no raw_text to analyze")
            
            extracted_data = await self.ai_service.extract_data(raw_text)
            result["steps_completed"].append("extract")
            logger.info(f"PipelineService: Data extracted - title: {extracted_data.title}")
        except Exception as e:
            logger.error(f"PipelineService: Error extracting data: {e}")
            result["status"] = "error"
            result["errors"].append(f"Error extracting data: {str(e)}")
            await self._update_tender_status(tender, "extraction_failed", db)
            return result
        
        # Step 3: Analyze risks
        risks_result: Optional[TenderRisks] = None
        try:
            risks_result = await self.ai_service.analyze_risks(raw_text)
            
            # Save analysis to DB
            analysis = Analysis(
                tender_id=tender_id,
                summary=f"Risk analysis completed. Overall score: {risks_result.overall_risk_score}/100",
                risks={
                    "risks": [
                        {
                            "category": r.category,
                            "description": r.description,
                            "level": r.level.value if hasattr(r.level, 'value') else r.level,
                            "mitigation": r.mitigation
                        }
                        for r in risks_result.risks
                    ],
                    "overall_risk_score": risks_result.overall_risk_score
                }
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            
            result["steps_completed"].append("analyze_risks")
            logger.info(f"PipelineService: Risks analyzed - {len(risks_result.risks)} risks found")
        except Exception as e:
            logger.error(f"PipelineService: Error analyzing risks: {e}")
            result["errors"].append(f"Error analyzing risks: {str(e)}")
            await self._update_tender_status(tender, "analysis_failed", db)
            return result
        
        # Step 4: Calculate score
        score_result: Optional[TenderScore] = None
        try:
            score_result = await self.ai_service.score(extracted_data, risks_result)
            
            # Save score to DB
            score = Score(
                tender_id=tender_id,
                value=score_result.score,
                reason=f"Pros: {', '.join(score_result.pros[:3])}. Cons: {', '.join(score_result.cons[:3])}."
            )
            db.add(score)
            await db.commit()
            await db.refresh(score)
            
            result["steps_completed"].append("score")
            logger.info(f"PipelineService: Score calculated - {score_result.score}/100, decision: {score_result.decision}")
        except Exception as e:
            logger.error(f"PipelineService: Error calculating score: {e}")
            result["errors"].append(f"Error calculating score: {str(e)}")
            await self._update_tender_status(tender, "scoring_failed", db)
            return result
        
        # Step 5: Generate proposal
        proposal_result: Optional[TenderProposal] = None
        try:
            proposal_result = await self.ai_service.generate_proposal(extracted_data)
            
            # Save proposal to DB
            proposal = Proposal(
                tender_id=tender_id,
                text=proposal_result.proposal_text
            )
            db.add(proposal)
            await db.commit()
            await db.refresh(proposal)
            
            result["steps_completed"].append("generate_proposal")
            logger.info(f"PipelineService: Proposal generated - {len(proposal_result.proposal_text)} chars")
        except Exception as e:
            logger.error(f"PipelineService: Error generating proposal: {e}")
            result["errors"].append(f"Error generating proposal: {str(e)}")
            await self._update_tender_status(tender, "proposal_failed", db)
            return result
        
        # Step 6: Decision engine and final status update
        try:
            final_status = "completed"
            
            # Decision engine logic
            if score_result and score_result.score < 50:
                final_status = "low_priority"
                logger.info(f"PipelineService: Decision engine - LOW PRIORITY (score: {score_result.score})")
            elif score_result and score_result.score >= 80:
                final_status = "high_priority"
                logger.info(f"PipelineService: Decision engine - HIGH PRIORITY (score: {score_result.score})")
            
            await self._update_tender_status(tender, final_status, db)
            result["steps_completed"].append("status_update")
            result["status"] = "completed"
            logger.info(f"PipelineService: Pipeline completed - final status: {final_status}")
            
        except Exception as e:
            logger.error(f"PipelineService: Error updating final status: {e}")
            result["errors"].append(f"Error updating status: {str(e)}")
        
        return result
    
    async def _load_tender(self, tender_id: int, db: AsyncSession) -> Optional[Tender]:
        """Load tender from database by ID."""
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id)
        )
        return result.scalar_one_or_none()
    
    async def _update_tender_status(self, tender: Tender, status: str, db: AsyncSession):
        """Update tender status in database."""
        tender.status = status
        await db.commit()
        await db.refresh(tender)
        logger.info(f"PipelineService: Tender status updated to '{status}'")


# Singleton instance
pipeline_service: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    """Get or create PipelineService singleton."""
    global pipeline_service
    if pipeline_service is None:
        pipeline_service = PipelineService()
    return pipeline_service
