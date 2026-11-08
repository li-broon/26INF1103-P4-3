from src.io_manager.menus.menu import Menu


#child class of Menu(Main Menu)
class MainMenu(Menu):
    def title(self) -> str:
        return "Main Menu"

    def options(self) -> list:
        return ["Report a new incident (chatbot)", "View saved incident reports", "Exit"]