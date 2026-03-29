"""
rewards.py — Reward Computation for the PTPA OpenEnv Environment

Imports canonical reward signal values from tasks.py and provides
helper functions for the engine to compute per-step rewards.
"""

from __future__ import annotations

from typing import Set

from tasks import REWARD_SIGNALS, get_reward_value


# ---------------------------------------------------------------------------
# Backward-compatible shim (used by Person A's task handler files)
# ---------------------------------------------------------------------------
def compute_reward(signal: str) -> float:
    """Return the scalar reward value for a named signal."""
    return get_reward_value(signal)


def discovery_reward() -> tuple[float, str]:
    """Agent successfully retrieved a relevant policy section."""
    return REWARD_SIGNALS["discovery_reward"], "Discovery: retrieved relevant policy section"


def evidence_reward(label: str = "") -> tuple[float, str]:
    """Agent extracted a clinically significant piece of evidence."""
    reason = f"Evidence: extracted critical finding — {label}" if label else "Evidence: extracted critical finding"
    return REWARD_SIGNALS["evidence_reward"], reason


def logic_reward(label: str = "") -> tuple[float, str]:
    """Agent correctly identified a red flag or exception criteria."""
    reason = f"Logic: identified {label}" if label else "Logic: correct clinical reasoning"
    return REWARD_SIGNALS["logic_reward"], reason


def success_reward() -> tuple[float, str]:
    """Agent submitted the correct final determination."""
    return REWARD_SIGNALS["success_reward"], "Success: correct determination submitted"


def loop_penalty() -> tuple[float, str]:
    """Agent repeated the same query without new results."""
    return REWARD_SIGNALS["loop_penalty"], "Penalty: repeated query (loop detected)"


def destructive_penalty(reason: str = "") -> tuple[float, str]:
    """Agent accessed unauthorized records or submitted false info."""
    msg = f"Penalty: destructive action — {reason}" if reason else "Penalty: destructive action"
    return REWARD_SIGNALS["destructive_penalty"], msg


def no_reward(reason: str = "") -> tuple[float, str]:
    msg = reason if reason else "No reward signal"
    return REWARD_SIGNALS["no_reward"], msg


def compute_step_reward(
    action_type: str,
    action_succeeded: bool,
    new_info_found: bool,
    queried_sections: Set[str],
    current_section: str | None = None,
    is_correct_decision: bool | None = None,
    label: str = "",
) -> tuple[float, str]:
    """
    Central reward dispatcher called by the engine after each step.

    Returns (reward_value, reward_reason).
    """
    if not action_succeeded:
        return no_reward("Action failed")

    # Loop detection: same section queried again
    if current_section and current_section in queried_sections and not new_info_found:
        return loop_penalty()

    # Final decision
    if action_type == "submit_decision":
        if is_correct_decision is True:
            return success_reward()
        elif is_correct_decision is False:
            return no_reward("Incorrect determination submitted")
        return no_reward("Decision submitted")

    # Evidence extraction actions
    evidence_actions = {
        "extract_pt_sessions",
        "extract_lab_values",
        "check_red_flags",
    }
    if action_type in evidence_actions and new_info_found:
        return evidence_reward(label)

    # Logic / reasoning actions
    logic_actions = {
        "compare_policy_duration",
        "check_step_therapy",
        "generate_appeal_letter",
    }
    if action_type in logic_actions and new_info_found:
        return logic_reward(label)

    # Policy / database queries
    discovery_actions = {
        "query_policy_database",
        "check_eligibility",
        "check_cpt_coverage",
        "query_patient_record",
    }
    if action_type in discovery_actions and new_info_found:
        return discovery_reward()

    return no_reward("Action completed, no new information")
