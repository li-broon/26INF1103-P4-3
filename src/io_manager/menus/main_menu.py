from src.io_manager.menus.menu import Menu


# The First Menu Shown: Report, View Reports, Charts or Exit
class MainMenu(Menu):
    def title(self) -> str:
        return "Main Menu"

    def options(self) -> list:
        return ["Report a new incident (chatbot)", "View saved incident reports", "View charts", "Exit"]