"""Definiciones estáticas de botín enemigo y cofres."""

ENEMY_LOOT_TABLE = {
    "tiers": {
        "1": {
            "weapons": [
                {"type": "weapon", "id": "short_rifle", "weight": 1.0},
                {"type": "weapon", "id": "dual_pistols", "weight": 0.8},
            ],
            "upgrades": [
                {"type": "upgrade", "id": "spd_up", "weight": 2.0},
            ],
            "consumables": [
                {"type": "consumable", "id": "heal_small", "amount": 1, "weight": 0.2},
                {"type": "consumable", "id": "heal_battery_full", "amount": 1, "weight": 0.03},
            ],
            "bundles": [
                {
                    "type": "bundle",
                    "weight": 1.0,
                    "contents": [
                        {"type": "gold", "amount": 30},
                        {"type": "consumable", "id": "heal_small", "amount": 2},
                    ],
                }
            ],
        },
        "2": {
            "weapons": [
                {"type": "weapon", "id": "light_rifle", "weight": 1.1},
                {"type": "weapon", "id": "tesla_gloves", "weight": 0.9},
            ],
            "upgrades": [
                {"type": "upgrade", "id": "cdr_charm", "weight": 1.7},
                {"type": "upgrade", "id": "sprint_core", "weight": 1.6},
                {"type": "upgrade", "id": "dash_core", "weight": 1.3},
            ],
            "consumables": [
                {"type": "consumable", "id": "heal_small", "amount": 1, "weight": 0.18},
                {"type": "consumable", "id": "heal_battery_full", "amount": 1, "weight": 0.02},
            ],
            "bundles": [
                {
                    "type": "bundle",
                    "weight": 1.2,
                    "contents": [
                        {"type": "gold", "amount": 45},
                        {"type": "consumable", "id": "heal_small", "amount": 2},
                        {"type": "upgrade", "id": "spd_up"},
                    ],
                },
                {
                    "type": "bundle",
                    "weight": 0.7,
                    "contents": [
                        {"type": "gold", "amount": 40},
                        {"type": "consumable", "id": "heal_small", "amount": 3},
                        {"type": "upgrade", "id": "cdr_charm"},
                    ],
                },
            ],
        },
        "3": {
            "weapons": [
                {"type": "weapon", "id": "pulse_rifle", "weight": 1.0},
                {"type": "weapon", "id": "arcane_salvo", "weight": 1.0},
                {"type": "weapon", "id": "ember_carbine", "weight": 1.0},
            ],
            "upgrades": [
                {"type": "upgrade", "id": "cdr_core", "weight": 1.8},
                {"type": "upgrade", "id": "dash_drive", "weight": 1.5},
            ],
            "consumables": [
                {"type": "consumable", "id": "heal_small", "amount": 1, "weight": 0.16},
                {"type": "consumable", "id": "heal_battery_full", "amount": 1, "weight": 0.03},
            ],
            "bundles": [
                {
                    "type": "bundle",
                    "weight": 1.4,
                    "contents": [
                        {"type": "gold", "amount": 70},
                        {"type": "consumable", "id": "heal_small", "amount": 2},
                        {"type": "upgrade", "id": "dash_core"},
                    ],
                },
                {
                    "type": "bundle",
                    "weight": 0.8,
                    "contents": [
                        {"type": "consumable", "id": "heal_battery_full", "amount": 1},
                        {"type": "upgrade", "id": "cdr_core"},
                    ],
                },
            ],
        },
    },
    "global_drop_rates": {
        "enemy_gold_chance": 0.70,
        "enemy_heal_small_chance": 0.20,
        "enemy_heal_big_chance": 0.10,
        "enemy_upgrade_chance": 0.10,
        "enemy_bundle_chance": 0.05,
        "enemy_weapon_rare_chance": 1.0,
    },
}
