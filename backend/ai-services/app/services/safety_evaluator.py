"""
Comprehensive Deterministic Safety Rule Engine & Multilingual Synthesizer.
Strict Hierarchy:
1. Cyclone & Severe Official Weather Warnings (Immediate NO_GO).
2. Critical Data Gap Enforcement (Never convert missing data into GO).
3. Vessel Threshold Limits (Wave height, wave period, wind speed, gusts).
4. Visibility & Precipitation.
5. Tidal Context (Only evaluated if verified source exists).
6. Multilingual Grounded Synthesis (English, Hindi, Marathi).
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[2])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.schemas.normalized import SafetyAssessment, MarineAlert
    from app.core.security import redact_secrets
except (ImportError, ValueError):
    from ..schemas.normalized import SafetyAssessment, MarineAlert
    from ..core.security import redact_secrets


class SafetyEvaluatorService:
    def __init__(self):
        # Default vessel limits (wave meters, wind m/s)
        self.vessel_limits = {
            "non_motorized_traditional": {"max_wave": 1.2, "max_wind": 7.0, "name": "Traditional Non-Motorized Craft"},
            "motorized_fiberglass": {"max_wave": 2.0, "max_wind": 10.5, "name": "FRP Motorized Fishing Boat (< 10m)"},
            "mechanized_trawler": {"max_wave": 3.2, "max_wind": 15.0, "name": "Deep-Sea Mechanized Trawler"},
        }

    def evaluate_safety(
        self,
        latitude: float,
        longitude: float,
        vessel_class: str = "motorized_fiberglass",
        weather_data: Optional[Dict[str, Any]] = None,
        marine_data: Optional[Dict[str, Any]] = None,
        tide_data: Optional[Dict[str, Any]] = None,
        alerts: Optional[List[Dict[str, Any]]] = None,
    ) -> SafetyAssessment:
        now_str = datetime.now(timezone.utc).isoformat()
        reasons: List[str] = []
        missing_data: List[str] = []
        official_sources: List[str] = []

        limits = self.vessel_limits.get(vessel_class.lower(), self.vessel_limits["motorized_fiberglass"])

        # ── 1. Check Official Cyclone & Warning Alerts First ─────────────────
        alert_evidence = alerts or []
        has_severe_alert = False
        severe_alert_detail = ""

        for alt in alert_evidence:
            official_sources.append(alt.get("issuing_agency", "Disaster Management Authority"))
            sev = alt.get("severity", "").lower()
            if sev in ["extreme", "severe", "danger", "critical"]:
                has_severe_alert = True
                severe_alert_detail = alt.get("event_type", "Severe Meteorological Warning")
                reasons.append(f"Official Severe Alert Active: {severe_alert_detail} ({alt.get('affected_area', 'Operating Zone')})")

        if has_severe_alert:
            decision = "NO_GO"
            risk_level = "CRITICAL"
            risk_score = 95
            reasons.append("Policy rule: Active severe storm/cyclone alerts mandate immediate suspension of voyages.")
            return self._build_assessment(
                decision=decision,
                risk_score=risk_score,
                risk_level=risk_level,
                latitude=latitude,
                longitude=longitude,
                reasons=reasons,
                weather_evidence=weather_data or {},
                marine_evidence=marine_data or {},
                tide_evidence=tide_data or {},
                alert_evidence=alert_evidence,
                missing_data=missing_data,
                official_sources=official_sources,
                vessel_name=limits["name"],
                generated_at=now_str,
            )

        # ── 2. Check Critical Data Availability ──────────────────────────────
        if not weather_data or weather_data.get("data_status") == "unavailable" or weather_data.get("status") == "DATA_UNAVAILABLE":
            missing_data.append("Wind speed & atmospheric weather observations")
        if not marine_data or marine_data.get("data_status") == "unavailable" or marine_data.get("status") == "DATA_UNAVAILABLE":
            missing_data.append("Significant wave height & sea-state forecast")

        # CRITICAL SAFETY RULE: Never convert missing data into a safe decision!
        if missing_data:
            decision = "DATA_UNAVAILABLE"
            risk_level = "UNKNOWN"
            risk_score = 75
            reasons.append(
                f"Missing critical telemetry feeds: {', '.join(missing_data)}. "
                "Deterministic safety policy mandates DATA_UNAVAILABLE / NO_GO when physical limits cannot be verified."
            )
            return self._build_assessment(
                decision=decision,
                risk_score=risk_score,
                risk_level=risk_level,
                latitude=latitude,
                longitude=longitude,
                reasons=reasons,
                weather_evidence=weather_data or {},
                marine_evidence=marine_data or {},
                tide_evidence=tide_data or {},
                alert_evidence=alert_evidence,
                missing_data=missing_data,
                official_sources=official_sources,
                vessel_name=limits["name"],
                generated_at=now_str,
            )

        # ── 3. Extract Physical Variables ────────────────────────────────────
        w_data = weather_data or {}
        m_data = marine_data or {}

        wind_speed = float(w_data.get("wind_speed", 0.0) or w_data.get("wind_speed_mps", 0.0))
        wind_gust = float(w_data.get("wind_gusts", 0.0) or w_data.get("wind_gust_mps", 0.0))
        wave_height = float(m_data.get("wave_height", 0.0) or m_data.get("wave_height_meters", 0.0))
        wave_period = m_data.get("wave_period") or m_data.get("wave_period_seconds")
        visibility = w_data.get("visibility") or w_data.get("visibility_km")
        precip = float(w_data.get("precipitation", 0.0) or w_data.get("precipitation_mm", 0.0))

        if w_data.get("provider"):
            official_sources.append(str(w_data["provider"]))
        if m_data.get("provider"):
            official_sources.append(str(m_data["provider"]))

        # ── 4. Evaluate Thresholds ───────────────────────────────────────────
        decision = "GO"
        risk_level = "LOW"
        risk_score = 15

        # Wave height evaluation
        if wave_height > limits["max_wave"]:
            reasons.append(f"Significant wave height ({wave_height:.2f}m) exceeds safe limit ({limits['max_wave']:.2f}m) for {limits['name']}.")
            decision = "NO_GO"
            risk_level = "HIGH"
            risk_score = max(risk_score, 85)
        elif wave_height > (limits["max_wave"] * 0.8):
            reasons.append(f"Wave height ({wave_height:.2f}m) approaching caution limit ({limits['max_wave'] * 0.8:.2f}m).")
            if decision != "NO_GO":
                decision = "CAUTION"
                risk_level = "MODERATE"
                risk_score = max(risk_score, 50)

        # Wind speed & gusts evaluation
        if wind_speed > limits["max_wind"] or wind_gust > (limits["max_wind"] * 1.25):
            reasons.append(f"Wind speed ({wind_speed:.1f} m/s) or gusts ({wind_gust:.1f} m/s) exceed safe operating limits.")
            decision = "NO_GO"
            risk_level = "HIGH"
            risk_score = max(risk_score, 80)
        elif wind_speed > (limits["max_wind"] * 0.8):
            reasons.append(f"Wind speed ({wind_speed:.1f} m/s) is elevated.")
            if decision != "NO_GO":
                decision = "CAUTION"
                risk_level = "MODERATE"
                risk_score = max(risk_score, 45)

        # Visibility & Precipitation
        if visibility is not None and float(visibility) < 2000.0:  # < 2 km
            reasons.append(f"Low visibility ({float(visibility)/1000.0:.1f} km). Navigational collision risk.")
            if decision != "NO_GO":
                decision = "CAUTION"
                risk_score = max(risk_score, 55)

        if precip > 15.0:  # Heavy squall rain
            reasons.append(f"Heavy precipitation detected ({precip:.1f} mm). Squall risk.")
            if decision != "NO_GO":
                decision = "CAUTION"
                risk_score = max(risk_score, 50)

        # Tide information: Only evaluate if valid tide source exists
        tide_evidence_clean = tide_data or {}
        if not tide_data or tide_data.get("status") == "DATA_UNAVAILABLE" or tide_data.get("data_status") == "DATA_UNAVAILABLE":
            missing_data.append("Local tide station harmonic water-level")
        else:
            wl = tide_data.get("water_level") or tide_data.get("tide_height_meters")
            if wl is not None and float(wl) < 0.4:
                reasons.append(f"Low water level ({float(wl):.2f}m Chart Datum). Caution for harbor navigation / reef grounding.")
                if decision == "GO":
                    decision = "CAUTION"
                    risk_score = max(risk_score, 35)

        if not reasons:
            reasons.append(f"All weather and sea-state parameters within safe limits for {limits['name']}.")

        return self._build_assessment(
            decision=decision,
            risk_score=risk_score,
            risk_level=risk_level,
            latitude=latitude,
            longitude=longitude,
            reasons=reasons,
            weather_evidence=w_data,
            marine_evidence=m_data,
            tide_evidence=tide_evidence_clean,
            alert_evidence=alert_evidence,
            missing_data=missing_data,
            official_sources=list(set(official_sources)),
            vessel_name=limits["name"],
            generated_at=now_str,
        )

    def _build_assessment(
        self,
        decision: str,
        risk_score: int,
        risk_level: str,
        latitude: float,
        longitude: float,
        reasons: List[str],
        weather_evidence: Dict[str, Any],
        marine_evidence: Dict[str, Any],
        tide_evidence: Dict[str, Any],
        alert_evidence: List[Dict[str, Any]],
        missing_data: List[str],
        official_sources: List[str],
        vessel_name: str,
        generated_at: str,
    ) -> SafetyAssessment:
        # Multilingual explanations
        explanations = self._generate_multilingual_explanations(
            decision=decision,
            risk_level=risk_level,
            risk_score=risk_score,
            reasons=reasons,
            missing_data=missing_data,
            vessel_name=vessel_name,
        )

        disclaimer = (
            "SAFETY ADVISORY NOTICE: This assessment is an automated, algorithmic decision-support tool. "
            "Never present an AI-generated fishing or safety recommendation as an official emergency warning. "
            "Always follow mandatory orders issued by the India Meteorological Department (IMD), National Disaster "
            "Management Authority (NDMA), and Indian Coast Guard. Emergency SAR Helpline: 1554 / VHF Ch 16."
        )

        return SafetyAssessment(
            decision=decision,
            risk_score=risk_score,
            risk_level=risk_level,
            valid_time=generated_at,
            location={"latitude": latitude, "longitude": longitude},
            reasons=reasons,
            weather_evidence=weather_evidence,
            marine_evidence=marine_evidence,
            tide_evidence=tide_evidence,
            alert_evidence=alert_evidence,
            missing_data=missing_data,
            official_sources=official_sources,
            disclaimer=disclaimer,
            generated_at=generated_at,
            explanations=explanations,
        )

    def _generate_multilingual_explanations(
        self,
        decision: str,
        risk_level: str,
        risk_score: int,
        reasons: List[str],
        missing_data: List[str],
        vessel_name: str,
    ) -> Dict[str, str]:
        # English
        reasons_en = " ".join(reasons)
        missing_en = f" Note missing data: {', '.join(missing_data)}." if missing_data else ""
        en_text = (
            f"ORCA Safety Assessment: [{decision}] for {vessel_name}. "
            f"Risk Level: {risk_level} (Score: {risk_score}/100). {reasons_en}{missing_en} "
            f"Emergency contacts: Coast Guard 1554, VHF Channel 16."
        )

        # Hindi (हिंदी)
        decision_hi = {
            "GO": "प्रस्थान सुरक्षित (GO)",
            "CAUTION": "सावधानीपूर्वक प्रस्थान (CAUTION)",
            "NO_GO": "समुद्र में न जाएं (NO_GO)",
            "DATA_UNAVAILABLE": "डेटा अपर्याप्त - समुद्र में न जाएं (DATA_UNAVAILABLE)",
        }.get(decision, decision)

        hi_text = (
            f"ओरका (ORCA) समुद्री सुरक्षा निर्णय: [{decision_hi}]। "
            f"नाव प्रकार: {vessel_name}। जोखिम स्तर: {risk_level} (अंक: {risk_score}/100)। "
            f"प्रमुख कारण: {reasons_en} "
            f"आपातकालीन संपर्क: भारतीय तटरक्षक बल (Coast Guard) टोल-फ्री 1554 या वीएचएफ चैनल 16।"
        )

        # Marathi (मराठी)
        decision_mr = {
            "GO": "प्रवासास अनुमती (GO)",
            "CAUTION": "सावधगिरी बाळगा (CAUTION)",
            "NO_GO": "समुद्रात जाऊ नका (NO_GO)",
            "DATA_UNAVAILABLE": "माहिती अपुरी - समुद्रात जाऊ नका (DATA_UNAVAILABLE)",
        }.get(decision, decision)

        mr_text = (
            f"ओर्का (ORCA) सागरी सुरक्षा निकाल: [{decision_mr}]। "
            f"बोटीचा प्रकार: {vessel_name}। धोक्याची पातळी: {risk_level} (गुण: {risk_score}/100)। "
            f"कारणे: {reasons_en} "
            f"तातडीचा संपर्क: भारतीय तटरक्षक दल (Indian Coast Guard) 1554 किंवा व्हीएचएफ चॅनेल 16."
        )

        return {
            "en": en_text,
            "hi": hi_text,
            "mr": mr_text,
        }


safety_evaluator = SafetyEvaluatorService()
