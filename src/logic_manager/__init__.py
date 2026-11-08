# Keeps `from src.logic_manager import logic` working after the split into one file per class
from src.logic_manager.logic_manager import LogicManager, logic
from src.logic_manager.models.save_outcome import SaveOutcome

__all__ = ["LogicManager", "SaveOutcome", "logic"]
