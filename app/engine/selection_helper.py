from app.utilities import utils
from app.constants import TILEWIDTH, TILEHEIGHT
from app.engine.input_manager import INPUT

class SelectionHelper():
    def __init__(self, pos_list):
        self.pos_list = pos_list

    def handle_mouse(self):
        mouse_position = INPUT.get_mouse_position()
        if mouse_position:
            new_pos = mouse_position[0] // TILEWIDTH, mouse_position[1] // TILEHEIGHT
            if new_pos in self.pos_list:
                return new_pos
        return None

    # For a given position, determine which position in self.pos_list is closest
    def get_closest(self, position):
        if self.pos_list:
            return min(self.pos_list, key=lambda pos: utils.calculate_distance(pos, position))
        else:
            return None

    # For a given position, determine which position in self.pos_list is the closest position in the downward direction
    def get_down(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[1] > position[1]: # If further down than the position
                dist = utils.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

    def get_up(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[1] < position[1]: # If further up than the position
                dist = utils.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

    def get_right(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[0] > position[0]: # If further right than the position
                dist = utils.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest

    def get_left(self, position):
        min_distance, closest = 100, None
        for pos in self.pos_list:
            if pos[0] < position[0]: # If further left than the position
                dist = utils.calculate_distance(pos, position)
                if dist < min_distance:
                    closest = pos
                    min_distance = dist
        if closest is None: # Nothing was found in the down direction
            # Just find the closest
            closest = self.get_closest(position)
        return closest
