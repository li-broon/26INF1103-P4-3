# Public parts of the Logic Manager. "logic" keeps `from src.logic_manager import logic` working for main.py and the GUI
from src.logic_manager.exceptions import InvalidReportError
from src.logic_manager.logic_manager import LogicManager, logic
from src.logic_manager.models.evaluation import Evaluation
from src.logic_manager.models.logic_config import LogicConfig
from src.logic_manager.models.save_outcome import SaveOutcome

__all__ = ["Evaluation", "InvalidReportError", "LogicConfig", "LogicManager", "SaveOutcome", "logic"]