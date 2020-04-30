from app import utilities

from app.data.database import DB

from app.engine.sprites import SPRITES, FONT
import app.engine.config as cf
from app.engine import engine, base_surf, text_funcs, icons
from app.engine.game_state import game

class HelpDialog():
    help_logo = SPRITES.get('help_logo')
    font = FONT['convo_black']

    def __init__(self, desc, num_lines=2, name=False):
        self.name = name
        self.last_time = self.start_time = 0
        self.transition_in = False
        self.transition_out = 0

        if not desc:
            desc = ''
        desc = text_funcs.translate(desc)
        # Hard set num lines if desc is very short
        if len(desc) < 24:
            num_lines = 1

        self.lines = text_funcs.split(self.font, desc, num_lines)

        greater_line_len = max([self.font.width(line) for line in self.lines])
        if self.name:
            greater_line_len = max(greater_line_len, self.font.size(self.name)[0])

        self.width = greater_line_len + 24
        if self.name:
            num_lines += 1
        self.height = self.font.height * num_lines + 16

        self.help_surf = base_surf.create_base_surf(self.width, self.height, 'message_bg_base') 
        self.h_surf = engine.create_surface((self.width, self.height + 3), transparent=True)

    def get_width(self):
        return self.help_surf.get_width()

    def get_height(self):
        return self.help_surf.get_height()

    def handle_transition_in(self, time, h_surf):
        if self.transition_in:
            progress = (time - self.start_time) / 130.
            if progress >= 1:
                self.transition_in = False
            else:
                h_surf = engine.transform_scale(h_surf, (int(progress * h_surf.get_width()), int(progress * h_surf.get_height())))
        return h_surf

    def set_transition_out(self):
        self.transition_out = engine.get_time()

    def handle_transition_out(self, time, h_surf):
        if self.transition_out:
            progress = 1 - (time - self.transition_out) / 100.
            if progress <= 0.1:
                self.transition_out = 0
                progress = 0.1
            h_surf = engine.transform_scale(h_surf, (int(progress * h_surf.get_width()), int(progress * h_surf.get_height())))
        return h_surf

    def final_draw(self, surf, pos, time, help_surf):
        # Draw help logo
        h_surf = engine.copy_surface(self.h_surf)
        h_surf.blit(help_surf, (0, 3))
        h_surf.blit(self.help_logo, (9, 0))

        if self.transition_in:
            h_surf = self.handle_transition_in(time, h_surf)
        elif self.transition_out:
            h_surf = self.handle_transition_out(time, h_surf)

        surf.blit(h_surf, pos)
        return surf

    def draw(self, surf, pos):
        time = engine.get_time()
        if time > self.last_time + 1000:  # If it's been at least a second since last update
            self.start_time = time - 16
            self.transition_in = True
        self.last_time = time

        help_surf = engine.copy_surface(self.help_surf)
        if self.name:
            self.font.blit(self.name, help_surf, (8, 8))

        if cf.SETTINGS['text_speed'] > 0:
            num_characters = int(2 * (time - self.start_time) / float(cf.SETTINGS['text_speed']))
        else:
            num_characters = 1000
        for idx, line in enumerate(self.lines):
            if num_characters > 0:
                self.font.blit(line[:num_characters], help_surf, (8, self.font.height * idx + 8 + (16 if self.name else 0)))
                num_characters -= len(line)

        surf = self.final_draw(surf, pos, time, help_surf)
        return surf

class ItemHelpDialog(HelpDialog):
    font_blue = FONT['text_blue']
    font_yellow = FONT['text_yellow']

    def __init__(self, item):
        self.last_time = self.start_time = 0
        self.transition_in = False
        self.transition_out = 0

        self.item = item

        if self.item.level:
            weapon_level = self.item.level.value
        elif self.item.prf_unit or self.item.prf_class:
            weapon_level = 'Prf'
        else:
            weapon_level = '--'
        might = self.item.might.value if self.item.might else '--'
        hit = self.item.hit.value if self.item.hit else '--'
        if DB.constants.get('crit').value:
            crit = self.item.crit.value if self.item.crit else '--'
        else:
            crit = None
        weight = self.item.weight.value if self.item.weight else '--'
        min_rng = self.item.minimum_range
        max_rng = self.item.maximum_range
        if utilities.is_int(min_rng) and utilities.is_int(max_rng):
            if min_rng == max_rng:
                rng = min_rng
            else:
                rng = '%d-%d' % (min_rng, max_rng)
        else:
            owner = game.get_unit(self.owner_nid)
            item_range = game.equations.get_range(self.item, owner)
            rng = '%d-%d' % (min(item_range), max(item_range))

        self.vals = (weapon_level, rng, weight, might, hit, crit)

        if self.item.desc:
            self.lines = text_funcs.line_wrap(self.font, self.item.desc, 164)
        else:
            self.lines = []

        size_y = 48 + self.font.height * len(self.lines)
        self.help_surf = base_surf.create_base_surf((176, size_y), 'message_bg_base')
        self.h_surf = engine.create_surface((176, size_y + 3), transparent=True)

    def draw(self, surf, pos):
        time = engine.get_time()
        if time > self.last_time + 1000:  # If it's been at least a second since last update
            self.start_time = time - 16
        self.last_time = time

        help_surf = engine.copy_surface(self.help_surf)
        if self.item.weapon:
            icons.draw_weapon(help_surf, self.item.weapon.value, (8, 6))
        elif self.item.spell:
            icons.draw_weapon(help_surf, self.item.spell.weapon_type, (8, 6))

        self.font_yellow.blit('Rng', (56, 6))
        self.font_yellow.blit('Wt', (116, 6))
        self.font_yellow.blit('Mt', (8, 22))
        self.font_yellow.blit('Hit', (56, 22))
        if self.vals[5] is not None:
            self.font_yellow.blit('Crit', (116, 22))

        self.font_blue.right_blit(self.vals[0], (54, 6))
        self.font_blue.right_blit(self.vals[1], (108, 6))
        self.font_blue.right_blit(self.vals[2], (160, 6))
        self.font_blue.right_blit(self.vals[3], (54, 22))
        self.font_blue.right_blit(self.vals[4], (108, 22))
        if self.vals[5] is not None:
            self.font_blue.right_blit(self.vals[5], (160, 22))

        if cf.SETTINGS['text_speed'] > 0:
            num_characters = int(2 * (time - self.start_time) / float(cf.SETTINGS['text_speed']))
        else:
            num_characters = 1000
        for idx, line in enumerate(self.lines):
            if num_characters > 0:
                self.font.blit(line[:num_characters], help_surf, (8, self.font.height * idx + 6 + 32))
                num_characters -= len(line)

        surf = self.final_draw(surf, pos, time, help_surf)
        return surf