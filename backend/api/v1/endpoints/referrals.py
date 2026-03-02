import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.schemas.referral import ReferralStatsResponse
from backend.services.referral_service import ReferralService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get referral statistics for current user.
    """
    service = ReferralService(db)
    stats = await service.get_referrer_stats(current_user.id)
    return stats


@router.get("/code")
async def get_referral_code(
    current_user=Depends(get_current_user),
):
    """
    Get current user's referral code.
    """
    return {
        "referral_code": current_user.referral_code,
        "referral_url": f"https://yourapp.com/register?ref={current_user.referral_code}",
    }
