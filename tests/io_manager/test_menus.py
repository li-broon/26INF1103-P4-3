# ------- #
# Imports
# ------- #

import contextlib
from io import StringIO

from src.io_manager.menus.filter_menu import FilterMenu
from src.io_manager.menus.main_menu import MainMenu
from src.io_manager.menus.menu import Menu
from src.io_manager.menus.page_menu import PageMenu
from src.io_manager.menus.view_menu import ViewMenu
from src.io_manager.prompts.prompter import Prompter
from tests.fakes.scripted_input import ScriptedInput


# Tests for the Menu Abstract Class and its Four Child Menus
class TestMenus:

    # Test that Menu is abstract: Python must refuse to create a plain Menu
    def test_menu_is_abstract(self):
        try:
            Menu(Prompter())
            assert False, "Menu should be abstract"
        except TypeError:
            pass

    # Every menu shares show() but has its own options: the same code accepts 3 on the main menu, 5 on the view menu and 4 on the page menu
    def test_menus_accept_their_own_last_option(self):
        menus = [(MainMenu, 3), (ViewMenu, 5), (PageMenu, 4), (FilterMenu, 8)]
        for menu_class, last_option in menus:
            keyboard = ScriptedInput(str(last_option + 1), str(last_option))
            menu = menu_class(Prompter(read=keyboard.read))
            with contextlib.redirect_stdout(StringIO()) as out:
                choice = menu.show()
            assert choice == last_option                                     # the last real option is accepted
            assert f"{last_option + 1} is not an option" in out.getvalue()   # one past the end is rejected
