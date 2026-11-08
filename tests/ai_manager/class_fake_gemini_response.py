# Fake Gemini Reply (Only the .text the Service Reads)
class FakeGeminiResponse:
    def __init__(self, text: str):
        self.text = text
