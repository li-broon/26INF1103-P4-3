# Stands in for the keyboard: pass .read to anything that normally calls input(), and it hands back the answers in order
class ScriptedInput:
    def __init__(self, *answers: str):
        self._answers = list(answers)

    def read(self, prompt: str) -> str:
        return self._answers.pop(0)
