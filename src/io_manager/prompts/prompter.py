from src.io_manager.constants import CANCEL_WORDS, RESET, YELLOW


#Asks the User for Input and Keeps Asking Until the Answer is Valid
class Prompter:
    def __init__(self, read=input, cancel_words=CANCEL_WORDS):
        self._read=read
        self._cancel_words= cancel_words

    def ask_yes_no(self, question: str) -> bool:
        while True:
            answer = self._read(f"{question} (y/n): ").strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            print(f"{YELLOW}Please type 'y' for yes or 'n' for no.{RESET}")

    def ask_number(self,prompt:str, low:int, high: int) -> int: 
        while True: 
            user_input = self._read(prompt).strip()

            #rejects blank input
            if user_input =="":
                print(f"{YELLOW}This can't be left blank. Please type a number.{RESET}")
                continue 
            
            try:
                choice= int(user_input)
            except ValueError:
                print(f"{YELLOW}'{user_input}' is not a number. Please type a whole number.{RESET}")
                continue
            if low <= choice <= high:
                return choice
            print(f"{YELLOW}{choice} is not an option. Please type a number from {low} to {high}.{RESET}")
