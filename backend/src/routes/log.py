from fastapi import APIRouter, Body
from ..infra.db import usage_logs
from ..models.schemas import UsageLogEvent

router = APIRouter(prefix="/log", tags=["Logging"])

@router.post("", status_code=204)
def post_log(evt: UsageLogEvent):
    usage_logs.insert_one(evt.model_dump())
    return