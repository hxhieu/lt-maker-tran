import os

from app.constants import TILEWIDTH, TILEHEIGHT, TILEX, TILEY

from app.utilities.data import Data, Prefab
from app.resources.base_catalog import ManifestCatalog

class TileMapPrefab(Prefab):
    def __init__(self, nid):
        self.nid = nid
        self.width, self.height = TILEX, TILEY
        self.layers = Data()
        self.layers.append(LayerGrid('base', self))

        self.tilesets = []  # Opened tilesets associated with this tilemap, nothing more
        self.image = None  # Icon used for drawing in resource editor

    def clear(self):
        self.width, self.height = TILEX, TILEY
        self.layers.clear()
        self.layers.append(LayerGrid('base', self))

    def check_bounds(self, pos):
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    def get_terrain(self, pos):
        for layer in reversed(self.layers):
            if layer.visible and pos in layer.terrain_grid:
                return layer.terrain_grid[pos]

    def resize(self, width, height, x_offset, y_offset):
        self.width = width
        self.height = height

        for layer in self.layers:
            # Terrain
            new_terrain_grid = {}
            for coord, terrain_nid in layer.terrain_grid.items():
                new_coord = coord[0] + x_offset, coord[1] + y_offset
                if self.check_bounds(new_coord):
                    new_terrain_grid[new_coord] = terrain_nid
            layer.terrain_grid = new_terrain_grid
            # Tile Sprites
            new_sprite_grid = {}
            for coord, tile_sprite in layer.sprite_grid.items():
                new_coord = coord[0] + x_offset, coord[1] + y_offset
                if self.check_bounds(new_coord):
                    new_sprite_grid[new_coord] = tile_sprite
            layer.sprite_grid = new_sprite_grid

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['size'] = self.width, self.height
        if self.width == 0 or self.height == 0:
            print("TileMap: Width or Height == 0!!!")
        s_dict['layers'] = [layer.save() for layer in self.layers]
        s_dict['tilesets'] = self.tilesets
        return s_dict

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        self.width, self.height = s_dict['size']
        self.tilesets = s_dict['tilesets']
        self.layers = Data([LayerGrid.restore(layer, self) for layer in s_dict['layers']])
        return self

class TileSet(Prefab):
    def __init__(self, nid, full_path=None):
        self.nid = nid
        self.width, self.height = 0, 0
        self.terrain_grid = {}
        self.full_path = full_path

        self.image = None
        self.subimages = {}

    def check_bounds(self, pos):
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    def set_pixmap(self, pixmap):
        self.image = pixmap
        self.width = self.pixmap.width() // TILEWIDTH
        self.height = self.pixmap.height() // TILEHEIGHT
        # Subsurface
        self.subimages.clear()
        for x in range(self.width):
            for y in range(self.height):
                p = self.image.copy(x * TILEWIDTH, y * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
                self.subimages[(x, y)] = p

    def get_pixmap(self, pos):
        if pos in self.subimages:
            return self.subimages[pos]
        return None

    def set_full_path(self, full_path):
        self.full_path = full_path

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        # s_dict['size'] = (self.width, self.height)
        s_dict['terrain_grid'] = {}
        for coord, terrain_nid in self.terrain_grid.items():
            str_coord = "%d,%d" % (coord[0], coord[1])
            s_dict['terrain_grid'][str_coord] = terrain_nid
        return s_dict

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        # self.width, self.height = s_dict['size']
        for str_coord, terrain_nid in s_dict['terrain_grid'].items():
            coord = tuple(int(_) for _ in str_coord.split(','))
            self.terrain_grid[coord] = terrain_nid
        return self

class LayerGrid(Prefab):
    def __init__(self, nid: str, parent):
        self.nid: str = nid
        self.parent = parent
        self.visible: bool = True
        self.terrain_grid = {}
        self.sprite_grid = {}

    def set(self, coord, tile, tile_sprite):
        self.terrain_grid[coord] = tile
        self.sprite_grid[coord] = tile_sprite

    def get_terrain(self, coord):
        return self.terrain_grid.get(coord)

    def get_sprite(self, coord):
        return self.sprite_grid.get(coord)

    def set_sprite(self, self_coord, tileset_nid, tileset_coord):
        tile_sprite = TileSprite(tileset_nid, tileset_coord, self)
        self.sprite_grid[self_coord] = tile_sprite

    def erase_sprite(self, coord):
        if coord in self.sprite_grid:
            del self.sprite_grid[coord]

    def erase_terrain(self, coord):
        if coord in self.terrain_grid:
            del self.terrain_grid[coord]

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['visible'] = self.visible
        s_dict['terrain_grid'] = {}
        for coord, terrain_nid in self.terrain_grid.items():
            str_coord = "%d,%d" % (coord[0], coord[1])
            s_dict['terrain_grid'][str_coord] = terrain_nid
        s_dict['sprite_grid'] = {}
        for coord, tile_sprite in self.sprite_grid.items():
            str_coord = "%d,%d" % (coord[0], coord[1])
            s_dict['sprite_grid'][str_coord] = tile_sprite.serialize()
        return s_dict

    @classmethod
    def restore(cls, s_dict, parent):
        self = cls(s_dict['nid'], parent)
        self.visible = s_dict['visible']
        for str_coord, terrain_nid in s_dict['terrain_grid'].items():
            coord = tuple(int(_) for _ in str_coord.split(','))
            self.terrain_grid[coord] = terrain_nid
        for str_coord, data in s_dict['sprite_grid'].items():
            coord = tuple(int(_) for _ in str_coord.split(','))
            self.sprite_grid[coord] = TileSprite.deserialize(*data, self)
        return self

class TileSprite(Prefab):
    def __init__(self, tileset_nid, tileset_position, parent):
        self.parent = parent
        self.tileset_nid = tileset_nid
        self.tileset_position = tileset_position

    def save(self):
        return self.tileset_nid, self.tileset_position

    @classmethod
    def restore(cls, tileset_nid, tileset_position, parent):
        new_tile_sprite = cls(tileset_nid, tuple(tileset_position), parent)
        return new_tile_sprite

class TileSetCatalog(ManifestCatalog):
    manifest = 'tileset.json'
    title = 'tilesets'

    def load(self, loc):
        tileset_dict = self.read_manifest(os.path.join(loc, self.manifest))
        for s_dict in tileset_dict:
            new_tileset = TileSet.restore(s_dict)
            new_tileset.set_full_path(os.path.join(loc, new_tileset.nid))
            self.append(new_tileset)

class TileMapCatalog(ManifestCatalog):
    manifest = 'tilemap.json'
    title = 'tilemaps'

    def load(self, loc):
        tilemap_dict = self.read_manifest(os.path.join(loc, self.manifest))
        for s_dict in tilemap_dict:
            new_tilemap = TileMapPrefab.restore(s_dict)
            self.append(new_tilemap)

    def save(self, loc):
        # No need to finagle with full paths
        # Because TileMaps are don't have any connection to any actual file.
        # They are all references to TileSets
        self.dump(loc)
