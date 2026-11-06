from src.io_manager.menu.Menu import Menu


#Child Class of Menu(PageMenu)
class PageMenu(Menu):
    def title(self) -> str:
        return "Page Options"

    def options(self) -> list:
        return [
            "Next page",
            "Previous page",
            "View a full report",
            "Back to report options",
        ]