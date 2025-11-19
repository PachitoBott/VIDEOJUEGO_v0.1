from __future__ import annotations

import random
from collections.abc import Iterable
from typing import Any


def apply_reward_entry(player: Any, reward: dict) -> bool:
    """Aplica una entrada de recompensa genérica al jugador."""
    if not isinstance(reward, dict):
        return False
    rtype = reward.get("type")
    if rtype == "gold":
        return apply_gold_reward(player, reward.get("amount", 0))
    if rtype == "heal":
        return apply_heal_reward(player, reward.get("amount", 0))
    if rtype == "weapon":
        return apply_weapon_reward(player, reward.get("id"))
    if rtype == "upgrade":
        return apply_upgrade_reward(player, reward.get("id"))
    if rtype == "consumable":
        return apply_consumable_reward(player, reward.get("id"), reward)
    if rtype == "bundle":
        return apply_bundle_reward(player, reward.get("contents"))
    return False


def apply_gold_reward(player: Any, amount: Any) -> bool:
    amount = int(amount)
    if amount <= 0:
        return False
    current = getattr(player, "gold", 0)
    setattr(player, "gold", current + amount)
    return True


def apply_heal_reward(player: Any, amount: Any) -> bool:
    amount = int(amount)
    if amount <= 0:
        return False
    max_hp = getattr(player, "max_hp", getattr(player, "hp", 1))
    hp = getattr(player, "hp", max_hp)
    new_hp = min(max_hp, hp + amount)
    setattr(player, "hp", new_hp)
    if hasattr(player, "_hits_taken_current_life"):
        setattr(player, "_hits_taken_current_life", max(0, max_hp - new_hp))
    return new_hp != hp


def apply_weapon_reward(player: Any, weapon_id: Any) -> bool:
    if not weapon_id:
        return False
    unlock = getattr(player, "unlock_weapon", None)
    if callable(unlock):
        return bool(unlock(weapon_id, auto_equip=True))
    equip = getattr(player, "equip_weapon", None)
    if callable(equip):
        equip(weapon_id)
        return True
    setattr(player, "current_weapon", weapon_id)
    return True


def apply_upgrade_reward(player: Any, upgrade_id: Any) -> bool:
    if not upgrade_id:
        return False
    register = getattr(player, "register_upgrade", None)
    has_upgrade = getattr(player, "has_upgrade", None)
    set_modifier = getattr(player, "set_cooldown_modifier", None)
    uid = str(upgrade_id)

    if uid == "hp_up":
        max_lives = getattr(player, "max_lives", getattr(player, "lives", 1))
        lives = getattr(player, "lives", max_lives)
        max_lives += 1
        lives = min(lives + 1, max_lives)
        setattr(player, "max_lives", max_lives)
        setattr(player, "lives", lives)
        if callable(register):
            register(uid)
        return True
    if uid == "spd_up":
        speed = getattr(player, "speed", 1.0)
        setattr(player, "speed", speed * 1.05)
        if callable(register):
            register(uid)
        return True
    if uid == "cdr_charm":
        core_active = callable(has_upgrade) and has_upgrade("cdr_core")
        multiplier = 0.94 if core_active else 0.9
        if callable(register):
            register(uid)
        if callable(set_modifier):
            set_modifier(uid, multiplier)
        else:
            current = getattr(player, "cooldown_scale", 1.0)
            new_scale = max(0.35, current * multiplier)
            setattr(player, "cooldown_scale", new_scale)
            refresher = getattr(player, "refresh_weapon_modifiers", None)
            if callable(refresher):
                refresher()
            elif hasattr(player, "weapon") and player.weapon:
                setter = getattr(player.weapon, "set_cooldown_scale", None)
                if callable(setter):
                    setter(new_scale)
        return True
    if uid == "cdr_core":
        charm_active = callable(has_upgrade) and has_upgrade("cdr_charm")
        if callable(register):
            register(uid)
        if callable(set_modifier):
            set_modifier(uid, 0.88)
            if charm_active:
                set_modifier("cdr_charm", 0.94)
        else:
            current = getattr(player, "cooldown_scale", 1.0)
            new_scale = max(0.35, current * 0.88)
            setattr(player, "cooldown_scale", new_scale)
            refresher = getattr(player, "refresh_weapon_modifiers", None)
            if callable(refresher):
                refresher()
            elif hasattr(player, "weapon") and player.weapon:
                setter = getattr(player.weapon, "set_cooldown_scale", None)
                if callable(setter):
                    setter(new_scale)
            if charm_active:
                setattr(player, "cooldown_scale", max(0.35, new_scale * (0.94 / 0.9)))
                refresher = getattr(player, "refresh_weapon_modifiers", None)
                if callable(refresher):
                    refresher()
        return True
    if uid == "sprint_core":
        sprint = getattr(player, "sprint_multiplier", 1.0)
        setattr(player, "sprint_multiplier", sprint * 1.1)
        speed = getattr(player, "speed", 1.0)
        setattr(player, "speed", speed * 1.03)
        if hasattr(player, "sprint_control_bonus"):
            player.sprint_control_bonus = max(getattr(player, "sprint_control_bonus", 0.0), 0.15)
        if callable(register):
            register(uid)
        return True
    if uid == "dash_core":
        cooldown = getattr(player, "dash_cooldown", 0.75)
        new_cd = max(0.25, cooldown * 0.85)
        setattr(player, "dash_cooldown", new_cd)
        if hasattr(player, "dash_core_bonus_window"):
            player.dash_core_bonus_window = max(getattr(player, "dash_core_bonus_window", 0.0), 0.15)
        if hasattr(player, "dash_core_bonus_iframe"):
            player.dash_core_bonus_iframe = max(getattr(player, "dash_core_bonus_iframe", 0.0), 0.05)
        if callable(register):
            register(uid)
        return True
    if uid == "dash_drive":
        duration = getattr(player, "dash_duration", 0.18)
        new_duration = min(0.6, duration + 0.08)
        setattr(player, "dash_duration", new_duration)
        setattr(
            player,
            "dash_iframe_duration",
            max(getattr(player, "dash_iframe_duration", new_duration + 0.08), new_duration + 0.08),
        )
        if hasattr(player, "phase_during_dash"):
            player.phase_during_dash = True
        if callable(register):
            register(uid)
        return True
    return False


def apply_consumable_reward(player: Any, consumable_id: Any, data: dict | None = None) -> bool:
    cid = str(consumable_id) if consumable_id else ""
    if cid == "heal_full":
        max_hp = getattr(player, "max_hp", getattr(player, "hp", 1))
        setattr(player, "hp", max_hp)
        if hasattr(player, "_hits_taken_current_life"):
            setattr(player, "_hits_taken_current_life", 0)
        return True
    if cid == "heal_medium":
        amount = random.randint(2, 3)
        return apply_heal_reward(player, amount)
    if cid == "heal_small":
        amount = int((data or {}).get("amount", 1) or 1)
        return apply_heal_reward(player, amount)
    if cid == "life_refill":
        max_lives = getattr(player, "max_lives", getattr(player, "lives", 1))
        setattr(player, "lives", max_lives)
        return True
    return False


def apply_bundle_reward(player: Any, contents: Iterable[dict] | None) -> bool:
    if not contents:
        return False
    applied_any = False
    for entry in contents:
        if not isinstance(entry, dict):
            continue
        applied_any = apply_reward_entry(player, entry) or applied_any
    return applied_any
