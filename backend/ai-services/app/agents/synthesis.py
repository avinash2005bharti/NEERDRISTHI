from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from ..schemas.agent_state import AgentState
from ..services.groq_client import groq_client
from ..observability.logger import logger


class GroundedSynthesisModel(BaseModel):
    explanation: str = Field(default="ORCA marine reasoning evaluated verified telemetry and deterministic safety protocol.", description="Multilingual, grounded reasoning explaining the deterministic safety verdict")
    data_gap_summary: str = Field(default="Telemetry status evaluated against official observation benchmarks.", description="Explicit summary of unconfigured or missing telemetry feeds in requested language")
    mandatory_safeguard: str = Field(default="Exercise standard maritime vigilance and monitor VHF Channel 16.", description="Actionable safety precaution in requested language")


LANG_NAMES = {
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "mr": "Marathi (मराठी)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "bn": "Bengali (বাংলা)",
    "gu": "Gujarati (ગુજરાતી)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "ml": "Malayalam (മലയാളം)",
    "pa": "Punjabi (ਪੰਜਾਬੀ)",
    "or": "Odia (ଓଡ଼ିଆ)",
    "ur": "Urdu (اردو)",
    "hinglish": "Hinglish (Hindi in Roman script)",
}

SYNTHESIS_TEMPLATES: Dict[str, Dict[str, str]] = {
    "hi": {
        "header": "ORCA समुद्री सुरक्षा विश्लेषण: [{recommendation}] (जोखिम स्तर: {risk_level}, स्कोर: {risk_score}/100, विश्वसनीयता: {confidence_score}%)।",
        "vessel": "नाव/जहाज श्रेणी: {vessel}।",
        "all_online": "सभी प्रमुख समुद्री टेलीमेट्री स्रोत सक्रिय हैं।",
        "gaps": "टेलीमेट्री अंतराल: {gaps}।",
        "no_rules": "कोई सुरक्षा सीमा पार नहीं हुई है।",
        "rules": "सक्रिय सुरक्षा नियम: {rules}।",
        "directive": "सुरक्षा निर्देश: {action}"
    },
    "mr": {
        "header": "ORCA सागरी सुरक्षा मूल्यांकन: [{recommendation}] (धोका पातळी: {risk_level}, गुण: {risk_score}/100, विश्वासार्हता: {confidence_score}%)।",
        "vessel": "बोटीचा प्रकार: {vessel}।",
        "all_online": "सर्व प्राथमिक सागरी टेलीमेट्री स्रोत सक्रिय आहेत.",
        "gaps": "माहिती अंतराल: {gaps}.",
        "no_rules": "कोणताही धोका आढळला नाही.",
        "rules": "सक्रिय सुरक्षा नियम: {rules}.",
        "directive": "सुरक्षा निर्देश: {action}"
    },
    "ta": {
        "header": "ORCA கடல் பாதுகாப்பு மதிப்பீடு: [{recommendation}] (ஆபத்து நிலை: {risk_level}, மதிப்பீடு: {risk_score}/100, நம்பிக்கை: {confidence_score}%)।",
        "vessel": "படகு வகை: {vessel}।",
        "all_online": "அனைத்து முக்கிய கடல் தரவு மூலங்களும் ஆன்லைனில் உள்ளன.",
        "gaps": "கிடைக்காத தரவுகள்: {gaps}.",
        "no_rules": "பாதுகாப்பு வரம்புகள் மீறப்படவில்லை.",
        "rules": "செயலில் உள்ள பாதுகாப்பு விதிகள்: {rules}.",
        "directive": "பாதுகாப்பு வழிகாட்டுதல்: {action}"
    },
    "te": {
        "header": "ORCA సముద్ర భద్రతా అంచనా: [{recommendation}] (ప్రమాద స్థాయి: {risk_level}, స్కోరు: {risk_score}/100, విశ్వసనీయత: {confidence_score}%)।",
        "vessel": "పడవ రకం: {vessel}।",
        "all_online": "అన్ని ప్రధాన సముద్ర టెలిమెట్రీ వనరులు అందుబాటులో ఉన్నాయి.",
        "gaps": "అందుబాటులో లేని డేటా: {gaps}.",
        "no_rules": "ఎలాంటి భద్రతా పరిమితులు ఉల్లంಘించబడలేదు.",
        "rules": "భద్రతా నిబంధనలు: {rules}.",
        "directive": "భద్రతా సూచన: {action}"
    },
    "bn": {
        "header": "ORCA সামুদ্রিক নিরাপত্তা মূল্যায়ন: [{recommendation}] (ঝুঁকির মাত্রা: {risk_level}, স্কোর: {risk_score}/100, নির্ভরযোগ্যতা: {confidence_score}%)।",
        "vessel": "নৌকার ধরন: {vessel}।",
        "all_online": "সমস্ত প্রাথমিক রিয়েল-টাইম তথ্য সক্রিয় আছে।",
        "gaps": "অনুপলব্ধ তথ্য: {gaps}।",
        "no_rules": "কোনো বিপদজনক অবস্থা নেই।",
        "rules": "সতর্কতামূলক নিয়ম: {rules}।",
        "directive": "নিরাপত্তা নির্দেশিকা: {action}"
    },
    "gu": {
        "header": "ORCA દરિયાઈ સુરક્ષા મૂલ્યાંકન: [{recommendation}] (જોખમ સ્તર: {risk_level}, સ્કોર: {risk_score}/100, વિશ્વસનીયતા: {confidence_score}%)।",
        "vessel": "હોડીનો પ્રકાર: {vessel}।",
        "all_online": "તમામ પ્રાથમિક દરિયાઈ ટેલિમેટ્રી સ્ત્રોતો સક્રિય છે.",
        "gaps": "અપૂરતો ડેટા: {gaps}.",
        "no_rules": "કોઈ જોખમ જણાયું નથી.",
        "rules": "સક્રિય નિયમો: {rules}.",
        "directive": "સુરક્ષા નિર્દેશ: {action}"
    },
    "kn": {
        "header": "ORCA ಸಾಗರ ಸುರಕ್ಷತಾ ಮೌಲ್ಯಮಾಪನ: [{recommendation}] (ಅಪಾಯದ ಮಟ್ಟ: {risk_level}, ಅಂಕ: {risk_score}/100, ವಿಶ್ವಾಸಾರ್ಹತೆ: {confidence_score}%)।",
        "vessel": "ದೋಣಿ ಪ್ರಕಾರ: {vessel}।",
        "all_online": "ಎಲ್ಲಾ ಪ್ರಾಥಮಿಕ ಸಾಗರ ಟೆಲಿಮೆಟ್ರಿ ಮೂಲಗಳು ಸಕ್ರಿಯವಾಗಿವೆ.",
        "gaps": "ಲಭ್ಯವಿಲ್ಲದ ಮಾಹಿತಿ: {gaps}.",
        "no_rules": "ಯಾವುದೇ ಅಪಾಯದ ಮಿತಿಗಳು ಉಲ್ಲಂಘನೆಯಾಗಿಲ್ಲ.",
        "rules": "ಸುರಕ್ಷತಾ ನಿಯಮಗಳು: {rules}.",
        "directive": "ಸುರಕ್ಷತಾ ನಿರ್ದೇಶನ: {action}"
    },
    "ml": {
        "header": "ORCA സമുദ്ര സുരക്ഷാ വിലയിരുത്തൽ: [{recommendation}] (അപകട നില: {risk_level}, സ്കോർ: {risk_score}/100, കൃത്യത: {confidence_score}%)।",
        "vessel": "ബോട്ടിന്റെ തരം: {vessel}।",
        "all_online": "എല്ലാ പ്രധാന സമുദ്ര നിരീക്ഷണ സംവിധാനങ്ങളും സജീവമാണ്.",
        "gaps": "ലഭ്യമല്ലാത്ത വിവരങ്ങൾ: {gaps}.",
        "no_rules": "അപകടസാധ്യതകളൊന്നും കണ്ടെത്തിയിട്ടില്ല.",
        "rules": "സുരക്ഷാ നിയമങ്ങൾ: {rules}.",
        "directive": "സുരക്ഷാ നിർദ്ദേശം: {action}"
    },
    "pa": {
        "header": "ORCA ਸਮੁੰਦਰੀ ਸੁਰੱਖਿਆ ਮੁਲਾਂਕਣ: [{recommendation}] (ਖਤਰਾ ਪੱਧਰ: {risk_level}, ਸਕੋਰ: {risk_score}/100, ਭਰੋਸੇਯੋਗਤਾ: {confidence_score}%)।",
        "vessel": "ਕਿਸ਼ਤੀ ਦੀ ਸ਼੍ਰੇਣੀ: {vessel}।",
        "all_online": "ਸਾਰੇ ਪ੍ਰਮੁੱਖ ਸਮੁੰਦਰੀ ਸਰੋਤ ਸਰਗਰਮ ਹਨ।",
        "gaps": "ਨਾ ਮਿਲਿਆ ਡੇਟਾ: {gaps}।",
        "no_rules": "ਕੋਈ ਖਤਰਾ ਨਹੀਂ ਹੈ।",
        "rules": "ਸੁਰੱਖਿਆ ਨਿਯਮ: {rules}।",
        "directive": "ਸੁਰੱਖਿਆ ਹਦਾਇਤ: {action}"
    },
    "or": {
        "header": "ORCA ସାମୁଦ୍ରିକ ସୁରକ୍ଷା ମୂଲ୍ୟାଙ୍କନ: [{recommendation}] (ବିପଦ ସ୍ତର: {risk_level}, ସ୍କୋର: {risk_score}/100, ବିଶ୍ୱସନୀୟତା: {confidence_score}%)।",
        "vessel": "ଡଙ୍ଗାର ପ୍ରକାର: {vessel}।",
        "all_online": "ସମସ୍ତ ସାମୁଦ୍ରିକ ଟେଲିମେଟ୍ରି ଉତ୍ସ ସକ୍ରିୟ ଅଛି।",
        "gaps": "ଅନୁପଲବ୍ଧ ତଥ୍ୟ: {gaps}।",
        "no_rules": "କୌଣସି ବିପଦ ଦେଖାଯାଇନାହିଁ।",
        "rules": "ସୁରକ୍ଷା ନିୟମ: {rules}।",
        "directive": "ସୁରକ୍ଷା ନିର୍ଦ୍ଦେଶ: {action}"
    },
    "ur": {
        "header": "ORCA سمندری تحفظ کا جائزہ: [{recommendation}] (خطرے کی سطح: {risk_level}، اسکور: {risk_score}/100، اعتماد: {confidence_score}%)۔",
        "vessel": "کشتی کی قسم: {vessel}۔",
        "all_online": "تمام بنیادی سمندری ڈیٹا ذرائع فعال ہیں۔",
        "gaps": "لاپتہ ڈیٹا: {gaps}۔",
        "no_rules": "کوئی خطرہ ریکارڈ نہیں ہوا۔",
        "rules": "حفاظتی قواعد: {rules}۔",
        "directive": "حفاظتی ہدایت: {action}"
    },
    "hinglish": {
        "header": "ORCA Marine Safety Assessment: [{recommendation}] (Risk Level: {risk_level}, Score: {risk_score}/100, Confidence: {confidence_score}%).",
        "vessel": "Vessel Class: {vessel}.",
        "all_online": "Saare primary marine telemetry feeds online hain.",
        "gaps": "Data gaps notice kiye gaye: {gaps}.",
        "no_rules": "Koi security warning ya hazard trigger nahi hua.",
        "rules": "Triggered safety rules: {rules}.",
        "directive": "Safety Directive: {action}"
    },
    "en": {
        "header": "ORCA Safety Evaluation: [{recommendation}] (Risk Level: {risk_level}, Score: {risk_score}/100, Confidence: {confidence_score}%).",
        "vessel": "Vessel Class: {vessel}.",
        "all_online": "All primary real telemetry sources are online.",
        "gaps": "Telemetry gaps identified: {gaps}.",
        "no_rules": "No safety thresholds breached.",
        "rules": "Triggered maritime safety rules: {rules}.",
        "directive": "Directive: {action}"
    },
}


