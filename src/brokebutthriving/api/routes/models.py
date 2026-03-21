from fastapi import APIRouter

from brokebutthriving.schemas.api import ModelRegistrySummary
from brokebutthriving.services.model_registry import load_model_registry


router = APIRouter(prefix="/models", tags=["models"])


@router.get("/registry", response_model=ModelRegistrySummary)
def get_model_registry() -> ModelRegistrySummary:
    return load_model_registry()
