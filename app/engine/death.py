from app.engine.sound import SOUNDTHREAD
from app.engine import action
from app.engine.game_state import game

class DeathManager():
    def __init__(self):
        self.dying_units = {}

    def should_die(self, unit):
        unit.is_dying = True
        self.dying_units[unit.nid] = 0

    def miracle(self, unit):
        unit.is_dying = False
        if unit.nid in self.dying_units:
            del self.dying_units[unit.nid]

    def force_death(self, unit):
        unit.is_dying = False
        action.do(action.Die(unit))
        if unit.nid in self.dying_units:
            del self.dying_units[unit.nid]

    def update(self) -> bool:
        for unit_nid in list(self.dying_units.keys()):
            death_counter = self.dying_units[unit_nid]
            unit = game.get_unit(unit_nid)
            if death_counter == 0:
                SOUNDTHREAD.play_sfx('Death')
            elif death_counter == 1:
                unit.sprite.start_flicker(0, 450, (255, 255, 255), fade_out=False)
                unit.sprite.set_transition('fade_out')

            self.dying_units[unit_nid] += 1

            if death_counter >= 27:
                self.force_death(unit)

        return not self.dying_units  # Done when no dying units left

    def is_dying(self, unit):
        return unit.nid in self.dying_units
