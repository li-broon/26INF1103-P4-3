# Two core I/O functions: get_user_input() asks the worker a question and
# returns their raw typed answer; display_messages() shows a message back
# to them. Every other function in this file builds on top of these two.
def get_user_input(prompt):
    user_input = input(prompt)
    return user_input

def display_messages(messages):
    print(messages)

# The 9 required report fields, as (question_text, key_name) pairs.
# key_name must match exactly what ai_manager.py and logic_manager.py
# expect, since they look up data using these same strings.
fields = [
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


# Asks every question in fields, in order, and builds a dict mapping
# each key_name to the worker's raw answer (no validation/parsing here —
# that's the AI Manager's job, per the project spec).
def collect_report_data():
    report_data = {}
    for question_text, key_name in fields:
        answer = get_user_input(question_text)
        report_data[key_name] = answer 
        
    return report_data

# Prints the collected report one field per line (key: value),
# so it's readable instead of one dumped chunk.
def display_report_data(data):
    for key, value in data.items():
        print(f"{key}: {value}")

# Temporary mock standing in for the real AI Manager, so I/O Manager
# can be tested end-to-end before ai_manager.py is ready to plug in.
# Replace with the real ai_manager call in Stage 6.
def fake_ai_manager(data):
    return {"status": "ok"}

# Looks up the original question text for a given key name.
# Needed for the re-prompt loop, since Logic Manager only sends back
# key names (e.g. "incident_datetime"), not the full question text.
# Returns None if the key isn't found in fields.
def get_question_by_key(fields, key_name):
    for question_text, key in fields:
        if key == key_name:
            return question_text
    return None

# Takes a list of issues from Logic Manager (each with a "field" key name
# and a "reason"), and re-asks only those specific questions.
# Updates report_data in place with the corrected answers and returns it.
def reprompt_for_issues(report_data, issues):
    for issue in issues:
        key_name = issue["field"]
        question_text = get_question_by_key(fields, key_name)

        if question_text is None:
            display_messages(f"Warning: no question found for field '{key_name}'")
            continue

        display_messages(f"There was an issue with your answer: {issue['reason']}")
        answer = get_user_input(question_text)
        report_data[key_name] = answer

    return report_data


# Runs the full interview: collect answers, send to AI Manager (mocked
# for now), and handle the response. Wrapped in main() + the __name__
# check below so importing this file elsewhere doesn't auto-trigger
# a full interview.
def main():
    data = collect_report_data()
    display_report_data(data)

    try:
        response = fake_ai_manager(data)
        display_messages(f"AI Manager response: {response}")
    except Exception as e:
        display_messages(f"Something went wrong talking to the AI Manager: {e}")

    # --- Temporary test for reprompt_for_issues(), remove before Stage 7 cleanup ---
    # fake_issues = [
    #     {"field": "hours_stopped", "reason": "must be a number"},
    #     {"field": "incident_datetime", "reason": "missing date"}
    # ]
    # data = reprompt_for_issues(data, fake_issues)
    # display_report_data(data)

if __name__ == "__main__":
    main()