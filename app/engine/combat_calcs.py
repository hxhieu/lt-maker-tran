from app import utilities
from app.data.database import DB
from app.engine import equations, unit_object
from app.engine.item_system import item_system

def get_weapon_rank_bonus(unit, item):
    weapon_type = item_system.weapon_type(unit, item)
    highest_rank = None
    for weapon_rank in DB.weapon_ranks:
        if unit.wexp[weapon_type] >= weapon_rank.requirement:
            highest_rank = weapon_rank
    return highest_rank

def compute_advantage(unit1, unit2, item1, item2, advantage=True):
    if not item1 or not item2:
        return None
    item1_weapontype = item_system.weapon_type(unit1, item1)
    item2_weapontype = item_system.weapon_type(unit2, item2)
    if not item1_weapontype or not item2_weapontype:
        return None
    if advantage:
        bonus = DB.weapons.get(item1_weapontype).advantage
    else:
        bonus = DB.weapons.get(item1_weapontype).disadvantage
    for adv in bonus:
        if adv.weapon_type == 'All' or adv.weapon_type == item2_weapontype:
            if adv.weapon_rank == 'All' or DB.weapon_ranks.get(adv.weapon_rank).requirement >= unit1.wexp[item1_weapontype]:
                return adv
    return None

def accuracy(unit, item=None):
    if not item:
        item = unit.get_weapon()
    if not item:
        return None

    accuracy = item_system.hit(unit, item)
    if accuracy is None:
        return None

    equation = item_system.accuracy_formula(unit, item)
    accuracy += equations.parser.get(equation, unit)
    
    weapon_rank = get_weapon_rank_bonus(unit, item)
    if weapon_rank:
        accuracy += int(weapon_rank.accuracy)

    # TODO
    # Support Bonus
    # Status Bonus

    return accuracy

def avoid(unit, item_to_avoid=None):
    if not item_to_avoid:
        avoid = equations.parser.avoid(unit)
    else:
        equation = item_system.avoid_formula(unit, item_to_avoid)
        avoid = equations.parser.get(equation, unit)
    return avoid

def crit_accuracy(unit, item=None):
    if not item:
        item = item.get_weapon()
    if not item:
        return None

    crit_accuracy = item_system.crit(unit, item)
    if crit_accuracy is None:
        return None

    equation = item_system.crit_accuracy_formula(unit, item)
    crit_accuracy += equations.parser.get(equation, unit)
    
    weapon_rank = get_weapon_rank_bonus(unit, item)
    if weapon_rank:
        crit_accuracy += int(weapon_rank.crit)

    return crit_accuracy

def crit_avoid(unit, item_to_avoid=None):
    if not item_to_avoid:
        avoid = equations.parser.crit_avoid(unit)
    else:
        equation = item_system.crit_avoid_formula(unit, item_to_avoid)
        avoid = equations.parser.get(equation, unit)
    return avoid

def damage(unit, item=None):
    if not item:
        item = item.get_weapon()
    if not item:
        return None

    might = item_system.damage(unit, item)
    if might is None:
        return None

    equation = item_system.damage_formula(unit, item)
    might += equations.parser.get(equation, unit)

    weapon_rank = get_weapon_rank_bonus(unit, item)
    if weapon_rank:
        might += int(weapon_rank.damage)

    # TODO
    # Support bonus
    # Status bonus

    return might

def defense(unit, item_to_avoid=None):
    if not item_to_avoid:
        res = equations.parser.defense(unit)
    else:
        equation = item_system.defense_formula(unit, item_to_avoid)
        res = equations.parser.get(equation, unit)
    return res

def attack_speed(unit, item=None):
    if not item:
        item = item.get_weapon()
    if not item:
        return None

    equation = item_system.attack_speed_formula(unit, item)
    attack_speed = equations.parser.get(equation, unit)

    weapon_rank = get_weapon_rank_bonus(unit, item)
    if weapon_rank:
        attack_speed += int(weapon_rank.attack_speed)

    # TODO
    # Support bonus
    # Status bonus

    return attack_speed

def defense_speed(unit, item_to_avoid=None):
    if not item_to_avoid:
        speed = equations.parser.defense_speed(unit)
    else:
        equation = item_system.defense_speed_formula(unit, item_to_avoid)
        speed = equations.parser.get(equation, unit)
    return speed

