from src.io_manager.menus.menu import Menu


# The Menu Under a Filtered Table: Turn Pages, Open a Report or its Transcript, or Go Back
class PageMenu(Menu):
    def title(self) -> str:
        return "Page Options"

    def options(self) -> list:
        return ["Next page", "Previous page", "View a full report", "View a report's transcript",
                "Back to report options"]