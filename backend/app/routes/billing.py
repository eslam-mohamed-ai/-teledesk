
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_company
from app.models import Company
from app.services.plans import PLANS, usage

router = APIRouter(prefix="/billing", tags=["billing"])
log = logging.getLogger("teledesk.billing")


class PlanIn(BaseModel):
    plan: str = Field(min_length=1, max_length=50)


@router.get("")
def billing(
    c: Company = Depends(current_company),
    db: Session = Depends(get_db),
):
    current_plan = c.plan

    if current_plan not in PLANS:
        raise HTTPException(
            status_code=500,
            detail="خطة الشركة الحالية غير معروفة",
        )

    return {
        "plan": current_plan,
        "plans": PLANS,
        "usage": usage(db, c.id, current_plan),
    }


@router.post("/plan")
def change_plan(
    body: PlanIn,
    c: Company = Depends(current_company),
):
    new_plan = body.plan.strip().lower()

    if new_plan not in PLANS:
        raise HTTPException(
            status_code=400,
            detail="خطة غير معروفة",
        )

    log.warning(
        "Plan change blocked: company_id=%s requested_plan=%s",
        c.id,
        new_plan,
    )

    raise HTTPException(
        status_code=501,
        detail="تغيير الخطط غير متاح حاليًا. يجب إتمام الدفع والتحقق منه أولًا.",
    )