def compute_hit(unit, target, item=None, mode=None):
    if not item:
        item = unit.get_weapon()
    if not item:
        return None

    hit = accuracy(unit, item)
    if hit is None:
        return 10000

    # Handles things like effective accuracy
    hit += item_system.modify_accuracy(unit, item, target, mode)
    
    # Weapon Triangle
    triangle_bonus = 0
    adv = compute_advantage(unit, target, item, target.get_weapon())
    disadv = compute_advantage(unit, target, item, target.get_weapon(), False)
    if adv:
        triangle_bonus += int(adv.accuracy)
    if disadv:
        triangle_bonus += int(disadv.accuracy)

    adv = compute_advantage(target, unit, target.get_weapon(), item)
    disadv = compute_advantage(target, unit, target.get_weapon(), item, False)
    if adv:
        triangle_bonus -= int(adv.avoid)
    if disadv:
        triangle_bonus -= int(disadv.avoid)
    hit += triangle_bonus

    hit -= avoid(target, item)

    return utilities.clamp(hit, 0, 100)

def compute_crit(unit, target, item=None, mode=None):
    if not item:
        item = unit.get_weapon()
    if not item:
        return None

    crit = crit_accuracy(unit, item)

    # Handles things like effective accuracy
    crit += item_system.modify_crit_accuracy(unit, item, target, mode)
    
    # Weapon Triangle
    triangle_bonus = 0
    adv = compute_advantage(unit, target, item, target.get_weapon())
    disadv = compute_advantage(unit, target, item, target.get_weapon(), False)
    if adv:
        triangle_bonus += int(adv.crit)
    if disadv:
        triangle_bonus += int(disadv.crit)

    adv = compute_advantage(target, unit, target.get_weapon(), item)
    disadv = compute_advantage(target, unit, target.get_weapon(), item, False)
    if adv:
        triangle_bonus -= int(adv.dodge)
    if disadv:
        triangle_bonus -= int(disadv.dodge)
    crit += triangle_bonus

    crit -= crit_avoid(target, item)

    return utilities.clamp(crit, 0, 100)

def compute_damage(unit, target, item=None, mode=None, crit=False):
    if not item:
        item = unit.get_weapon()
    if not item:
        return None

    might = damage(unit, item)

    # Handles things like effective damage
    might += item_system.modify_damage(unit, item, target, mode)

    # Weapon Triangle
    triangle_bonus = 0
    adv = compute_advantage(unit, target, item, target.get_weapon())
    disadv = compute_advantage(unit, target, item, target.get_weapon(), False)
    if adv:
        triangle_bonus += int(adv.damage)
    if disadv:
        triangle_bonus += int(disadv.damage)

    adv = compute_advantage(target, unit, target.get_weapon(), item)
    disadv = compute_advantage(target, unit, target.get_weapon(), item, False)
    if adv:
        triangle_bonus -= int(adv.resist)
    if disadv:
        triangle_bonus -= int(disadv.resist)
    might += triangle_bonus
    total_might = might

    might -= defense(target, item)

    if crit:
        might *= equations.parser.crit_mult(unit)
        for _ in range(equations.parser.crit_add(unit)):
            might += total_might

    might *= item_system.damage_multiplier(unit, item, target, mode)

    return int(max(DB.constants.get('min_damage').value, might))

def outspeed(unit, target, item, mode=None) -> bool:
    if not item:
        item = unit.get_weapon()

    speed = attack_speed(unit, item)

    # Handles things like effective damage
    speed += item_system.modify_attack_speed(unit, item, target, mode)

    # Weapon Triangle
    triangle_bonus = 0

    adv = compute_advantage(unit, target, item, target.get_weapon())
    disadv = compute_advantage(unit, target, item, target.get_weapon(), False)
    if adv:
        triangle_bonus += int(adv.attack_speed)
    if disadv:
        triangle_bonus += int(disadv.attack_speed)

    adv = compute_advantage(target, unit, target.get_weapon(), item)
    disadv = compute_advantage(target, unit, target.get_weapon(), item, False)
    if adv:
        triangle_bonus -= int(adv.defense_speed)
    if disadv:
        triangle_bonus -= int(disadv.defense_speed)

    speed -= defense_speed(target, item)

    # Skills and Status TODO
    return 2 if speed >= equations.parser.speed_to_double() else 1
