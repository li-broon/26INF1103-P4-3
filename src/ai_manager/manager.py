# --Class that Creates a New IncidentConversation for Each Worker, and Holds the AIService and Field Definitions-- #

# ------- #
# Imports
# ------- #

from src.ai_manager.constants import SEVERITY_LEVELS, ROOT_CAUSES, UNKNOWN_VALUE
from src.ai_manager.fields.text_field import TextField
from src.ai_manager.fields.location_field import LocationField
from src.ai_manager.fields.date_field import DateField
from src.ai_manager.fields.time_field import TimeField
from src.ai_manager.fields.boolean_field import BooleanField
from src.ai_manager.fields.number_field import NumberField
from src.ai_manager.fields.choice_field import ChoiceField
from src.ai_manager.fields.field_set import FieldSet
from src.ai_manager.services.ai_service import AIService
from src.ai_manager.conversation.analysis_task import AnalysisTask
from src.ai_manager.conversation.incident_conversation import IncidentConversation

# ----- #
# Class
# ----- #

class AIManager:
    def __init__(self, service: AIService):
        self._service = service

        # Details the AI Collects from the Worker
        self._worker_fields = FieldSet([
            TextField("reporter_name", "full name of the person reporting"),
            LocationField("location", "from the biggest place to the smallest, separated by commas: main site FIRST, then the "
                                      "exact area, then optionally an even more exact spot (e.g. 'Tuas site, loading bay 2' or "
                                      "'Jurong Island, Block A, level 3'); never put a smaller area before the main site "
                                      "(not 'loading bay 2, Tuas site'); if only the exact area is not known, write the site "
                                      f"then ', {UNKNOWN_VALUE}'"),
            DateField("incident_date", "date in YYYY-MM-DD"),
            TimeField("incident_time", "time in 24h HH:MM", allows_unknown=True),
            TextField("description", "what happened, in clear English"),
            TextField("injury_status", "who was hurt and how, or 'no injury'"),
            BooleanField("hospitalised", "true if the injured person was sent to hospital, otherwise false"),
            TextField("immediate_action_taken", "what was done straight after"),
            NumberField("work_stoppage_hours", "hours work was stopped, 0 if none", allows_unknown=True),
        ])

        # Details the AI Works Out Itself once the Report is Complete
        self._analysis_fields = FieldSet([
            TextField("detected_language", "language(s) the worker wrote in"),
            ChoiceField("ai_severity", SEVERITY_LEVELS),
            BooleanField("is_near_miss", "true if nobody was hurt and nothing was damaged"),
            ChoiceField("root_cause_category", ROOT_CAUSES),
            BooleanField("lost_time_injury", "true if the injured person cannot work their next shift"),
            TextField("safety_recommendation", "practical actions the safety officer should take"),
        ])

        self._analysis_task = AnalysisTask(service, self._worker_fields, self._analysis_fields)

    # Start a New Report Conversation
    def start_conversation(self) -> IncidentConversation:
        return IncidentConversation(self._service, self._worker_fields, self._analysis_fields, self._analysis_task)
