from app.constants import TILEWIDTH, TILEHEIGHT, WINWIDTH, WINHEIGHT, FRAMERATE

from app.counters import generic3counter, simplecounter

from app.engine import engine, unit_sprite, unit_sound
from app.engine.game_state import game

class MapView():
    def __init__(self):
        self.passive_sprite_counter = generic3counter(32 * FRAMERATE, 4 * FRAMERATE)
        self.active_sprite_counter = generic3counter(13 * FRAMERATE, 6 * FRAMERATE)
        self.move_sprite_counter = simplecounter((10 * FRAMERATE, 5 * FRAMERATE, 10 * FRAMERATE, 5 * FRAMERATE))
        self.fast_move_sprite_counter = simplecounter((6 * FRAMERATE, 3 * FRAMERATE, 6 * FRAMERATE, 3 * FRAMERATE))
        self.attack_movement_counter = generic3counter(4 * FRAMERATE, 3 * FRAMERATE, 4 * FRAMERATE)
        self.arrow_counter = simplecounter((16 * FRAMERATE, 16 * FRAMERATE, 16 * FRAMERATE))
        self.x2_counter = simplecounter([3 * FRAMERATE] * 18)

    def update(self):
        current_time = engine.get_time()
        self.passive_sprite_counter.update(current_time)
        self.active_sprite_counter.update(current_time)
        self.move_sprite_counter.update(current_time)
        self.fast_move_sprite_counter.update(current_time)
        self.attack_movement_counter.update(current_time)
        self.arrow_counter.update(current_time)
        self.x2_counter.update(current_time)

    def draw_units(self, surf):
        culled_units = [unit for unit in game.level.units if unit.position]
        if game.level.fog_of_war:
            culled_units = [unit for unit in culled_units if game.board.in_vision(unit.position)]
        draw_units = sorted(culled_units, key=lambda unit: unit.position[1])
        for unit in draw_units:
            if not unit.sprite:
                unit.sprite = unit_sprite.UnitSprite(unit)
            if not unit.sound:
                unit.sound = unit_sound.UnitSound(unit)
            unit.sprite.update()
            unit.sound.update()
            surf = unit.sprite.draw(surf)
        for unit in draw_units:
            surf = unit.sprite.draw_hp(surf)

    def draw(self):
        map_image = game.level.tilemap.get_full_image()
        surf = engine.copy_surface(map_image)
        surf = surf.convert_alpha()
        surf = game.boundary.draw(surf, (surf.get_width(), surf.get_height()))
        surf = game.highlight.draw(surf)
        surf = game.cursor.draw_arrows(surf)
        self.draw_units(surf)
        surf = game.cursor.draw(surf)

        # Camera Cull
        rect = game.camera.get_x() * TILEWIDTH, game.camera.get_y() * TILEHEIGHT, WINWIDTH, WINHEIGHT
        surf = engine.subsurface(surf, rect)

        surf = game.ui_view.draw(surf)
        return surf
