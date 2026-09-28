from typing import Dict, Any, List
from datetime import datetime, timezone
from ..schemas.agent_state import AgentState
from ..observability.logger import logger


def detect_query_language(text: str, profile_lang: str = "en") -> str:
    """Detects Indian script in user query or defaults to user profile language."""
    if not text:
        return profile_lang or "en"
    for ch in text:
        code = ord(ch)
        if 0x0900 <= code <= 0x097F:
            return "mr" if profile_lang == "mr" else "hi"
        elif 0x0B80 <= code <= 0x0BFF:
            return "ta"
        elif 0x0C00 <= code <= 0x0C7F:
            return "te"
        elif 0x0980 <= code <= 0x09FF:
            return "bn"
        elif 0x0A80 <= code <= 0x0AFF:
            return "gu"
        elif 0x0C80 <= code <= 0x0CFF:
            return "kn"
        elif 0x0D00 <= code <= 0x0D7F:
            return "ml"
        elif 0x0A00 <= code <= 0x0A7F:
            return "pa"
        elif 0x0B00 <= code <= 0x0B7F:
            return "or"
        elif 0x0600 <= code <= 0x06FF:
            return "ur"
    return profile_lang or "en"


CLARIFICATION_BY_LANG: Dict[str, str] = {
    "en": "Please specify your departure harbor, coastal location name, or GPS coordinates (latitude and longitude) to assess marine safety and fishing zones.",
    "hi": "कृपया समुद्री सुरक्षा और मत्स्य क्षेत्रों के सटीक विश्लेषण के लिए अपना बंदरगाह, तटीय स्थान का नाम या जीपीएस निर्देशांक (अक्षांश और देशांतर) बताएं।",
    "mr": "कृपया सागरी सुरक्षा आणि मासेमारी क्षेत्राच्या विश्लेषणासाठी आपले बंदर, किनारी ठिकाणाचे नाव किंवा जीपीएस निर्देशांक (अक्षांश आणि रेखांश) सांगा.",
    "ta": "கடல் பாதுகாப்பு மற்றும் மீன்பிடி மண்டலங்களை கணக்கிட தயவுசெய்து உங்கள் துறைமுகம், கடலோர இடம் அல்லது ஜிபிஎஸ் ஆயத்தொலைவுகளை (அட்சரேகை மற்றும் தீர்க்கரேகை) குறிப்பிடவும்.",
    "te": "సముద్ర భద్రత మరియు చేపల వేట మండలాలను విశ్లేషించడానికి దయచేసి మీ నౌకాశ్రయం, తీరప్రాంత ప్రదేశం పేరు లేదా GPS కోఆర్డినేట్లను పేర్కొనండి.",
    "bn": "সামুদ্রিক নিরাপত্তা এবং সম্ভাব্য মৎস্য অঞ্চল মূল্যায়নের জন্য অনুগ্রহ করে আপনার বন্দর, উপকূলীয় স্থান বা জিপিএস স্থানাঙ্ক উল্লেখ করুন।",
    "gu": "દરિયાઈ સુરક્ષા અને સંભવિત મત્સ્ય ઝોનની તપાસ માટે કૃપા કરીને તમારા બંદર, દરિયાકાંઠાના સ્થળનું નામ અથવા જીપીએસ કોઓર્ડિનેટ્સ જણાવો.",
    "kn": "ಸಾಗರ ಸುರಕ್ಷತೆ ಮತ್ತು ಮೀನುಗಾರಿಕೆ ವಲಯಗಳನ್ನು ವಿಶ್ಲೇಷಿಸಲು ದಯವಿಟ್ಟು ನಿಮ್ಮ ಬಂದರು, ಕರಾವಳಿ ಸ್ಥಳ ಅಥವಾ ಜಿಪಿಎಸ್ ನಿರ್ದೇಶಾಂಕಗಳನ್ನು ತಿಳಿಸಿ.",
    "ml": "സമുദ്ര സുരക്ഷയും മത്സ്യബന്ധന മേഖലകളും പരിശോധിക്കാൻ ദയവായി നിങ്ങളുടെ തുറമുഖം, തീരദേശ സ്ഥലം അല്ലെങ്കിൽ ജിപിഎസ് കോർഡിനേറ്റുകൾ വ്യക്തമാക്കുക.",
    "pa": "ਸਮੁੰਦਰੀ ਸੁਰੱਖਿਆ ਅਤੇ ਮੱਛੀ ਫੜਨ ਦੇ ਖੇਤਰਾਂ ਦੀ ਜਾਂਚ ਲਈ ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਬੰਦਰਗਾਹ, ਤੱਟਵਰਤੀ ਸਥਾਨ ਜਾਂ GPS ਨਿਰਦੇਸ਼ਾਂਕ ਦੱਸੋ।",
    "or": "ସାମୁଦ୍ରିକ ସୁରକ୍ଷା ଓ ମତ୍ସ୍ୟ କ୍ଷେତ୍ର ଯାଞ୍ଚ ପାଇଁ ଦୟାକରି ଆପଣଙ୍କ ବନ୍ଦର, ଉପକୂଳବର୍ତ୍ତୀ ସ୍ଥାନ ବା ଜିପିଏସ୍ ନିର୍ଦ୍ଦେଶାଙ୍କ ପ୍ରଦାନ କରନ୍ତୁ।",
    "ur": "سمندری تحفظ اور ماہی گیری کے زون کے جائزے کے لیے برائے مہربانی اپنی بندرگاہ، ساحلی مقام یا GPS کوآرڈینیٹس بتائیں۔",
    "hinglish": "Kripya marine safety aur fishing zones ke analysis ke liye apna departure harbor, coastal location ya GPS coordinates (latitude/longitude) batayein.",
}


