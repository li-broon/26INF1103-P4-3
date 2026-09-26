#Two functions for getting user input and display messages 
def get_user_input(prompt):
    user_input= input (prompt)
    return user_input

def display_messages(messages):
    print(messages)

fields= [
    ("What is your name?", "name"), 
    ("Where did this happen?", "location"),
    ("When did the incident occur (date and time)?", "incident_datetime"),
    ("Please descirbe what happened. ", "description"),
    ("Was anyone injured? If so, describe the injury.", "injury_status"),
    ("was the person hospitalized?(Yes/No)", "hospitalization_status"),
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

data = collect_report_data()
print(data)