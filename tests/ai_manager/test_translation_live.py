# ---------------- #
# Import and Setup
# ---------------- #
import difflib
import os

import pytest

from src.ai_manager import AIManager, AIServiceError, GeminiService

# Live Check Only: it Talks to the Real Gemini API, so it is Skipped Unless Asked For (CI and the Docker Test Command Stay Offline)
pytestmark = pytest.mark.skipif(os.environ.get("LIVE_AI_TESTS") != "1", reason="set LIVE_AI_TESTS=1 (with a GEMINI_API_KEY) to run the live translation check")

MAX_TURNS = 4  # Messages Allowed per Language Before the Run Counts as Failed

# Fields a Translation Error Would Change the Score or the MOM Flag Through: These Must Come Out Identical
STRUCTURED_FIELDS = ["incident_date", "incident_time", "hospitalised", "work_stoppage_hours",
                     "ai_severity", "root_cause_category", "is_near_miss", "lost_time_injury"]

# Free Text the AI Writes in English in its Own Words: Scored for Similarity, with a Floor that Only Catches a Wrong Translation
TEXT_FIELDS = ["location", "description", "injury_status", "immediate_action_taken"]
TEXT_SIMILARITY_FLOOR = 0.3

# The Same Incident in Singapore's Four Official Languages, Each Giving Every Detail in One Message, plus the Reply to
# Use if the AI Still Asks Something. English is the Reference the Others are Compared With.
# (The Malay, Chinese and Tamil Wording Should be Checked by a Native Speaker Before the Results are Quoted.)
SCENARIOS = {
    "English": {
        "expected_language": ("english",),
        "report": "My name is Muthu Raman. On 10 November 2026 at 9:30 in the morning, at the Tuas site, loading bay 2, "
                  "I slipped on oil that had leaked from the forklift and fell. I bruised my left knee but I was not sent "
                  "to hospital. We cleaned up the oil and I told my supervisor. Work stopped for 1 hour.",
        "follow_up": "Everything I know is in my message above. I do not know anything else.",
    },
    "Malay": {
        "expected_language": ("malay", "melayu"),
        "report": "Nama saya Muthu Raman. Pada 10 November 2026 jam 9:30 pagi, di tapak Tuas, pelantar pemunggahan 2, "
                  "saya tergelincir di atas minyak yang bocor dari forklift dan terjatuh. Lutut kiri saya lebam tetapi "
                  "saya tidak dihantar ke hospital. Kami membersihkan minyak itu dan saya memberitahu penyelia saya. "
                  "Kerja terhenti selama 1 jam.",
        "follow_up": "Semua yang saya tahu ada dalam mesej saya di atas. Saya tidak tahu apa-apa lagi.",
    },
    "Chinese": {
        "expected_language": ("chinese", "mandarin", "中文"),
        "report": "我叫 Muthu Raman。2026年11月10日早上9点30分，在大士工地的2号装卸区，我踩到叉车漏出的油滑倒了。"
                  "我的左膝盖瘀伤，但没有被送去医院。我们把油清理干净了，我也通知了主管。工作停了1个小时。",
        "follow_up": "我知道的都在上面的信息里了。其他的我不知道。",
    },
    "Tamil": {
        "expected_language": ("tamil", "தமிழ்"),
        "report": "என் பெயர் முத்து ராமன். 2026 நவம்பர் 10 ஆம் தேதி காலை 9:30 மணிக்கு, துவாஸ் தளத்தில், ஏற்றும் தளம் 2-ல், "
                  "ஃபோர்க்லிஃப்டில் இருந்து கசிந்த எண்ணெயில் வழுக்கி விழுந்தேன். என் இடது முழங்கால் கன்றிப் போய்விட்டது, "
                  "ஆனால் நான் மருத்துவமனைக்கு அனுப்பப்படவில்லை. நாங்கள் எண்ணெயைச் சுத்தம் செய்தோம், நான் என் "
                  "மேற்பார்வையாளரிடம் தெரிவித்தேன். வேலை 1 மணி நேரம் நின்றது.",
        "follow_up": "எனக்குத் தெரிந்த எல்லாம் மேலே உள்ள என் செய்தியில் உள்ளது. வேறு எதுவும் எனக்குத் தெரியாது.",
    },
}


# ------------ #
# Test Helpers
# ------------ #

# Report the Scenario in One Language Through the Real AI Manager, Exactly as the App Does, and Return the Finished Report
def report_in(language: str, ai_manager: AIManager) -> dict:
    scenario = SCENARIOS[language]
    conversation = ai_manager.start_conversation()
    message = scenario["report"]
    for turn in range(MAX_TURNS):
        reply = conversation.send(message)
        if reply.error:
            pytest.fail(f"{language}: the AI returned an error on turn {turn + 1}: {reply.error}")
        if reply.is_complete:
            return reply.report
        message = scenario["follow_up"]
    pytest.fail(f"{language}: the report was still not complete after {MAX_TURNS} messages (last reply: {reply.reply!r})")

# 0 to 1: How Alike Two Pieces of English Text are (1 is Identical)
def similarity(text_a, text_b) -> float:
    return difflib.SequenceMatcher(None, str(text_a).lower(), str(text_b).lower()).ratio()


# ---- #
# Test
# ---- #

# The Same Incident in Four Languages Must Give the Same Structured Report; the Free Text is Scored and Printed (Run with -s)
def test_same_incident_in_four_languages_gives_the_same_report():
    try:
        ai_manager = AIManager(GeminiService())
    except AIServiceError as error:
        pytest.skip(error.message.splitlines()[0])

    reference = report_in("English", ai_manager)
    problems = []
    for language in ("Malay", "Chinese", "Tamil"):
        report = report_in(language, ai_manager)
        print(f"\n=== {language} vs English ===")
        print(f"{'field':24} {'result':10} {'English':34} {language}")

        detected = str(report.get("detected_language", "")).lower()
        language_ok = any(name in detected for name in SCENARIOS[language]["expected_language"])
        print(f"{'detected_language':24} {'ok' if language_ok else 'WRONG':10} {'':34} {report.get('detected_language')}")
        if not language_ok:
            problems.append(f"{language}: detected_language was {report.get('detected_language')!r}")

        for field in STRUCTURED_FIELDS:
            same = report.get(field) == reference.get(field)
            print(f"{field:24} {'same' if same else 'DIFFERENT':10} {str(reference.get(field)):34} {report.get(field)}")
            if not same:
                problems.append(f"{language}: {field} was {report.get(field)!r}, English gave {reference.get(field)!r}")

        # Free Text is Long, so Each Version Gets its Own Line Under the Score
        for field in TEXT_FIELDS:
            score = similarity(reference.get(field), report.get(field))
            print(f"{field:24} {score:.2f}\n{'':6}English: {reference.get(field)}\n{'':6}{language + ':':9}{report.get(field)}")
            if score < TEXT_SIMILARITY_FLOOR:
                problems.append(f"{language}: {field} similarity {score:.2f} is below {TEXT_SIMILARITY_FLOOR}")

    assert not problems, "\n".join(problems)
