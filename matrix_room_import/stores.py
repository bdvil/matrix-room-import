from dataclasses import dataclass
from pathlib import Path

txn_store: list[str] = []

room_stores: list[str] = ["!fRJVGlWMSoaKdOdUAI:dvil.fr"]


@dataclass
class Process:
    path: Path
    event_id: str
    room_id: str


process_queue: list[Process] = []


rooms_to_remove: dict[str, str] = {}
"""Keys are message events, values are room ids."""
