from src.io_manager.menus.menu import Menu


#Child Class of Menu(PageMenu)
class PageMenu(Menu):
    def title(self) -> str:
        return "Page Options"

    def options(self) -> list:
        return ["Next page", "Previous page", "View a full report", "View a report's conversation (untranslated)",
                "Back to report options"]