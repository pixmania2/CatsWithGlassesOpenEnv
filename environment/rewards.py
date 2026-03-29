from tasks import get_reward_value


def compute_reward(signal: str) -> float:
    return get_reward_value(signal)