from typing import Type

from . import resources, subjects
from .base import BaseModel


__all__ = [
    "item",
    "resources",
    "subjects",
]


def resolve_model(model_name: str) -> type[BaseModel]:
    model_cls = BaseModel.registry._class_registry.get(model_name)
    if isinstance(model_cls, type) and issubclass(model_cls, BaseModel):
        return model_cls
    raise LookupError(f"Model `{model_name}` is not registered.")
