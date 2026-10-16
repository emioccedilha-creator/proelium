"""Interfaces opcionais. Nenhum provedor é executado nesta versão."""
from typing import Protocol

class VisionProvider(Protocol):
    def analyze(self, image: bytes, instructions: str) -> str: ...

class ImageEditor(Protocol):
    def edit(self, image: bytes, instructions: str) -> bytes: ...
