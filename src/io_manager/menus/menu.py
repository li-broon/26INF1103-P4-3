#A Numbered Menu: Shows a Title and Options, then Asks the User to Pick One (Child Menus Say WHAT to Show, the Parent Shows and Asks)

from abc import ABC, abstractmethod

from src.io_manager.constants import BOLD, CYAN, GREEN, RESET
from src.io_manager.prompts.prompter import Prompter


class Menu(ABC):
    def __init__(self, prompter: Prompter):
        self._prompter = prompter   # The shared Prompter, passed in (the menu uses it but doesn't own it)

    # Every child menu must say what its title is
    @abstractmethod 
    def title(self) -> str:
        pass

    # Every child menu MUST list its options, in order
    @abstractmethod
    def options(self) -> list:
        pass

    # a child menu that needs one overrides this method
    def subtitle(self) -> str:
        return ""
    
    # Same for every menu: print the title box and numbered options, then ask for a valid number
    def show(self) -> int:
        line = "=" * 72
        print(f"\n{line}\n{CYAN}{BOLD}{self.title().center(72)}{RESET}\n{line}")

        if self.subtitle():
            print(f"      {self.subtitle()}")

        options = self.options()
        for number, label in enumerate(options, start=1):
            print(f"      {GREEN}{BOLD}{number}{RESET}.  {label}")
        return self._prompter.ask_number(f"Choose an option (1-{len(options)}): ", 1, len(options))