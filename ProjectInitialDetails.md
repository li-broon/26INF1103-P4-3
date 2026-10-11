# Project Initial Details Submission
Problem Statement and Target Users
Problem Statement:
Traditional workplace incident reporting is rigid, time-consuming, and cumbersome for some users. Especially for foreign workers who have come from other countries and have to adjust to safety reporting norms that differ from one workplace to another, alongside the language barrier. 

This system solves this by letting workers report incidents conversationally in their own native languages. Then let the AI do the translating and conversing and produce a structured JSON record that is sent to a database. The AI can also extract insights from the conversation to give even more additional data for higher-ups.

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

Use of AI
The AI will interpret any type of language input and parse all requested data points into English.
Once conversation concludes, the AI will return a structured JSON response containing the necessary data.
The AI itself will analyse the conversation and generate additional insightful metadata:
Was it a Near-Miss
Root cause categorisation
Lost Time Injury
AI’s severity rating
AI’s safety recommendation
Detected Language

Business Rules
Importance score: The various data points each have their own respective weights which is used to calculate each incident's importance. After calculation, the incidents are all sorted from most to least urgent, so safety officers see the most serious incidents first.
Completeness check: A report is only accepted once every field is filled. If any are missing, the AI asks the worker for them in their language. If the worker cannot answer after being asked twice, the field is recorded as "unknown (worker could not say)".

Repository Link:
https://github.com/li-broon/26INF1103-P4-3
