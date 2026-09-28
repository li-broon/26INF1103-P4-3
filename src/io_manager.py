# ------- #
# Imports
# ------- #
import json # TEMP
from ai_manager import start_chat, send_message, check_api_key

error = check_api_key()
if error:
    print(error)
else:
    chat = start_chat()

    while True:
        result = send_message(chat, input("> "))
        print("Thinking...\n")
        if "error" in result:
            print("Error:", result["error"])
        else:
            print(result["reply"])
            if result["is_complete"]:
                print(json.dumps(result["report"], indent=2, ensure_ascii=False))  # TEMP: check final JSON
                break   # hand result["report"] to logic_manager
        