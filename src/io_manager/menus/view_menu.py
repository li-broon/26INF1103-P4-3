from src.io_manager.menus.menu import Menu


# The Menu Under the Table of All Reports: Turn Pages, Filter, Open a Report or its Transcript, or Go Back
class ViewMenu(Menu):
    def title(self) -> str:
        return "Report Options"

    def options(self) -> list:
        return ["Next page", "Previous page", "Filter these reports", "View a full report",
                "View a report's transcript", "Back to the main menu"]