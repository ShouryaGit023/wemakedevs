"""
ClimateShield - Amazon Bedrock Integration Module
Generates AI-powered Municipal Heat Action Advisories, Operational Briefs,
and Multi-Lingual Citizen Warnings (English, Gujarati, Hindi) using Amazon Bedrock.
Includes robust graceful fallbacks when AWS credentials or quotas are not present.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("climateshield.bedrock")

# Optional boto3 import
try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = Exception
    BotoCoreError = Exception
    NoCredentialsError = Exception

DEFAULT_BEDROCK_MODEL = os.getenv("AWS_BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", os.getenv("AWS_REGION", "us-east-1"))


def get_bedrock_client():
    """
    Instantiate boto3 bedrock-runtime client with configured region.
    Returns None if boto3 is unavailable or client initialization fails.
    """
    if not BOTO3_AVAILABLE:
        return None
    try:
        return boto3.client("bedrock-runtime", region_name=AWS_REGION)
    except Exception as e:
        logger.warning(f"Failed to initialize AWS Bedrock client: {e}")
        return None


def _build_advisory_prompt(
    city_name: str,
    max_hazard_level: str,
    peak_wbgt: float,
    ward_summaries: List[Dict[str, Any]],
    allocated_interventions: List[Dict[str, Any]],
    budget_used: float,
    equity_score: float,
    target_audience: str = "MUNICIPAL_OFFICERS",
    language: str = "en"
) -> str:
    """
    Constructs structured system and user prompts for Bedrock foundation models.
    """
    lang_instruction = "Respond in English."
    if language.lower() in ["gu", "gujarati"]:
        lang_instruction = "Respond in Gujarati with clear municipal terminology."
    elif language.lower() in ["hi", "hindi"]:
        lang_instruction = "Respond in Hindi with clear municipal terminology."

    prompt = f"""You are the ClimateShield AI Emergency Advisor, embedded into the Ahmedabad Municipal Corporation (AMC) Disaster Management Cell.
Analyze the following multi-hazard thermal risk and optimization output to generate an actionable advisory.

Language Requirement: {lang_instruction}
Target Audience: {target_audience}

Context:
- Target City: {city_name}
- Peak Effective WBGT: {peak_wbgt:.1f}°C
- Citywide Peak Hazard Level: {max_hazard_level}
- Budget Utilized: ₹{budget_used:,.0f}
- Equity Balance Score (Gini/Equity Index): {equity_score:.2f}

Top High-Risk Wards:
{json.dumps(ward_summaries[:5], indent=2)}

Allocated Interventions & Resources:
{json.dumps(allocated_interventions[:6], indent=2)}

Instructions:
1. Executive Situation Summary: Immediate risk to vulnerable demographics (slum dwellers, construction workers, elderly).
2. Priority Directives: 3-4 specific operational actions for field teams (e.g., dispatch water tankers to Behrampura/Danilimda, open cool shelters, halt noon outdoor labor).
3. Citizen Caution Advisory: A punchy 2-sentence public broadcast alert suitable for WhatsApp/SMS civic alerts.
4. Resource Optimization Note: Brief justification on how budget and equity constraints were balanced.

