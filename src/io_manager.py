# ------- #
# Imports
# ------- #

from src.ai_manager import start_chat, send_message, check_api_key
from src.logic_manager import logic

# --------------- #
# Welcome Message
# --------------- #

RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"

WELCOME = f"""

========================================================================
{CYAN}{BOLD} 
            👷 Workplace Incident Reporting Assistant 🦺{RESET}

========================================================================
{BOLD}
    👋 Hello! I'm here to help you report a workplace incident.{RESET}
    Just tell me what happened, like you're talking to a friend.
    I'll ask a few questions if anything is missing. 📝
        
        {GREEN}{BOLD}{UNDERLINE}🌏 Speak in YOUR language! Any language or a mix is OK.{RESET}

      🇬🇧  {GREEN}English{RESET}   : You can talk to me in your own language.
      🇲🇾  {GREEN}Melayu{RESET}    : Anda boleh bercakap dalam bahasa anda sendiri.
      🇨🇳  {GREEN}中文{RESET}      : 您可以用您的母语与我交谈。
      🇮🇳  {GREEN}தமிழ்{RESET}     : நீங்கள் உங்கள் சொந்த மொழியில் பேசலாம்.
      🇮🇳  {GREEN}हिन्दी{RESET}       : आप अपनी भाषा में बात कर सकते हैं।
      🇧🇩  {GREEN}বাংলা{RESET}      : আপনি আপনার নিজের ভাষায় কথা বলতে পারেন।{RESET}
    
    {RED}{BOLD}🚨 If someone is still in danger, call 995 and your supervisor FIRST! 🚨{RESET}
    {YELLOW}💬 Type your message below and press Enter to start. ⬇️{RESET}
"""

# ------------------------- #
# io_manager Main Functions
# ------------------------- #

def main():
    
    # Check if API Key Exists
    error = check_api_key()
    if error:
        print(error)
    else:
        
        # Initalise AI & Welcome User
        chat = start_chat()
        print(WELCOME)

        while True:
            result = send_message(chat, input("> ")) # User Input
            print("Thinking...\n")
            
            # Error Handling, Show Error Message
            if "error" in result:
                print("Error:", result["error"])
            else:
                print(result["reply"]) # AI Replies
                
                # If Chat is Completed, Send Completed JSON to 'logic_manager'
                if result["is_complete"]:
                    logic(result["report"])
                    break
