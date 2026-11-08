from src.io_manager.constants import FILTER_COLUMNS
from src.io_manager.menus.menu import Menu


#The Menu Asking Which Column to Filter By; its Options Come from FILTER_COLUMNS, Plus Back
class FilterMenu(Menu):
    def title(self) -> str:
        return "Filter Reports"

    def subtitle(self) -> str:
        return "Which column would you like to filter by?"

    def options(self) -> list:
        return [heading for heading, column in FILTER_COLUMNS] + ["Back"]