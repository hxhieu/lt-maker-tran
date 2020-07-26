import os
import shutil

from app.resources.base_catalog import ManifestCatalog

class Song():
    def __init__(self, nid, full_path=None):
        self.nid = nid
        self.full_path = full_path

        # Mutually exclusive. Can't have both start and battle versions
        self.intro_full_path = None
        self.battle_full_path = None

    def set_full_path(self, full_path):
        self.full_path = full_path

    def set_intro_full_path(self, full_path):
        self.intro_full_path = full_path

    def set_battle_full_path(self, full_path):
        self.battle_full_path = full_path

    def serialize(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['full_path'] = os.path.split(self.full_path)[-1]
        s_dict['intro_full_path'] = os.path.split(self.intro_full_path)[-1] if self.intro_full_path else None
        s_dict['battle_full_path'] = os.path.split(self.battle_full_path)[-1] if self.battle_full_path else None
        return s_dict

    @classmethod
    def deserialize(cls, s_dict):
        self = cls(s_dict['nid'], s_dict['full_path'])
        self.intro_full_path = s_dict['intro_full_path']
        self.battle_full_path = s_dict['battle_full_path']
        return self

class MusicCatalog(ManifestCatalog):
    manifest = 'music.json'
    title = 'music'
    filetype = '.ogg'

    def load(self, loc):
        music_dict = self.read_manifest(os.path.join(loc, self.manifest))
        for s_dict in music_dict:
            new_song = Song.deserialize(s_dict)
            new_song.set_full_path(os.path.join(loc, new_song.full_path))
            if new_song.battle_full_path:
                new_song.set_battle_full_path(os.path.join(loc, new_song.battle_full_path))
            if new_song.intro_full_path:
                new_song.set_intro_full_path(os.path.join(loc, new_song.intro_full_path))
            self.append(new_song)

    def save(self, loc):
        for song in self:
            # Full Path
            new_full_path = os.path.join(loc, song.nid + '.ogg')
            if os.path.abspath(song.full_path) != os.path.abspath(new_full_path):
                shutil.copy(song.full_path, new_full_path)
                song.set_full_path(new_full_path)
            # Battle Full Path
            new_full_path = os.path.join(loc, song.nid + '_battle.ogg')
            if song.battle_full_path and os.path.abspath(song.battle_full_path) != os.path.abspath(new_full_path):
                shutil.copy(song.battle_full_path, new_full_path)
                song.set_battle_full_path(new_full_path)
            # Intro Full Path
            new_full_path = os.path.join(loc, song.nid + '_intro.ogg')
            if song.intro_full_path and os.path.abspath(song.intro_full_path) != os.path.abspath(new_full_path):
                shutil.copy(song.intro_full_path, new_full_path)
                song.set_intro_full_path(new_full_path)
        self.dump(loc)

class SFX():
    def __init__(self, nid, full_path=None):
        self.nid = nid
        self.tag = None
        self.full_path = full_path

    def set_full_path(self, full_path):
        self.full_path = full_path

    def serialize(self):
        return (self.nid, self.tag, os.path.split(self.full_path)[-1])

    @classmethod
    def deserialize(cls, s_tuple):
        self = cls(s_tuple[0], s_tuple[2])
        self.tag = s_tuple[1]
        return self

class SFXCatalog(ManifestCatalog):
    manifest = 'sfx.json'
    title = 'sfx'
    filetype = '.ogg'

    def load(self, loc):
        sfx_dict = self.read_manifest(os.path.join(loc, self.manifest))
        temp_list = []
        for s_tuple in sfx_dict:
            new_sfx = SFX.deserialize(s_tuple)
            new_sfx.set_full_path(os.path.join(loc, new_sfx.full_path))
            temp_list.append(new_sfx)
        # Need to sort according to tag
        temp_list = sorted(temp_list, key=lambda x: x.tag if x.tag else '____')
        for sfx in temp_list:
            self.append(sfx)