from fastapi import APIRouter
from ..models.schemas import UsageLogEvent
from ..models import usage_log as ulog_model

router = APIRouter(prefix="/log", tags=["Logging"])

@router.post("", status_code=204)
def post_log(evt: UsageLogEvent):
    ulog_model.log(evt.model_dump())
    return