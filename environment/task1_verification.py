from models import (
    PTPAObservation,
    EvidenceItem,
    PolicyRule,
)
from tasks import TASK1_ANSWER_KEYS
from environment.rewards import compute_reward

print("task1_verification loaded")


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def check_eligibility(patient, ipd):
    insurance = patient["insurance"]
    insurer = insurance["insurer"]

    policy = ipd[insurer]["eligibility"]

    is_active = insurance.get("active", False)
    required = policy.get("active_required", True)

    eligible = is_active == required

    evidence = EvidenceItem(
        evidence_type="policy_rule",
        label="Eligibility Status",
        value=eligible,
        unit=None,
        date=None,
        clinically_significant=True,
        source_section="eligibility"
    )

    policy_rule = PolicyRule(
        insurer=insurer,
        section="eligibility",
        rule_id="ELIG-001",
        description="Policy must be active for coverage",
        requirement="active_required = True"
    )

    return eligible, [evidence], policy_rule


def check_cpt_coverage(patient, ipd):
    insurer = patient["insurance"]["insurer"]
    cpt = patient["requested_procedure"]["cpt_code"]

    covered_services = ipd[insurer]["covered_services"]

    is_covered = (
        cpt in covered_services and
        covered_services[cpt]["covered"] is True
    )

    policy_section = None
    if cpt in covered_services:
        policy_section = covered_services[cpt].get("policy_section")

    evidence = EvidenceItem(
        evidence_type="policy_rule",
        label="CPT Coverage",
        value=is_covered,
        unit=None,
        date=None,
        clinically_significant=True,
        source_section="covered_services"
    )

    policy_rule = PolicyRule(
        insurer=insurer,
        section="covered_services",
        rule_id="CPT-001",
        description=f"CPT {cpt} coverage check",
        requirement=policy_section
    )

    return is_covered, [evidence], policy_rule


# --------------------------------------------------
# MAIN HANDLER
# --------------------------------------------------

def handle_task1_action(action, state, prs, ipd):
    patient = prs[state.patient.patient_id]

    found_evidence = []
    reward = 0.0
    result = ""
    policy_rule = None

    # --------------------------------------------
    # CHECK ELIGIBILITY
    # --------------------------------------------
    if action.action_type == "check_eligibility":
        eligible, evidence, policy_rule = check_eligibility(patient, ipd)

        state.progress.eligibility_verified = True
        state.progress.policy_retrieved = True

        found_evidence.extend(evidence)
        state.progress.discovered_evidence.extend(evidence)

        reward += compute_reward("discovery_reward")

        result = f"Eligibility check → active={eligible}"

    # --------------------------------------------
    # CHECK CPT COVERAGE
    # --------------------------------------------
    elif action.action_type == "check_cpt_coverage":
        covered, evidence, policy_rule = check_cpt_coverage(patient, ipd)

        state.progress.cpt_coverage_checked = True
        state.progress.policy_retrieved = True

        found_evidence.extend(evidence)
        state.progress.discovered_evidence.extend(evidence)

        reward += compute_reward("discovery_reward")

        result = f"CPT coverage → covered={covered}"

    # --------------------------------------------
    # QUERY POLICY DATABASE (NEW - IMPORTANT)
    # --------------------------------------------
    elif action.action_type == "query_policy_database":
        insurer = action.parameters.get("insurer")
        section = action.parameters.get("section")

        policy_data = ipd.get(insurer, {}).get(section, {})

        policy_rule = PolicyRule(
            insurer=insurer,
            section=section,
            rule_id="POLICY-LOOKUP",
            description=f"Retrieved {section} policy",
            requirement=str(policy_data)
        )

        state.progress.policy_retrieved = True
        reward += compute_reward("discovery_reward")

        result = f"Retrieved {section} policy"

    # --------------------------------------------
    # SUBMIT DECISION
    # --------------------------------------------
    elif action.action_type == "submit_decision":
        answer = TASK1_ANSWER_KEYS[state.patient.patient_id]

        decision = action.parameters.get("decision")

        correct_decision = decision == answer["decision"]

        # Check policy citation (for 20% grading)
        cited_section = action.parameters.get("policy_section_cited")
        correct_section = answer["correct_policy_section"]

        citation_correct = cited_section == correct_section

        # Reward logic
        if correct_decision:
            reward += compute_reward("success_reward")

        state.progress.decision_submitted = True

        return PTPAObservation(
            result=f"Decision submitted → correct={correct_decision}, citation_correct={citation_correct}",
            success=True,
            reward=reward,
            found_evidence=state.progress.discovered_evidence,
            policy_rule=None,
            step_count=state.step_count,
            done=True
        )

    # --------------------------------------------
    # INVALID ACTION
    # --------------------------------------------
    else:
        return PTPAObservation(
            result="Invalid action for Task 1",
            success=False,
            reward=0.0,
            step_count=state.step_count,
            done=False,
            error="Invalid action"
        )

    # --------------------------------------------
    # DEFAULT RESPONSE
    # --------------------------------------------
    return PTPAObservation(
        result=result,
        success=True,
        reward=reward,
        found_evidence=found_evidence,
        policy_rule=policy_rule,
        step_count=state.step_count,
        done=False
    )