class SynthesisAgent:
    """
    Multilingual Grounded Synthesis and Explanation Agent.
    Receives only verified agent observations and the deterministic safety decision.
    Uses Groq LLM (if configured) with explicit language prompts to synthesize fluent
    responses in Hindi, Marathi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam,
    Punjabi, Odia, Urdu, Hinglish, or English.
    Fallback ensures 100% language fidelity even when LLM is unavailable.
    """

    async def execute(self, state: AgentState) -> Dict[str, Any]:
        safety_eval = state.get("safety_assessment") or {}
        recommendation = safety_eval.get("recommendation", "INSUFFICIENT_DATA")
        risk_level = safety_eval.get("risk_level", "UNKNOWN")
        risk_score = safety_eval.get("risk_score", 50)
        confidence_score = safety_eval.get("confidence_score", 20)
        triggered_rules = safety_eval.get("triggered_rules", [])
        missing_data = safety_eval.get("missing_data", [])
        required_action = safety_eval.get("required_next_action", "Exercise caution.")

        data_avail = state.get("data_availability") or {}
        user_profile = state.get("user_profile") or {}
        lang = user_profile.get("language") or "en"
        vessel = user_profile.get("vesselClass", "motorized_fiberglass")

        # 1. Deterministic multilingual base synthesis
        tmpl = SYNTHESIS_TEMPLATES.get(lang, SYNTHESIS_TEMPLATES["en"])
        gaps_str = ", ".join(missing_data) if missing_data else ""
        gaps_line = tmpl["gaps"].format(gaps=gaps_str) if missing_data else tmpl["all_online"]
        rules_str = "; ".join(triggered_rules) if triggered_rules else ""
        rules_line = tmpl["rules"].format(rules=rules_str) if triggered_rules else tmpl["no_rules"]

        base_answer = (
            f"{tmpl['header'].format(recommendation=recommendation, risk_level=risk_level, risk_score=risk_score, confidence_score=confidence_score)}\n"
            f"{tmpl['vessel'].format(vessel=vessel)}\n"
            f"{gaps_line}\n"
            f"{rules_line}\n"
            f"{tmpl['directive'].format(action=required_action)}"
        )

        # 2. If Groq LLM is configured, enrich explanation with grounded multilingual synthesis
        if groq_client.is_configured():
            full_lang = LANG_NAMES.get(lang, "English")
            system_prompt = (
                f"You are ORCA, an AI Marine Ecosystem Reasoning agent for SIH26176. "
                f"You are speaking to Indian fishermen, boat operators, and coastal maritime authorities. "
                f"CRITICAL MULTILINGUAL MANDATE:\n"
                f"You MUST write the explanation, data_gap_summary, and mandatory_safeguard in {full_lang}.\n"
                f"If language is Hindi ('hi'), write in natural, clear Hindi (हिंदी).\n"
                f"If language is Marathi ('mr'), write in authentic Marathi (मराठी).\n"
                f"If language is Tamil ('ta'), write in authentic Tamil (தமிழ்).\n"
                f"If language is Telugu ('te'), write in Telugu (తెలుగు).\n"
                f"If language is Bengali ('bn'), write in Bengali (বাংলা).\n"
                f"If language is Gujarati ('gu'), write in Gujarati (ગુજરાતી).\n"
                f"If language is Kannada ('kn'), write in Kannada (ಕನ್ನಡ).\n"
                f"If language is Malayalam ('ml'), write in Malayalam (മലയാളം).\n"
                f"If language is Punjabi ('pa'), write in Punjabi (ਪੰਜਾਬੀ).\n"
                f"If language is Odia ('or'), write in Odia (ଓଡ଼ିଆ).\n"
                f"If language is Urdu ('ur'), write in Urdu (اردو).\n"
                f"If language is Hinglish, write in conversational Hinglish.\n"
                f"CRITICAL SAFETY INVARIANTS:\n"
                f"1. NEVER contradict or alter the deterministic recommendation: [{recommendation}] or risk level: [{risk_level}].\n"
                f"2. NEVER invent wave heights, wind speeds, coordinates, or fishing zones.\n"
                f"3. Prominently emphasize safety directive: {required_action}.\n"
                f"4. Output must be strictly valid JSON matching the GroundedSynthesisModel schema."
            )

            prompt_content = f"""
User Query: {state.get('query')}
Target Language: {full_lang} (Code: {lang})
Vessel Class: {vessel}
Deterministic Recommendation: {recommendation}
Risk Level: {risk_level} (Score: {risk_score}/100, Confidence: {confidence_score}%)
Triggered Safety Rules: {triggered_rules}
Missing Data Telemetry: {missing_data}
Action Directive: {required_action}
Data Availability: {data_avail}
"""
            try:
                llm_result: Optional[GroundedSynthesisModel] = await groq_client.generate_structured(
                    messages=[{"role": "user", "content": prompt_content}],
                    response_model=GroundedSynthesisModel,
                    system_prompt=system_prompt,
                )

                if llm_result and llm_result.explanation:
                    base_answer = (
                        f"{llm_result.explanation}\n\n"
                        f"{llm_result.data_gap_summary}\n\n"
                        f"🛡️ {llm_result.mandatory_safeguard}"
                    )
            except Exception as e:
                logger.warning(f"Groq LLM synthesis encountered error: {e}. Using deterministic multilingual template.")

        trace_entry = {
            "agent": "synthesis",
            "status": "completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Synthesis completed in language '{lang}' ({LANG_NAMES.get(lang, 'English')})",
        }
        current_traces = list(state.get("agent_traces") or [])
        current_traces.append(trace_entry)

        return {
            "synthesis_output": {
                "answer": base_answer,
                "language": lang,
            },
            "agent_traces": current_traces,
        }


synthesis_agent = SynthesisAgent()