class PlannerAgent:
    """
    Query Intake and Planner Agent.
    Validates user query, classifies intent with multilingual keyword recognition,
    checks location availability, and generates execution steps.
    """

    SUPPORTED_INTENTS = [
        "safety_check",
        "find_pfz",
        "route_safety",
        "marine_status",
        "authority_monitoring",
    ]

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        query = state.get("query", "").strip()
        location = state.get("location") or {}
        user_profile = state.get("user_profile") or {}
        intent = state.get("intent")

        lang = detect_query_language(query, user_profile.get("language", "en"))
        user_profile["language"] = lang

        logger.info(f"Planner processing query in '{lang}': '{query}'")

        # 1. Infer intent if not explicitly supplied
        if not intent or intent not in self.SUPPORTED_INTENTS:
            q_lower = query.lower()
            pfz_kw = [
                "pfz", "fish", "fishing", "catch", "chlorophyll", "tuna", "mackerel", "sardine",
                "मछली", "मत्स्य", "शिकार", "पकड़ना", "मासे", "मासेमारी", "மீன்", "மீன்பிடி", "చేపలు", "చేపల",
                "মাছ", "মৎস্য", "માછલી", "મત્સ્ય", "ಮೀನು", "ಮತ್ಸ್ಯ", "മത്സ്യം", "മത്സ്യബന്ധനം",
                "ਮੱਛੀ", "ਮੱਛੀਆਂ", "ମାଛ", "ମତ୍ସ୍ୟ", "مچھلی", "مچھلیاں", "machli", "meen", "maasa"
            ]
            route_kw = [
                "route", "waypoint", "passage", "boundary", "navigation", "distance", "heading", "bearing",
                "रास्ता", "मार्ग", "दूरी", "दिशा", "नाविक", "नेविगेशन", "रस्ता", "दिशा", "मार्गक्रमण",
                "வழி", "பாதை", "திசை", "దారి", "మార్గం", "দিశ", "পথ", "রাস্তা", "રસ્તો", "માર્ગ",
                "ದಾರಿ", "ಮಾರ್ಗ", "വഴി", "പാത", "ਰਾਹ", "ਰਸਤਾ", "ବାଟ", "ରାସ୍ତା", "راستہ", "منزل"
            ]
            status_kw = [
                "harbor", "status", "sea state", "tide", "weather", "wave", "swell", "wind", "temp", "current",
                "मौसम", "हवा", "लहर", "समुद्र", "ज्वार", "भाटा", "तापमान", "लाटा", "हवामान", "भरती", "ओहोटी",
                "வானிலை", "காற்று", "அலை", "கடல்", "వాతావరణం", "గాలి", "అలలు", "సముద్రం",
                "আবহাওয়া", "বাতাস", "ঢেউ", "સમુદ્ર", "મોજા", "પવન", "હવામાન", "ಹವಾಮಾನ", "ಗಾಳಿ",
                "കാലാവസ്ഥ", "കാറ്റ്", "തിരമാല", "ਮੌਸਮ", "ਹਵਾ", "ਪਾଣିପାଗ", "ପବନ", "موسم", "ہوا"
            ]
            auth_kw = ["vessel", "patrol", "surveillance", "authority", "navy", "coastguard", "रक्षक", "गश्त", "तटरक्षक"]

            if any(w in q_lower for w in pfz_kw):
                intent = "find_pfz"
            elif any(w in q_lower for w in route_kw):
                intent = "route_safety"
            elif any(w in q_lower for w in status_kw):
                intent = "marine_status"
            elif any(w in q_lower for w in auth_kw):
                intent = "authority_monitoring"
            else:
                intent = "safety_check"

        # 2. Check for missing location when required
        has_coords = (location.get("latitude") is not None) and (location.get("longitude") is not None)
        has_name = bool(location.get("name"))

        clarification = None
        if not has_coords and not has_name:
            clarification = CLARIFICATION_BY_LANG.get(lang, CLARIFICATION_BY_LANG["en"])

        # 3. Formulate execution plan
        plan: List[str] = [
            "resolve_location",
            "fetch_marine_data",
            "fetch_weather_sea_state",
            "retrieve_semantic_memory",
            "geospatial_safety_analysis",
            "evaluate_deterministic_safety",
            "synthesize_grounded_response",
        ]

        trace_entry = {
            "agent": "planner",
            "status": "completed" if not clarification else "skipped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Intent: {intent}, Language: {lang}, Planned steps: {len(plan)}",
        }

        current_traces = list(state.get("agent_traces") or [])
        current_traces.append(trace_entry)

        return {
            "intent": intent,
            "user_profile": user_profile,
            "execution_plan": plan,
            "clarification_question": clarification,
            "agent_traces": current_traces,
            "status": "clarification_required" if clarification else "running",
        }


planner_agent = PlannerAgent()

