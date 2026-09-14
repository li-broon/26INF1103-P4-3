# Project Initial Details Submission
Problem Statement and Target Users
Problem Statement:
Traditional workplace incident reporting is rigid, time-consuming, and cumbersome for some users. Especially for foreign workers who have come from other countries and have to adjust to safety reporting norms that differ from one workplace to another, alongside the language barrier. 

This system solves this by letting workers report incidents conversationally in their own native languages. Then let the AI do the translating and parse the information given into a string of useful text that can be added into a database. The AI can also extract insights from the conversation to give even more additional data for higher-ups.

Target Users: 
Contractors: Workers themselves who can quickly report incidents in their native language without navigating complex forms.
Safety officers: They require data that is structured, categorised and accurate to ensure site safety.
Supervisors & Managers: People with leadership positions who need information on work stoppages and severe safety violations.

User Inputs
Users will type into the terminal similar to having a conversation with the AI. The user can provide all the information needed below. If they don’t, the system will prompt a back-and-forth conversation until the user provides all info.:
Name
Location
Incident date and time
Description of event
Injury status
Hospitalization status
Immediate Action Taken
Number of hours stopped
User’s subjective severity rating

Use of AI
The AI will interpret any type of language input and parse all requested data points into English.
Once conversion concludes, the AI will return a structured JSON response containing the necessary data.
The AI itself will analyse the conversion and generate additional insightful metadata:
Was it a Near-Miss
Root cause categorisation
Lost Time Injury
AI’s severity rating
AI’s safety recommendation

Business Rules
Severity Escalation: If the AI outputs its severity rating as ‘Critical’, or a worker is hospitalised, the logic manager will immediately flag the specific entry to the safety officers.
Data validation: The logic manager must check the JSON output for any missing mandatory fields. If it detects this, it will reject it. Then, it goes back to the I/O Manager to reprompt the user for the missing fields. 
High-risk root cause: If the AI categorised some incidents as ‘chemical’ or ‘electrical’. The logic manager immediately flags the specific entry to the safety officers, regardless of whether an injury occurred.

Repository Link:
https://github.com/li-broon/26_INF1103_P4-3
