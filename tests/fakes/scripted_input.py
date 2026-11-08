# Stands in for the Keyboard: Pass .read to Anything that Normally Calls input(), and it Hands Back the Answers in Order
class ScriptedInput:
    def __init__(self, *answers: str):
        self._answers = list(answers)

    def read(self, prompt: str) -> str:
        return self._answers.pop(0)
