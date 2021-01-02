from app.utilities import utils
from app.utilities.data import Prefab
from app.data.database import DB

from app.engine import equations, item_system, item_funcs, skill_system, unit_funcs
from app.engine.game_state import game

# Main unit object used by engine
class UnitObject(Prefab):
    @classmethod
    def from_prefab(cls, prefab):
        self = cls()
        self.nid = prefab.nid
        if prefab.starting_position:
            self.position = self.previous_position = tuple(prefab.starting_position)
        else:
            self.position = self.previous_position = None
        self.team = prefab.team
        self.party = None
        self.klass = prefab.klass
        self.variant = prefab.variant
        self.level = prefab.level
        self.exp = 0
        self.generic = prefab.generic

        self.ai = prefab.ai

        self.items = item_funcs.create_items(self, prefab.starting_items)

        if self.generic:
            self.faction = prefab.faction
            self.name = DB.factions.get(self.faction).name
            self.desc = DB.factions.get(self.faction).desc
            self._tags = []
            self.stats = {stat.nid: stat.value for stat in DB.classes.get(self.klass).bases}
            self.growths = {stat.nid: stat.value for stat in DB.classes.get(self.klass).growths}
            klass_obj = DB.classes.get(self.klass)
            self.wexp = {weapon.nid: klass_obj.wexp_gain.get(weapon.nid).wexp_gain for weapon in DB.weapons}
            self.calculate_needed_wexp_from_items()
            self.portrait_nid = None
        else:
            self.faction = None
            self.name = prefab.name
            self.desc = prefab.desc
            self._tags = [tag for tag in prefab.tags]
            self.stats = {stat.nid: stat.value for stat in prefab.bases}
            self.growths = {stat.nid: stat.value for stat in prefab.growths}
            self.wexp = {weapon.nid: weapon.wexp_gain for weapon in prefab.wexp_gain}
            self.portrait_nid = prefab.portrait_nid
        self.starting_position = self.position
            
        if DB.constants.get('player_leveling').value == 'Fixed':
            self.growth_points = {k: 50 for k in self.stats.keys()}
        else:
            self.growth_points = {k: 0 for k in self.stats.keys()}

        # Handle skills
        personal_skills = unit_funcs.get_personal_skills(self, prefab)
        class_skills = unit_funcs.get_starting_skills(self)
        self.skills = personal_skills + class_skills

        self.current_hp = equations.parser.hitpoints(self)
        if 'MANA' in DB.equations:
            self.current_mana = equations.parser.mana(self)
        else:
            self.current_mana = 0
        self.current_fatigue = 0
        self.movement_left = equations.parser.movement(self)

        self.traveler = None

        # -- Equipped Items
        self.equipped_weapon = None
        self.equipped_accessory = None
        self.equipped_weapon = self.get_weapon()
        self.equipped_accessory = self.get_accessory()

        # -- Other properties
        self.dead = False
        self.is_dying = False
        self._finished = False
        self._has_attacked = False
        self._has_traded = False
        self._has_moved = False

        # For rescue
        self.has_rescued = False
        self.has_taken = False
        self.has_given = False
        self.has_dropped = False

        self._sprite = None
        self._sound = None
        self.battle_anim = None

        self.current_move = None  # Holds the move action the unit last used
        # Maybe move to movement manager?
        return self

    def get_hp(self):
        return self.current_hp

    def set_hp(self, val):
        self.current_hp = int(utils.clamp(val, 0, equations.parser.hitpoints(self)))

    def get_mana(self):
        return self.current_mana

    def set_mana(self, val):
        if 'MANA' in DB.equations:
            max_mana = equations.parser.mana(self)
            self.current_mana = int(utils.clamp(val, 0, max_mana))
        else:
            self.current_mana = 0

    def get_fatigue(self):
        return self.current_fatigue

    def set_fatigue(self, val):
        self.current_fatigue = int(utils.clamp(val, 0, equations.parser.fatigue(self)))

    def get_exp(self):
        return self.exp

    def set_exp(self, val):
        self.exp = int(utils.clamp(val, 0, 100))

    def stat_bonus(self, stat):
        return skill_system.stat_change(self, stat)

    @property
    def sprite(self):
        if not self._sprite:
            from app.engine import unit_sprite
            self._sprite = unit_sprite.UnitSprite(self)
        return self._sprite

    @property
    def sound(self):
        if not self._sound:
            from app.engine import unit_sound
            self._sound = unit_sound.UnitSound(self)
        return self._sound
    
    @property
    def tags(self):
        unit_tags = self._tags
        class_tags = DB.classes.get(self.klass).tags
        return unit_tags + class_tags

    @property
    def accessories(self):
        return [item for item in self.items if item_system.is_accessory(self, item)]

    @property
    def nonaccessories(self):
        return [item for item in self.items if not item_system.is_accessory(self, item)]

    def calculate_needed_wexp_from_items(self):
        for item in item_funcs.get_all_items(self):
            weapon_rank_required = item_system.weapon_rank(self, item)
            if weapon_rank_required:
                weapon_type = item_system.weapon_type(self, item)
                requirement = DB.weapon_ranks.get(weapon_rank_required).requirement
                self.wexp[weapon_type] = max(self.wexp[weapon_type], requirement)

    def get_weapon(self):
        if self.equipped_weapon:
            return self.equipped_weapon
        else:
            for item in self.items:
                weapon = item_system.is_weapon(self, item)
                available = item_funcs.available(self, item)
                equippable = item_system.equippable(self, item)
                if weapon and available and equippable:
                    # Don't think I need to wrap this in an action thing
                    # Since it's more of an attribute that will be 
                    # rediscovered each time if necessary
                    self.equip(item)  
                    return item
        return None

    def get_spell(self):
        for item in self.items:
            if item_system.is_spell(self, item) and item_funcs.available(self, item):
                return item
        return None

    def get_accessory(self):
        if self.equipped_accessory:
            return self.equipped_accessory
        else:
            for item in self.items:
                if item_system.is_accessory(self, item) and \
                        item_funcs.available(self, item) and \
                        item_system.equippable(self, item):
                    return item
        return None

    def equip(self, item):
        if item_system.is_accessory(self, item) and item is self.equipped_accessory:
            return  # Don't need to do anything
        elif item is self.equipped_weapon:
            return  # Don't need to do anything
        if item_system.equippable(self, item) and item_funcs.available(self, item):
            if item_system.is_accessory(self, item):
                if self.equipped_accessory:
                    self.unequip(self.equipped_accessory)
                self.equipped_accessory = item
            else:
                if self.equipped_weapon:
                    self.unequip(self.equipped_weapon)
                self.equipped_weapon = item
            item_system.on_equip_item(self, item)
            skill_system.on_equip_item(self, item)

    def unequip(self, item):
        if item_system.is_accessory(self, item):
            self.equipped_accessory = None
        else:
            self.equipped_weapon = None
        skill_system.on_unequip_item(self, item)
        item_system.on_unequip_item(self, item)

    def add_item(self, item):
        index = len(self.items)
        self.insert_item(index, item)

    def bring_to_top_item(self, item):
        if item_system.is_accessory(self, item):
            self.items.remove(item)
            self.items.insert(len(self.nonaccessories), item)
        else:
            self.items.remove(item)
            self.items.insert(0, item)

    def insert_item(self, index, item):
        if item in self.items:
            self.items.remove(item)
            self.items.insert(index, item)
        else:
            self.items.insert(index, item)
            item.owner_nid = self.nid
            # Statuses here
            item_system.on_add_item(self, item)
            skill_system.on_add_item(self, item)

    def remove_item(self, item):
        if item is self.equipped_weapon or item is self.equipped_accessory:
            self.unequip(item)
        self.items.remove(item)
        item.owner_nid = None
        # Status effects
        skill_system.on_remove_item(self, item)
        item_system.on_remove_item(self, item)
        # There may be a new item equipped
        self.get_weapon()
        self.get_accessory()

    def get_internal_level(self):
        klass = DB.classes.get(self.klass)
        if klass.tier == 0:
            return self.level - klass.max_level
        elif klass.tier == 1:
            return self.level
        else:
            running_total = self.level
            # Need do while
            counter = 5
            while counter > 0:
                counter -= 1  # Just to make sure no infinte loop
                promotes_from = klass.promotes_from
                if promotes_from:
                    klass = DB.classes.get(promotes_from)
                    running_total += klass.max_level
                else:
                    return running_total
                if klass.tier <= 0:
                    return running_total
            return running_total 

    def get_group(self) -> str:
        if not game.level:
            return None
        groups = game.level.unit_groups
        for group in groups:
            if self in group.units:
                return group.nid
        return None

    @property
    def finished(self):
        return self._finished

    @property
    def has_attacked(self):
        return self._finished or self._has_attacked

    @property
    def has_traded(self):
        return self._finished or self._has_attacked or self._has_traded

    @property
    def has_moved(self):
        return self._finished or self._has_attacked or self._has_traded or self._has_moved

    @finished.setter
    def finished(self, val):
        self._finished = val

    @has_attacked.setter
    def has_attacked(self, val):
        self._has_attacked = val

    @has_traded.setter
    def has_traded(self, val):
        self._has_traded = val

    @has_moved.setter
    def has_moved(self, val):
        self._has_moved = val

    def get_action_state(self):
        return (self._finished, self._has_attacked, self._has_traded, self._has_moved, 
                self.has_rescued, self.has_dropped, self.has_taken, self.has_given)

    def set_action_state(self, state):
        self._finished = state[0]
        self._has_attacked = state[1]
        self._has_traded = state[2]
        self._has_moved = state[3]

        self.has_rescued = state[4]
        self.has_dropped = state[5]
        self.has_taken = state[6]
        self.has_given = state[7]

    def reset(self):
        self._finished = False
        self._has_attacked = False
        self._has_traded = False
        self._has_moved = False

        self.has_rescued = False
        self.has_dropped = False
        self.has_taken = False
        self.has_given = False

    def clean_up(self):
        if self.traveler:
            self.traveler = None
            # Remove rescue penalty

        self.set_hp(1000)  # Set to full health

        # TODO remove temporary statuses
        self.position = None
        if self._sprite:
            self._sprite.change_state('normal')
        self.reset()

    def save(self):
        s_dict = {'nid': self.nid,
                  'position': self.position,
                  'team': self.team,
                  'party': self.party,
                  'klass': self.klass,
                  'variant': self.variant,
                  'faction': self.faction,
                  'level': self.level,
                  'exp': self.exp,
                  'generic': self.generic,
                  'ai': self.ai,
                  'items': [item.uid for item in self.items],
                  'name': self.name,
                  'desc': self.desc,
                  'tags': self._tags,
                  'stats': self.stats,
                  'growths': self.growths,
                  'growth_points': self.growth_points,
                  'starting_position': self.starting_position,
                  'wexp': self.wexp,
                  'portrait_nid': self.portrait_nid,
                  'skills': [skill.uid for skill in self.skills],
                  'current_hp': self.current_hp,
                  'current_mana': self.current_mana,
                  'current_fatigue': self.current_fatigue,
                  'traveler': self.traveler,
                  'dead': self.dead,
                  'action_state': self.get_action_state(),
                  }
        return s_dict

    @classmethod
    def restore(cls, s_dict):
        self = cls()
        self.nid = s_dict['nid']
        if s_dict['position']:
            self.position = self.previous_position = tuple(s_dict['position'])
        else:
            self.position = self.previous_position = None
        self.team = s_dict['team']
        self.party = s_dict['party']
        self.klass = s_dict['klass']
        self.variant = s_dict['variant']
        self.level = s_dict['level']
        self.exp = s_dict['exp']
        self.generic = s_dict['generic']

        self.ai = s_dict['ai']

        self.items = [game.get_item(item_uid) for item_uid in s_dict['items']]
        self.items = [i for i in self.items if i]

        self.faction = s_dict['faction']
        self.name = s_dict['name']
        self.desc = s_dict['desc']
        self._tags = s_dict['tags']
        self.stats = s_dict['stats']
        self.growths = s_dict['growths']
        self.growth_points = s_dict['growth_points']
        self.wexp = s_dict['wexp']
        self.portrait_nid = s_dict['portrait_nid']
        self.starting_position = self.position

        self.skills = [game.get_skill(skill_uid) for skill_uid in s_dict['skills']]
        self.skills = [s for s in self.skills if s]

        self.current_hp = s_dict['current_hp']
        self.current_mana = s_dict['current_mana']
        self.current_fatigue = s_dict['current_fatigue']
        self.movement_left = equations.parser.movement(self)

        self.traveler = s_dict['traveler']

        self.equipped_weapon = None
        self.equipped_accessory = None
        self.equipped_weapon = self.get_weapon()
        self.equipped_accessory = self.get_accessory()

        # -- Other properties
        self.dead = s_dict['dead']
        self.is_dying = False
        action_state = s_dict.get('action_state')
        if action_state:
            self.set_action_state(action_state)

        self._sprite = None
        self._sound = None
        self.battle_anim = None

        self.current_move = None  # Holds the move action the unit last used
        # Maybe move to movement manager?
        return self
