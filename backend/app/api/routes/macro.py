from fastapi import APIRouter, HTTPException

from backend.app.services.macro import MacroService, MacroServiceError

router = APIRouter(prefix="/api/macro", tags=["macro"])
service = MacroService()


@router.get("/{country}")
def get_macro_environment(country: str) -> dict:
    try:
        return service.get_current_environment(country).to_dict()
    except MacroServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
