from app.counters import generic3counter
from app.data.constants import TILEWIDTH, TILEHEIGHT, FRAMERATE
from app.engine.sprites import SPRITES
from app.engine import engine
from app.engine import config as cf
from app.engine.game_state import game
from app.engine.fluid_scroll import FluidScroll

import logging
logger = logging.getLogger(__name__)

class Cursor():
    def __init__(self):
        self.cursor_counter = generic3counter(20*FRAMERATE, 2*FRAMERATE, 8*FRAMERATE)
        self.position = (0, 0)
        self.draw_state = 0
        self.speed_state = False

        self.sprite = SPRITES.get('cursor')
        self.format_sprite(self.sprite)
        self.offset_x, self.offset_y = 0, 0

        self.fluid = FluidScroll(cf.SETTINGS['cursor_speed'])

    def get_hover(self):
        return game.grid.get_unit(self.position)

    def hide(self):
        self.draw_state = 0

    def show(self):
        self.draw_state = 1

    def set_turnwheel_sprite(self):
        self.draw_state = 3

    def set_pos(self, pos):
        logger.info("New position %s", pos)
        self.position = pos

    def autocursor(self):
        player_units = [unit for unit in game.level.units if unit.team == 'player']
        lord_units = [unit for unit in player_units if 'Lord' in unit.tags]
        if lord_units:
            self.set_pos(lord_units[0].position)
        elif player_units:
            self.set_pos(player_units[0].position)

    def take_input(self):
        self.fluid.update()
        directions = self.fluid.get_directions()

        if 'LEFT' in directions and self.position[0] > 0:
            self.move(-1, 0)
            game.camera.set_x(self.position[0])
        elif 'RIGHT' in directions and self.position[0] < game.tilemap.width - 1:
            self.move(1, 0)
            game.camera.set_x(self.position[0])

        if 'UP' in directions and self.position[1] > 0:
            self.move(0, -1)
            game.camera.set_y(self.position[1])
        elif 'DOWN' in directions and self.position[1] < game.tilemap.height - 1:
            self.move(0, 1)
            game.camera.set_y(self.position[1])

    def move(self, dx, dy):
        x, y = self.position
        self.position = x + dx, y + dy

        # If we are slow
        if cf.SETTINGS['cursor_speed'] >= 40:
            if self.speed_state:
                self.offset_x += 8*dx
                self.offset_y += 8*dy
            else:
                self.offset_x += 12*dx
                self.offset_y += 12*dy

    def update(self):
        self.cursor_counter.update(engine.get_time())
        left = self.cursor_counter.count * TILEWIDTH * 2
        hovered_unit = self.get_hover()
        if hovered_unit and hovered_unit.team == 'player' and not hovered_unit.finished:
            self.image = self.active_sprite
        else:
            self.image = engine.subsurface(self.passive_sprite, (left, 0, 32, 32))

    def format_sprite(self, sprite):
        self.passive_sprite = engine.subsurface(sprite, (0, 0, 128, 32))
        self.red_sprite = engine.subsurface(sprite, (0, 32, 128, 32))
        self.active_sprite = engine.subsurface(sprite, (0, 64, 32, 32))
        self.formation_sprite = engine.subsurface(sprite, (64, 64, 64, 32))
        self.green_sprite = engine.subsurface(sprite, (0, 96, 128, 32))

    def draw(self, surf):
        if self.draw_state:
            x, y = self.position
            left = x * TILEWIDTH - max(0, (self.image.get_width() - 16)//2) - self.offset_x
            top = y * TILEHEIGHT - max(0, (self.image.get_height() - 16)//2) - self.offset_y
            surf.blit(self.image, (left, top))

            # Now reset offset
            num = 8 if self.speed_state else 4
            if self.offset_x > 0:
                self.offset_x = max(0, self.offset_x - num)
            elif self.offset_x < 0:
                self.offset_x = min(0, self.offset_x + num)
            if self.offset_y > 0:
                self.offset_y = max(0, self.offset_y - num)
            elif self.offset_y < 0:
                self.offset_y = min(0, self.offset_y + num)
        return surf
