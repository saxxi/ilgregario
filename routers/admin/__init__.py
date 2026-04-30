from fastapi import APIRouter

from .overview import router as _overview
from .users import router as _users
from .athletes import router as _athletes
from .races import router as _races
from .seasons import router as _seasons

router = APIRouter()
router.include_router(_overview)
router.include_router(_users)
router.include_router(_athletes)
router.include_router(_races)
router.include_router(_seasons)