Provide a structured, authoritative, yet easy-to-read response without unnecessary pleasantries.
"""
    return prompt


def generate_fallback_advisory(
    city_name: str,
    max_hazard_level: str,
    peak_wbgt: float,
    ward_summaries: List[Dict[str, Any]],
    allocated_interventions: List[Dict[str, Any]],
    budget_used: float,
    equity_score: float,
    language: str = "en",
    reason: str = "AWS credentials not configured"
) -> Dict[str, Any]:
    """
    Deterministic rule-based fallback generator when Bedrock is unavailable or during offline demo.
    Ensures zero downtime and guarantees 100% test reliability.
    """
    high_risk_names = [w.get("name", w.get("ward_name", "Ward")) for w in ward_summaries[:3]]
    wards_str = ", ".join(high_risk_names) if high_risk_names else "Danilimda, Behrampura, Vatva"

    intervention_types = list({i.get("intervention_type", i.get("type", "Intervention")) for i in allocated_interventions[:4]})
    interventions_str = ", ".join(intervention_types) if intervention_types else "Hydration Kiosks, Cool Roofs, Shade Canopies"

    if language.lower() in ["gu", "gujarati"]:
        situation = f"અમદાવાદ મહાનગર પાલિકા (AMC) હીટ એલર્ટ: {max_hazard_level} જોખમ. પીક WBGT {peak_wbgt:.1f}°C નોંધાયેલ છે. સૌથી વધુ જોખમી વોર્ડ: {wards_str}."
        directives = [
            f"{wards_str} ના સ્લમ વિસ્તારોમાં તાત્કાલિક પીવાના પાણીના ટેન્કર અને ORS કિઓસ્ક તૈનાત કરો.",
            "બપોરે ૧૨ થી ૪ વાગ્યા સુધી બાંધકામ અને મજૂરી કામ સ્થગિત રાખવા માટે આદેશ જાહેર કરો.",
            "તમામ અર્બન હેલ્થ સેન્ટર (UHC) ખાતે કૂલિંગ સેન્ટરો કાર્યરત કરો."
        ]
        public_alert = f"સાવચેત રહો: શહેરમાં અતિશય ગરમીનું મોજું ({peak_wbgt:.1f}°C WBGT). બપોરે બહાર જવાનું ટાળો અને પૂરતું પાણી પીઓ."
    elif language.lower() in ["hi", "hindi"]:
        situation = f"अहमदाबाद नगर निगम (AMC) हीट एक्शन एडवाइजरी: शहर में {max_hazard_level} थर्मल जोखिम दर्ज किया गया है। अधिकतम WBGT {peak_wbgt:.1f}°C है। सर्वाधिक संवेदनशील वार्ड: {wards_str}."
        directives = [
            f"{wards_str} के उच्च-जोखिम वाले क्षेत्रों में तुरंत पेयजल टैंकर एवं ओआरएस बूथ तैनात करें।",
            "दोपहर 12 से 4 बजे के बीच निर्माण कार्य और आउटडोर श्रम पर रोक लगाएं।",
            "सभी प्राथमिक स्वास्थ्य केंद्रों में इमरजेंसी कूलिंग वार्ड सक्रिय करें।"
        ]
        public_alert = f"चेतावनी: अहमदाबाद में भीषण लू का अलर्ट ({peak_wbgt:.1f}°C WBGT)। दोपहर के समय अनावश्यक रूप से धूप में न निकलें।"
    else:
        situation = f"{city_name} (AMC) Emergency Thermal Advisory: The city is currently operating under {max_hazard_level} heat risk conditions with peak outdoor WBGT reaching {peak_wbgt:.1f}°C. Priority vulnerability hotspots identified: {wards_str}."
        directives = [
            f"Immediately mobilize emergency water tankers and hydration kiosks across high-vulnerability settlements in {wards_str}.",
            "Enforce municipal advisories halting non-essential outdoor construction labor between 12:00 PM and 4:00 PM.",
            "Activate dedicated cool-roof community shelters and ensure 24/7 ORS stock in all Urban Health Centers (UHCs)."
        ]
        public_alert = f"HEAT ADVISORY: {city_name} is experiencing severe thermal stress ({peak_wbgt:.1f}°C WBGT). Limit direct sun exposure from 12 PM - 4 PM and hydrate regularly."

    return {
        "status": "SUCCESS_FALLBACK",
        "provider": "ClimateShield Rule Engine (Bedrock Offline Fallback)",
        "model_id": "fallback-rule-engine-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "language": language,
        "hazard_level": max_hazard_level,
        "peak_wbgt": peak_wbgt,
        "executive_summary": situation,
        "priority_directives": directives,
        "citizen_broadcast_alert": public_alert,
        "resource_allocation_note": f"Deployed {len(allocated_interventions)} assets ({interventions_str}) utilizing ₹{budget_used:,.0f} with an equity balance score of {equity_score:.2f}.",
        "bedrock_metadata": {
            "invoked": False,
            "reason": reason,
            "target_model": DEFAULT_BEDROCK_MODEL,
            "region": AWS_REGION
        }
    }


def generate_heat_advisory_with_bedrock(
    city_name: str = "Ahmedabad",
    max_hazard_level: str = "HIGH",
    peak_wbgt: float = 31.5,
    ward_summaries: Optional[List[Dict[str, Any]]] = None,
    allocated_interventions: Optional[List[Dict[str, Any]]] = None,
    budget_used: float = 450000.0,
    equity_score: float = 0.88,
    target_audience: str = "MUNICIPAL_OFFICERS",
    language: str = "en",
    model_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Invokes Amazon Bedrock Foundation Models (Claude 3 or Amazon Titan) to generate an
    evidence-based municipal heat advisory and citizen notification.
    """
    ward_summaries = ward_summaries or []
    allocated_interventions = allocated_interventions or []
    chosen_model = model_id or DEFAULT_BEDROCK_MODEL

    client = get_bedrock_client()
    if client is None:
        return generate_fallback_advisory(
            city_name=city_name,
            max_hazard_level=max_hazard_level,
            peak_wbgt=peak_wbgt,
            ward_summaries=ward_summaries,
            allocated_interventions=allocated_interventions,
            budget_used=budget_used,
            equity_score=equity_score,
            language=language,
            reason="boto3 bedrock-runtime client could not be initialized or AWS credentials not supplied"
        )

    prompt = _build_advisory_prompt(
        city_name=city_name,
        max_hazard_level=max_hazard_level,
        peak_wbgt=peak_wbgt,
        ward_summaries=ward_summaries,
        allocated_interventions=allocated_interventions,
        budget_used=budget_used,
        equity_score=equity_score,
        target_audience=target_audience,
        language=language
    )

    try:
        # Determine payload based on model family
        if "anthropic.claude" in chosen_model:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        elif "amazon.titan" in chosen_model:
            payload = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 1000,
                    "temperature": 0.2,
                    "topP": 0.9
                }
            }
        else:
            # Generic Claude-compatible format default
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}]
            }

        response = client.invoke_model(
            modelId=chosen_model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )

        response_body = json.loads(response["body"].read().decode("utf-8"))

        raw_text = ""
        if "anthropic.claude" in chosen_model and "content" in response_body:
            raw_text = response_body["content"][0]["text"]
        elif "results" in response_body:
            raw_text = response_body["results"][0]["outputText"]
        elif "generation" in response_body:
            raw_text = response_body["generation"]
        else:
            raw_text = json.dumps(response_body)

        return {
            "status": "SUCCESS",
            "provider": "Amazon Bedrock",
            "model_id": chosen_model,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "language": language,
            "hazard_level": max_hazard_level,
            "peak_wbgt": peak_wbgt,
            "raw_advisory_text": raw_text,
            "bedrock_metadata": {
                "invoked": True,
                "region": AWS_REGION,
                "model_id": chosen_model
            }
        }

    except (ClientError, BotoCoreError, NoCredentialsError) as aws_err:
        logger.warning(f"Amazon Bedrock call failed, falling back to deterministic template: {aws_err}")
        return generate_fallback_advisory(
            city_name=city_name,
            max_hazard_level=max_hazard_level,
            peak_wbgt=peak_wbgt,
            ward_summaries=ward_summaries,
            allocated_interventions=allocated_interventions,
            budget_used=budget_used,
            equity_score=equity_score,
            language=language,
            reason=f"AWS API invocation error: {str(aws_err)}"
        )
    except Exception as general_err:
        logger.error(f"Unexpected error in Bedrock advisory generation: {general_err}")
        return generate_fallback_advisory(
            city_name=city_name,
            max_hazard_level=max_hazard_level,
            peak_wbgt=peak_wbgt,
            ward_summaries=ward_summaries,
            allocated_interventions=allocated_interventions,
            budget_used=budget_used,
            equity_score=equity_score,
            language=language,
            reason=f"Unexpected error: {str(general_err)}"
        )
