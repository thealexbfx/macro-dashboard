from fastapi import APIRouter
from backend.app.services.home import HomeService

router = APIRouter(prefix="/api/home", tags=["home"])

@router.get("")
def home_snapshot():
    return HomeService().snapshot()
