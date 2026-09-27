#Two functions for getting user input and display messages 
def get_user_input(prompt):
    user_input= input (prompt)
    return user_input

def display_messages(messages):
    print(messages)

fields= [
    ("What is your name? ", "name"), 
    ("Where did this happen? ", "location"),
    ("When did the incident occur (date and time)? ", "incident_datetime"),
    ("Please describe what happened. ", "description"),
    ("Was anyone injured? If so, describe the injury.", "injury_status"),
    ("was the person hospitalized?(Yes/No) ", "hospitalization_status"),
    ("What immediate action was taken? ", "immediate_action"),
    ("How many hours of work were stopped? ", "hours_stopped"),
    ("On a scale of 1-10, how urgent is this? ", "urgency_rating"),
]



#Collecting Data for each questions
def collect_report_data():
    report_data = {}
    for question_text, key_name in fields:
        answer =  get_user_input (question_text)
        report_data [key_name] = answer 
        
    return report_data

#Data collected will be organised and not in one whole chunk
def display_report_data(data):
    for key, value in data.items():
        print(f"{key}: {value}")

# Temporary mock standing in for the real AI Manager, so I/O Manager
# can be tested end-to-end before ai_manager.py is ready to plug in.
def fake_ai_manager(data):
    return {"status": "ok"}

# Looks up the original question text for a given key name.
# Needed for the re-prompt loop, since Logic Manager only sends back
# key names (e.g. "incident_datetime"), not the full question text.
def get_question_by_key(fields, key_name):
    for question_text, key in fields:
        if key == key_name:
            return question_text
    return None

#Run the interview only when this file is executed directly, not when imported
def main():
    data = collect_report_data()
    display_report_data(data)

    try:
        response = fake_ai_manager(data)
        display_messages(f"AI Manager response: {response}")
    except Exception as e:
        display_messages(f"Something went wrong talking to the AI Manager: {e}")

if __name__ == "__main__":
    main()

print(get_question_by_key(fields, "hours_stopped"))