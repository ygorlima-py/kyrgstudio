
SECTION_ADAPTATION_FIELDS = {
    "hook": ["main_promise", "core_problem", "core_desire"],
    "problem": ["core_problem"],
    "pain": ["core_problem"],
    "agitation": ["core_problem", "core_desire"],
    "promise": ["main_promise"],
    "mechanism": ["unique_mechanism"],
    "proof": ["proof_assets"],
    "story": ["proof_assets", "core_problem", "core_desire"],
    "objection": ["objections"],
    "offer": ["product_or_solution", "offer_details"],
    "cta": ["call_to_action"],
    "urgency": ["offer_details"],
    "scarcity": ["offer_details"],
    "education": ["product_or_solution", "unique_mechanism"],
    "transition": ["target_audience", "main_promise"],
    "payoff": ["main_promise", "core_desire", "call_to_action"],
}

SECTION_PAUSE_SECONDS = {
    "hook": 0.5,
    "problem": 0.4,
    "pain": 0.4,
    "agitation": 0.5,
    "promise": 0.65,
    "mechanism": 0.4,
    "proof": 0.55,
    "story": 0.75,
    "objection": 0.65,
    "offer": 0.4,
    "cta": 0.45,
    "urgency": 0.3,
    "scarcity": 0.3,
    "education": 0.4,
    "transition": 0.3,
    "payoff": 0.65,
}

PAUSE_INTENT_COEFFICIENT = {
    "short": 0.75,
    "medium": 1.0,
    "long": 1.35,
    "dramatic": 1.75,
}

