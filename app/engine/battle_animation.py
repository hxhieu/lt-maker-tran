import random

from app.resources.resources import RESOURCES
from app.data.database import DB

from app.engine.sound import SOUNDTHREAD
from app.engine import engine, image_mods

battle_anim_speed = 1

class BattleAnimation():
    idle_poses = {'Stand', 'RangedStand', 'TransformStand'}

    def __init__(self, anim_prefab, unit, item):
        self.anim_prefab = anim_prefab
        self.unit = unit
        self.item = item

        self.poses = []  # TODO Generate poses  -- 
        # Copy Stand -> RangedStand and Dodge -> RangedDodge if missing
        # Copy Attack -> Miss and Attack -> Critcal if missing
        self.frame_directory = {}  # TODO Generate Frame directory
        self.current_pose = None
        self.current_palette = None

        self.state = 'inert'
        self.in_basic_state: bool = False  # Is animation in a basic state?
        self.processing = False

        self.wait_for_hit: bool = False
        self.script_idx = 0
        self.current_frame = None
        self.under_frame = None
        self.over_frame = None
        self.frame_count = 0
        self.num_frames = 0

        # Pairing stuff
        self.owner = None
        self.partner_anim = None
        self.parent = self
        self.right = True
        self.at_range = 0
        self.init_position = None
        self.init_speed = 0
        self.entrance = 0

        # Effect stuff
        self.child_effects = []
        self.under_child_effects = []
        self.loop = False

        # For drawing
        self.animations = []
        self.blend = 0
        # Flash Frames
        self.foreground = None
        self.foreground_counter = 0
        self.background = None
        self.background_counter = 0
        self.flash_color = []
        self.flash_counter = 0
        self.flash_image = None
        self.screen_dodge_color = None
        self.screen_dodge_counter = 0
        self.screen_dodge_image = None
        # Opacity
        self.opacity = 255
        self.death_opacity = []
        # Offset
        self.static = False # Animation will always be in the same place on the screen
        self.ignore_pan = False  # Animation will ignore any panning
        self.pan_away = False

        self.lr_offset = []
        self.effect_offset = (0, 0)
        self.personal_offset = (0, 0)

    def pair(self, owner, partner_anim, right, at_range, entrance_frames=0, position=None, parent=None):
        self.owner = owner
        self.partner_anim = partner_anim
        self.parent = parent if parent else self
        self.right = right
        self.at_range = at_range
        self.entrance_frames = entrance_frames
        self.entrance_counter = entrance_frames
        self.init_position = position
        self.get_stand()
        self.script_idx = 0
        self.current_frame = None
        self.under_frame = None
        self.over_frame = None
        self.reset()

    def get_stand(self):
        if self.at_range:
            self.current_pose = 'RangedStand'
        else:
            self.current_pose = 'Stand'

    def start_anim(self, pose):
        self.change_pose(pose)
        self.script_idx = 0
        self.wait_for_hit = True
        self.reset_frames()

    def change_pose(self, pose):
        self.current_pose = pose

    def has_pose(self, pose) -> bool:
        return pose in self.poses

    def end_current_pose(self):
        if 'Stand' in self.poses:
            self.get_stand()
            self.state = 'run'
        else:
            self.state = 'inert'
        # Make sure to return to correct pan if we somehow didn't
        if self.pan_away:
            self.pan_away = False
            self.owner.pan_back()
        self.script_idx = 0

    def finish(self):
        self.get_stand()
        self.state = 'leaving'
        self.script_idx = 0

    def reset_frames(self):
        self.state = 'run'
        self.frame_count = 0
        self.num_frames = 0

    def can_proceed(self):
        return self.loop or self.state == 'wait'

    def done(self) -> bool:
        return self.state == 'inert' or (self.state == 'run' and self.current_pose in self.idle_poses)

    def dodge(self):
        if self.at_range:
            self.start_anim('RangedDodge')
        else:
            self.start_anim('Dodge')

    def add_effect(self, effect):
        pass

    def get_frames(self, num) -> int:
        return max(1, int(int(num) * battle_anim_speed))

    def start_dying_animation(self):
        self.state = 'dying'
        self.death_opacity = [0, 20, 20, 20, 20, 44, 44, 44, 44, 64,
                              64, 64, 64, 84, 84, 84, 108, 108, 108, 108, 
                              128, 128, 128, 128, 148, 148, 148, 148, 172, 172, 
                              172, 192, 192, 192, 192, 212, 212, 212, 212, 236,
                              236, 236, 236, 255, 255, 255, 0, 0, 0, 0,
                              0, 0, -1, 0, 0, 0, 0, 0, 0, 255, 
                              0, 0, 0, 0, 0, 0, 255, 0, 0, 0,
                              0, 0, 0, 255, 0, 0, 0, 0, 0, 0,
                              255, 0, 0, 0, 0, 0, 0]

    def wait_for_dying(self):
        if self.in_basic_state:
            self.num_frames = int(42 * battle_anim_speed)

    def clear_all_effects(self):
        for child in self.child_effects:
            child.clear_all_effects()
        for child in self.under_child_effects:
            child.clear_all_effects()
        self.child_effects.clear()
        self.under_child_effects.clear()

    def update(self):
        if self.state == 'run':
            # Read script
            if self.frame_count >= self.num_frames:
                self.processing = True
                self.read_script()
            if self.current_pose in self.poses:
                if self.script_idx >= len(self.poses[self.current_pose]):
                    # Check whether we should loop or end
                    if self.current_pose in self.idle_poses:
                        self.script_idx = 0  # Loop
                    else:
                        self.end_current_pose()
            else:
                self.end_current_pose()

            self.frame_count += 1
            if self.entrance_counter:
                self.entrance_counter -= 1

        elif self.state == 'dying':
            if self.death_opacity:
                opacity = self.death_opacity.pop()
                if opacity == -1:
                    opacity = 255
                    self.flash_color = (248, 248, 248)
                    self.flash_frames = 100
                    SOUNDTHREAD.play_sfx('CombatDeath')
                self.opacity = opacity
            else:
                self.state = 'inert'

        elif self.state == 'leaving':
            self.entrance_counter += 1
            if self.entrance_counter > self.entrance_frames:
                self.entrance_counter = self.entrance_frames
                self.state = 'inert'  # done

        elif self.state == 'wait':
            pass

        # Handle effects
        for child in self.child_effects:
            child.update()
        for child in self.under_child_effects:
            child.update()

        # Remove completed child effects
        self.child_effects = [child for child in self.child_effects if child.state != 'inert']
        self.under_child_effects = [child for child in self.under_child_effects if child.state != 'inert']

    def read_script(self):
        if not self.has_pose(self.current_pose):
            return
        script = self.poses[self.current_pose]
        while self.script_idx < len(script) and self.processing:
            command = script[self.script_idx]
            self.run_command(command)
            self.script_idx += 1

    def run_command(self, command):
        self.in_basic_state = False

        values = command.values
        if command.nid == 'frame':
            self.frame_count = 0
            self.num_frames = self.get_frames(values[0])
            self.current_frame = self.frame_directory.get(values[1])
            self.under_frame = self.over_frame = None
            self.processing = False  # No more processing -- need to wait at least a frame
        elif command.nid == 'over_frame':
            self.frame_count = 0
            self.num_frames = self.get_frames(values[0])
            self.over_frame = self.frame_directory.get(values[1])
            self.under_frame = self.current_frame = None
            self.processing = False
        elif command.nid == 'under_frame':
            self.frame_count = 0
            self.num_frames = self.get_frames(values[0])
            self.under_frame = self.frame_directory.get(values[1])
            self.over_frame = self.current_frame = None
            self.processing = False
        elif command.nid == 'frame_with_offset':
            self.frame_count = 0
            self.num_frames = self.get_frames(values[0])
            self.current_frame = self.frame_directory.get(values[1])
            self.under_frame = self.over_frame = None
            self.processing = False
            self.personal_offset = (int(values[2]), int(values[3]))
        elif command.nid == 'dual_frame':
            self.frame_count = 0
            self.num_frames = self.get_frames(values[0])
            self.current_frame = self.frame_directory.get(values[1])
            self.under_frame = self.frame_directory.get(values[1])
            self.over_frame = None
            self.processing = False
        elif command.nid == 'wait':
            self.frame_count = 0
            self.num_frames = self.get_frames(values[0])
            self.current_frame = self.over_frame = self.under_frame = None
            self.processing = False  # No more processing -- need to wait at least a frame

        elif command.nid == 'sound':
            SOUNDTHREAD.play_sfx(values[0])
        elif command.nid == 'random_sound':
            sound = random.choice(values)
            SOUNDTHREAD.play_sfx(sound)
        elif command.nid == 'stop_sound':
            SOUNDTHREAD.stop_sfx(values[0])

        elif command.nid == 'start_hit':
            self.owner.shake()
            self.owner.start_hit()
            if self.partner_anim:  # Also offset partner, since they got hit
                self.partner_anim.lr_offset = [-1, -2, -3, -2, -1]
        elif command.nid == 'wait_for_hit':
            if self.wait_for_hit:
                self.current_frame = self.frame_directory(values[0])
                self.under_frame = self.frame_directory(values[1])
                self.over_frame = None
                self.processing = False
                self.state = 'wait'
                self.in_basic_state = True
        elif command.nid == 'miss':
            if self.right:
                position = (72, 21)
            else:
                position = (128, 21)  # Enemy's position
            team = self.owner.right.team if self.right else self.owner.left.team
            color = utils.get_team_color(team)
            anim_nid = 'Miss%s' % color.capitalize()
            animation = RESOURCES.animations.get(anim_nid)
            if animation:
                anim = Animation(animation, position)
                self.animations.append(anim)
            self.owner.start_hit(miss=True)
            if self.partner_anim:
                self.partner_anim.dodge()
        elif command.nid == 'spell_hit':
            self.owner.spell_hit(values[0])
            self.state = 'wait'
            self.processing = False

        elif command.nid == 'effect':
            effect = values[0]
            child_effect = self.get_effect(effect)
            if child_effect:
                self.child_effects.append(child_effect)
        elif command.nid == 'under_effect':
            effect = values[0]
            child_effect = self.get_effect(effect)
            if child_effect:
                self.parent.under_child_effects.append(child_effect)
        elif command.nid == 'enemy_effect':
            effect = values[0]
            child_effect = self.get_effect(effect, enemy=True)
            if child_effect and self.partner_anim:
                self.partner_anim.child_effects.append(child_effect)
        elif command.nid == 'enemy_under_effect':
            effect = values[0]
            child_effect = self.get_effect(effect, enemy=True)
            if child_effect and self.partner_anim:
                self.partner_anim.under_child_effects.append(child_effect)
        elif command.nid == 'clear_all_effects':
            self.clear_all_effects()

        elif command.nid == 'spell':
            if values[0]:
                effect = values[0]
            else:
                effect = self.item.nid
            child_effect = self.get_effect(effect)
            if child_effect:
                self.child_effects.append(child_effect)

        elif command.nid == 'blend':
            if bool(values[0]):
                self.blend = engine.BLEND_RGB_ADD
            else:
                self.blend = 0
        elif command.nid == 'static':
            self.static = bool(values[0])
        elif command.nid == 'ignore_pan':
            self.ignore_pan = bool(values[0])
        elif command.nid == 'opacity':
            self.opacity = int(values[0])
        elif command.nid == 'parent_opacity':
            self.parent.opacity = int(values[0])

    def draw(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state == 'inert':
            return

        # Screen flash
        if self.background and not self.blend:
            engine.blit(surf, self.background, (0, 0), None, engine.BLEND_RGB_ADD)

        for child in self.under_child_effects:
            child.draw(surf, (0, 0), range_offset, pan_offset)

        if self.current_frame is not None:
            image, offset = self.get_image(self.current_frame, shake, range_offset, pan_offset, self.static)

            # Move the animations in at the beginnign and out at the end
            if self.entrance_counter:
                progress = (self.entrance_frames - self.entrance_counter) / self.entrance_frames
                new_size = int(progress * image.get_width()), int(progress * image.get_height())
                image = engine.transform_scale(image, new_size)
                if self.flash_color and self.flash_image:
                    self.flash_image = image
                diff_x = offset[0] - self.init_position[0]
                diff_y = offset[1] - self.init_position[1]
                offset = int(self.init_position[0] + progress * diff_x), int(self.init_position[1] + progress * diff_y)

            # Self flash
            image = self.handle_flash(image)

            # Self screen dodge
            image = self.handle_screen_dodge(image)

            if self.opacity != 255:
                if self.blend:
                    image = image_mods.make_translucent_blend(image, 255 - self.opacity)
                else:
                    image = image_mods.make_translucent(image.convert_alpha(), (255 - self.opacity)/255.)

            # Actually blit
            if self.background and self.blend:
                old_bg = self.background.copy()
                engine.blit(old_bg, image, offset)
                engine.blit(surf, old_bg, (0, 0), None, self.blend)
            else:
                engine.blit(surf, image, offset, None, self.blend)

        # Handle children
        for child in self.child_effects:
            child.draw(surf, (0, 0), range_offset, pan_offset)

        # Update and draw animations
        self.animations = [anim for anim in self.animations if not anim.update()]
        for anim in self.animations:
            anim.draw(surf)

        # Screen flash
        if self.foreground:
            engine.blit(surf, self.foreground, (0, 0), None, engine.BLEND_RGB_ADD)
            self.foreground_counter -= 1
            if self.foreground_counter <= 0:
                self.foreground = None
                self.foreground_counter = 0

        if self.background:
            # Draw above
            self.background_counter -= 1
            if self.background_counter <= 0:
                self.background = None
                self.background_counter = 0

    def draw_under(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'inert' and self.under_frame is not None:
            image, offset = self.get_image(self.under_frame, shake, range_offset, pan_offset, False)
            engine.blit(surf, image, offset, None, self.blend)

    def draw_over(self, surf, shake=(0, 0), range_offset=0, pan_offset=0):
        if self.state != 'inert' and self.over_frame is not None:
            image, offset = self.get_image(self.over_frame, shake, range_offset, pan_offset, False)
            engine.blit(surf, image, offset, None, self.blend)

    def get_image(self, frame, shake, range_offset, pan_offset, static) -> tuple:
        image = frame.image.copy()
        if not self.right:
            image = engine.flip_horiz(image)
        offset = frame.offset
        # Handle offset (placement of the object on the screen)
        if self.lr_offset:
            offset = offset[0] + self.lr_offset.pop(), offset[1]
        if self.effect_offset:
            offset = offset[0] + self.effect_offset[0], offset[1] + self.effect_offset[1]
        if self.personal_offset:
            offset = offset[0] + self.personal_offset[0], offset[1] + self.personal_offset[1]

        left = 0
        if not static:
            left += shake[0] + range_offset
        if self.at_range and not static:
            if self.ignore_pan:
                if self.right:
                    pan_max = range_offset - 24
                else:
                    pan_max = range_offset + 24
                left -= pan_max
            else:
                left += pan_offset

        if self.right:
            offset = offset[0] + shake[0] + left, offset[1] + shake[1]
        else:
            offset = WINWIDTH - offset[0] - image.get_width() + left, offset[1] + shake[1]
        return image, offset

    def handle_flash(self, image):
        if self.flash_color:
            if not self.flash_image:
                flash_color = self.flash_color[self.flash_counter % len(self.flash_color)]
                self.flash_image = image_mods.change_color(image.convert_alpha(), flash_color)
            self.flash_counter -= 1
            image = self.flash_image
            # done
            if self.flash_counter <= 0:
                self.flash_color.clear()
                self.flash_counter = 0
                self.flash_image = None
        return image

    def handle_screen_dodge(self, image):
        if self.screen_dodge_color:
            if not self.screen_dodge_image:
                self.screen_dodge_image = image_mods.screen_dodge(image.convert_alpha(), self.screen_dodge_color)
            self.screen_dodge_counter -= 1
            image = self.screen_dodge_image
            # done
            if self.screen_dodge_color <= 0:
                self.screen_dodge_color = None
                self.screen_dodge_frames = 0
                self.screen_dodge_image = None
        return image

def get_battle_anim(unit, item) -> BattleAnimation:
    class_obj = DB.classes.get(unit.klass)
    combat_anim_nid = class_obj.combat_anim_nid
    if unit.variant:
        combat_anim_nid += unit.variant
    res = RESOURCES.combat_anims.get(combat_anim_nid)
    if not res:  # Try without unit variant
        res = RESOURCES.combat_anims.get(class_obj.combat_anim_nid)
    if not res:
        return None

    battle_anim = BattleAnimation(res, unit, item)
    return battle_anim
