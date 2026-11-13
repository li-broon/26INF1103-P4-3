from src.io_manager.menus.menu import Menu


#Child Class of Menu (View Menu)
class ViewMenu(Menu):
    def title(self) -> str:
        return "Report Options"

    def options(self) -> list:
        return ["Next page", "Previous page", "Filter these reports", "View a full report",
                "View a report's transcript", "Back to the main menu"]