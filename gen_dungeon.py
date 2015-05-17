# -*- coding: utf-8 -*-
__author__ = 'Tachi'
from xml.dom import minidom
import MT


class Direction(object):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

    def getOppositeDirection(self, dir):
        if dir == Direction.UP:
            return Direction.DOWN
        elif dir == Direction.RIGHT:
            return Direction.LEFT
        elif dir == Direction.DOWN:
            return Direction.UP
        elif dir == Direction.LEFT:
            return Direction.RIGHT
        else:
            return -1


class RandomDirection(object):
    directions = [0, 0, 0, 0]

    def __init__(self):
        self.directions = [0, 0, 0, 0]

    def getDirection(self, MT):
        visited = True
        direction = 0
        while visited:
            direction = MT.extract_number() & 3
            visited = self.directions[direction]
        self.directions[direction] = 1
        return direction


class Position(object):
    x = 0
    y = 0

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def getBias(self, dir):
        if dir == Direction.UP:
            return Position(0, 1)
        elif dir == Direction.RIGHT:
            return Position(1, 0)
        elif dir == Direction.DOWN:
            return Position(0, -1)
        elif dir == Direction.LEFT:
            return Position(-1, 0)
        else:
            return Position(0, 0)

    def getBiasedPosition(self, direction):
        bias = self.getBias(direction)
        return Position(self.x + bias.x, self.y + bias.y)


class pseudoImages(object):
    # LEFT = 3  DOWN = 2  RIGHT = 1  UP = 0
    pseudo = {
        0x0000: ["  ",
                 "  "],
        0x1000: ["╗ ",
                 "╝ "],
        0x0100: ["  ",
                 "╔╗"],
        0x1100: ["═╗",
                 "╗║"],
        0x0010: [" ╔",
                 " ╚"],
        0x1010: ["══",
                 "══"],
        0x0110: ["╔═",
                 "║╔"],
        0x1110: ["══",
                 "╗╔"],
        0x0001: ["╚╝",
                 "  "],
        0x1001: ["╝║",
                 "═╝"],
        0x0101: ["║║",
                 "║║"],
        0x1101: ["╝║",
                 "╗║"],
        0x0011: ["║╚",
                 "╚═"],
        0x1011: ["╝╚",
                 "══"],
        0x0111: ["║╚",
                 "║╔"],
        0x1111: ["╝╚",
                 "╗╔"],
    }

    def getPseudoImage(self, directions):
        code = 0
        for d in range(4):
            if directions[d] > 0:
                code |= 1 << d*4
        return self.pseudo[code]

class maze_room_internal(object):
    directions = [0, 0, 0, 0]
    isOnCriticalPath = False
    isVisited = 0
    isReserved = False

    def __init__(self):
        self.directions = [0, 0, 0, 0]

    def isOccupied(self):
        if self.isVisited or self.isReserved:
            return True
        return False

    def Visited(self, cnt):
        self.isVisited = cnt

    def GetPassageType(self, direction):
        return self.directions[direction]


class maze_move(object):
    pos_from = Position(0, 0)
    pos_to = Position(0, 0)
    direction = -1

    def __init__(self, pos_from, pos_to, direction):
        self.pos_from = Position(0, 0)
        self.pos_to = Position(0, 0)
        self.pos_from.x, self.pos_from.y = pos_from.x, pos_from.y
        self.pos_to.x, self.pos_to.y = pos_to.x, pos_to.y
        self.direction = direction


class MazeGenerator(object):
    width = 0
    height = 0
    start_direction = 0
    start_pos = Position(0, 0)
    current_pos = Position(0, 0)
    end_pos = Position(0, 0)
    counter = 0
    isCriticalPathGenerated = False
    isSubPathGenerated = False
    rooms = []  # [width][height] array of maze_room_internal
    CriticalPath = []  # list of maze_move
    _CritPathMinResult = 0
    _CritPathMaxResult = 0

    def __init__(self):
        self.start_pos = Position(0, 0)
        self.current_pos = Position(0, 0)
        self.end_pos = Position(0, 0)
        self.rooms = []
        self.CriticalPath = []

    def print_maze(self):
        """ debug """
        print "maze gen"
        print "  000102030405060708"
        for y in range(self.height-1,-1,-1):
            row = "{0:02} ".format(y)
            for x in range(self.width):
                if self.start_pos.x == x and self.start_pos.y == y:
                    row += "S "
                elif self.rooms[x][y].isVisited > 0:
                    row += "X "
                else:
                    row += "  "
            print row

    def setSize(self, width, height):
        self.width = width
        self.height = height
        self.rooms = []
        self.CriticalPath = []
        for h in range(self.width):
            row = []
            for w in range(self.height):
                row.append(maze_room_internal())
            self.rooms.append(row)
        self.end_pos = Position(width-1, height-1)

    def generateCriticalPath(self, MT, CritPathMin, CritPathMax):
        if self.isCriticalPathGenerated:
            return True
        else:
            if CritPathMin > CritPathMax:
                CritPathMin, CritPathMax = CritPathMax, CritPathMin
            self._CritPathMinResult = 0
            self._CritPathMaxResult = 0
            self.isCriticalPathGenerated = self._generateCriticalPathRecursive(0, CritPathMin, CritPathMax, -1, MT)
            return self.isCriticalPathGenerated

    def generateSubPath(self, MT, coverageFactor, branchProbability):
        if self.isCriticalPathGenerated:
            if self.isSubPathGenerated:
                return True
            else:
                if coverageFactor > 100:
                    coverageFactor = 100
                if branchProbability > 100:
                    branchProbability = 100
                free_rooms = 0
                for y in range(self.height):
                    for x in range(self.width):
                        if not self.rooms[x][y].isOccupied():
                            free_rooms += 1
                coverage = int(free_rooms * coverageFactor / 100)
                to_vector = []
                if len(self.CriticalPath) > 0:
                    for move in self.CriticalPath:
                        to_vector.append(move.pos_to)
                    to_vector = to_vector[:-1]
                to_vector = self._generateSubPath_sub_1(to_vector)
                temp_vector = []
                if coverage > 0:
                    for i in range(coverage):
                        vect = to_vector
                        if len(temp_vector) == 0:
                            if len(to_vector) == 0:
                                break
                            flag = True
                        else:
                            if len(to_vector) == 0:
                                flag = False
                                vect = temp_vector
                            else:
                                rnd = MT.extract_number() % 100
                                flag = branchProbability >= rnd
                                if not flag:
                                    vect = temp_vector
                        rand_idx = MT.extract_number() % len(vect)
                        pos = vect[rand_idx]
                        room = self.getRoom(pos)
                        directions = [0, 0, 0, 0]
                        random_dir = -1
                        direction = 0
                        while True:
                            random_dir = self._generateSubPath_random_dir(MT, directions)
                            if room.GetPassageType(random_dir) == 0:
                                if self.isRoomInDirectionFree(pos, random_dir):
                                    break
                            direction += 1
                            if direction >= 4:
                                break
                        if direction >= 4:
                            temp_vector = self._generateSubPath_sub_3(temp_vector, to_vector)
                            to_vector = self._generateSubPath_sub_1(to_vector)
                            continue
                        biased_pos = pos.getBiasedPosition(random_dir)
                        room2 = self.getRoom(biased_pos)
                        room.directions[random_dir] = 2
                        room2.directions[Direction().getOppositeDirection(random_dir)] = 1
                        self.counter += 1
                        room2.Visited(self.counter)
                        temp_vector.append(biased_pos)
                        if not flag:
                            temp_vector = temp_vector[:rand_idx] + temp_vector[rand_idx+1:]
                            to_vector.append(pos)
                        temp_vector = self._generateSubPath_sub_3(temp_vector, to_vector)
                        to_vector = self._generateSubPath_sub_1(to_vector)
                    self.isSubPathGenerated = True
                    print "sub"
                    self.print_maze()
                    return True
                else:
                    return True
        else:
            return False

    def _generateSubPath_random_dir(self, MT, directions):
        for direction in range(4):
            if directions[direction] == 0:
                while True:
                    random_dir = MT.extract_number() & 3
                    if directions[random_dir] == 0:
                        directions[random_dir] = 1
                        return random_dir
        return -1

    def _generateSubPath_sub_1(self, to_vector):
        temp_vector = []
        for to in to_vector:
            if self._generateSubPath_sub_2(to):
                temp_vector.append(to)
        return temp_vector

    def _generateSubPath_sub_3(self, temp_vector, to_vector):
        temp_vector2 = []
        for pos in temp_vector:
            if self._generateSubPath_sub_2(pos):
                room = self.getRoom(pos)
                vect = temp_vector2
                for direction in range(4):
                    if room.directions[direction] == 2:
                        vect = to_vector
                        break
                vect.append(pos)
        return temp_vector2

    def _generateSubPath_sub_2(self, pos):
        room = self.getRoom(pos)
        if room:
            for direction in range(4):
                if room.GetPassageType(direction) == 0:
                    if self.isRoomInDirectionFree(pos, direction):
                        return True
            return False
        else:
            return False

    def _generateCriticalPathRecursive(self, CritPathPos, CritPathMin, CritPathMax, direction, MT):
        directions = [0, 0, 0, 0]
        self._CritPathMaxResult += 1
        if self._CritPathMaxResult <= 10 * CritPathMax:
            if CritPathMin <= CritPathPos <= CritPathMax and \
                    self.isRoomInDirectionFree(self.current_pos, self.start_direction):
                self.start_pos.x, self.start_pos.y = self.current_pos.x, self.current_pos.y
                for move in self.CriticalPath:
                    move.pos_from.x, move.pos_to.x = move.pos_to.x, move.pos_from.x
                    move.pos_from.y, move.pos_to.y = move.pos_to.y, move.pos_from.y
                    move.direction = Direction().getOppositeDirection(move.direction)
                CriticalPath = []
                while len(self.CriticalPath) > 0:
                    CriticalPath.append(self.CriticalPath[-1])
                    self.CriticalPath = self.CriticalPath[:-1]
                self.CriticalPath = CriticalPath
                self.print_maze()
                return True
            else:
                CritPathPos += 1
                count = 0
                if CritPathPos <= CritPathMax:
                    if direction != -1:
                        direction = Direction().getOppositeDirection(direction)
                    for i_dir in range(4):
                        if i_dir == direction:
                            directions[i_dir] = 0
                        else:
                            next_pos = self.current_pos.getBiasedPosition(i_dir)
                            directions[i_dir] = self._sub(next_pos)
                            count += directions[i_dir]
                    while count > 0:
                        rnd = MT.extract_number() % count + 1
                        cnt2 = 0
                        i_dir = 0
                        for i_dir in range(4):
                            cnt2 += directions[i_dir]
                            if cnt2 >= rnd:
                                break
                        count -= directions[i_dir]
                        directions[i_dir] = 0
                        #moves_count = len(self.CriticalPath)
                        if self._make_move(i_dir):
                            if self._generateCriticalPathRecursive(CritPathPos, CritPathMin, CritPathMax, i_dir, MT):
                                return True
                            self._undo_move()
                else:
                    return False
        else:
            return False

    def _sub(self, pos):
        if self.getRoom(pos) != 0:
            cnt = 1
            for i_dir in range(4):
                room = self.getRoom(pos.getBiasedPosition(i_dir))
                if room != 0:
                    if not room.isOccupied():
                        cnt += 1
            return cnt
        else:
            return 0

    def _make_move(self, direction):
        if self.isRoomInDirectionFree(self.current_pos, direction):
            next_pos = self.current_pos.getBiasedPosition(direction)
            current_room = self.getRoom(self.current_pos)
            next_room = self.getRoom(next_pos)
            move = maze_move(self.current_pos, next_pos, direction)
            self.CriticalPath.append(move)
            self.counter += 1
            next_room.Visited(self.counter)
            next_room.isOnCriticalPath = True
            current_room.directions[direction] = 1
            next_room.directions[Direction().getOppositeDirection(direction)] = 2
            self.current_pos = next_pos
            return True
        return False

    def _undo_move(self, count=1):
        for i in range(count):
            move = self.CriticalPath[-1]
            self.CriticalPath = self.CriticalPath[:-1]
            current_room = self.getRoom(move.pos_from)
            next_room = self.getRoom(move.pos_to)
            opposite_direction = Direction().getOppositeDirection(move.direction)
            if next_room.isVisited:
                current_room.directions[move.direction] = 0
                next_room.directions[opposite_direction] = 0
                next_room.isVisited = 0
                next_room.isOnCriticalPath = False
                self.counter -= 1
            self.current_pos = self.current_pos.getBiasedPosition(opposite_direction)

    def getRoom(self, pos):
        if 0 <= pos.x < self.width and 0 <= pos.y < self.height:
            return self.rooms[pos.x][pos.y]
        else:
            return 0

    def getStartPosition(self):
        return self.start_pos

    def getCriticalPath(self):
        return self.CriticalPath

    def setStartDir(self, dir):
        self.start_direction = dir

    def getStartDir(self):
        return self.start_direction

    def isFree(self, pos):
        return self.rooms[pos.x][pos.y].isOccupied() is False

    def isRoomInDirectionFree(self, pos, direction):
        dir_pos = pos.getBiasedPosition(direction)
        if 0 <= dir_pos.x < self.width and 0 <= dir_pos.y < self.height:
            return not self.rooms[dir_pos.x][dir_pos.y].isOccupied()
        else:
            return False

    def markReservedPosition(self, pos):
        room = self.rooms[pos.x][pos.y]
        if not room.isVisited:
            room.isReserved = True

    def setPathPosition(self, pos):
        if self.width > pos.x and self.height > pos.y:
            for y in range(self.height):
                for x in range(self.width):
                    room = self.rooms[x][y]
                    room.directions = [0, 0, 0, 0]
                    room.isVisited = False
            self.CriticalPath = []
            self.start_pos = Position(0, 0)
            self.current_pos = Position(0, 0)
            self.end_pos.x, self.end_pos.y = pos.x, pos.y
            self.current_pos.x, self.current_pos.y = pos.x, pos.y
            self.counter = 1
            room = self.rooms[pos.x][pos.y]
            room.isVisited = self.counter
            room.isOnCriticalPath = True


class SDungeonFloor(object):
    width = 1
    height = 1
    crit_path_min = 1
    crit_path_max = 1
    is_custom_floor = False
    HasBossRoom = False
    branchProbability = 0
    coverageFactor = 0


class DungeonClass(object):
    name = ""
    base_seed = 0
    floors = []

    def __init__(self):
        self.floors = []

    def getFloorDesc(self, n):
        return self.floors[n]


def load_dungeon_class(dungeon_class):
    dungeon_xmls = ["dungeondb2.xml", "dungeondb.xml", "dungeon_ruin.xml"]
    for xml_name in dungeon_xmls:
        dom = minidom.parse(xml_name)
        dungeons = dom.getElementsByTagName('dungeon')
        for dungeon in dungeons:
            if dungeon.getAttribute('name').lower() == dungeon_class:
                s_dungeon_class = DungeonClass()
                s_dungeon_class.name = dungeon_class
                s_dungeon_class.base_seed = int(dungeon.getAttribute('baseseed'))
                floors = dungeon.getElementsByTagName('floordesc')
                for floor in floors:
                    floor_desc = SDungeonFloor()
                    floor_desc.is_custom_floor = floor.hasAttribute('custom')
                    floor_desc.width = int(floor.getAttribute('width'))
                    floor_desc.height = int(floor.getAttribute('height'))
                    floor_desc.crit_path_min = int(floor.getAttribute('critpathmin'))
                    floor_desc.crit_path_max = int(floor.getAttribute('critpathmax'))
                    floor_desc.HasBossRoom = len(floor.getElementsByTagName('boss')) > 0
                    floor_desc.branchProbability = int(floor.getAttribute('branch'))
                    floor_desc.coverageFactor = int(floor.getAttribute('coverage'))
                    s_dungeon_class.floors.append(floor_desc)
                return s_dungeon_class
    return None


class RoomTrait(object):
    neighbor = [None, None, None, None]
    link = [0, 0, 0, 0]
    doorType = [0, 0, 0, 0]
    roomType = 0
    shapeType = 0
    shapeRotationCount = 0

    def __init__(self):
        self.neighbor = [None, None, None, None]
        self.link = [0, 0, 0, 0]
        self.doorType = [0, 0, 0, 0]

    def setNeighbor(self, direction, room):
        self.neighbor[direction] = room

    def isLinked(self, direction):
        if direction > 3:
            raise
        return self.link[direction] != 0

    def getDoorType(self, direction):
        if direction > 3:
            raise
        return self.doorType[direction]

    def Link(self, direction, link_type):
        if direction > 3:
            raise
        self.link[direction] = link_type
        if self.neighbor[direction] is not None:
            opposite_direction = Direction().getOppositeDirection(direction)
            if link_type == 1:
                self.neighbor[direction].link[opposite_direction] = 2
            elif link_type == 2:
                self.neighbor[direction].link[opposite_direction] = 1
            else:
                self.neighbor[direction].link[opposite_direction] = 0

    def setDoorType(self, direction, door_type):
        if direction > 3:
            raise
        self.doorType[direction] = door_type
        opposite_direction = Direction().getOppositeDirection(direction)
        room = self.neighbor[direction]
        if room is not None:
            room.doorType[opposite_direction] = door_type


class DungeonFloorStructure(object):
    dungeon_structure = None
    prev_floor_structure = None
    next_floor_structure = None
    maze_generator = MazeGenerator()
    rooms = []
    width = 1
    height = 1
    HasBossRoom = False
    IsLastFloor = True
    pos = Position(0, 0)
    start_pos = Position(0, 0)
    start_direction = Direction.DOWN

    def __init__(self, dungeon_structure, floor_desc, IsLastFloor, prev):
        self.pos = Position(0, 0)
        self.start_pos = Position(0, 0)
        self.prev_floor_structure = prev
        self.dungeon_structure = dungeon_structure
        self.HasBossRoom = floor_desc.HasBossRoom
        self.branchProbability = floor_desc.branchProbability
        self.coverageFactor = floor_desc.coverageFactor
        self.IsLastFloor = IsLastFloor
        self._calculate_size(floor_desc)
        self._init_roomtraits()
        self.maze_generator = MazeGenerator()
        self._generate_maze(floor_desc)

    def _calculate_size(self, floor_desc):
        w = floor_desc.width
        h = floor_desc.height
        if floor_desc.width < 6:
            w = 6
        elif floor_desc.width > 18:
            w = 18
        if floor_desc.height < 6:
            h = 6
        elif floor_desc.height > 18:
            h = 18
        rnd = self.dungeon_structure.MT_maze.extract_number()
        self.width = w - rnd % int(w/5.0)
        rnd = self.dungeon_structure.MT_maze.extract_number()
        self.height = h - rnd % int(h/5.0)

    def _init_roomtraits(self):
        self.rooms = []
        for h in range(self.width):
            row = []
            for w in range(self.height):
                row.append(RoomTrait())
            self.rooms.append(row)
        for y in range(self.height):
            for x in range(self.width):
                for direction in range(4):
                    biased_pos = Position(x, y).getBiasedPosition(direction)
                    if biased_pos.x >= 0 and biased_pos.y >= 0:
                        if biased_pos.x < self.width and biased_pos.y < self.height:
                            self.rooms[x][y].setNeighbor(direction, self.rooms[biased_pos.x][biased_pos.y])

    def getRoom(self, pos):
        if pos.x < 0 or pos.y < 0 or pos.x >= self.width or pos.y >= self.height:
            raise
        return self.rooms[pos.x][pos.y]

    def _set_traits(self, pos, direction, door_type):
        biased_pos = pos.getBiasedPosition(direction)
        if biased_pos.x >= 0 and biased_pos.y >= 0:
            if biased_pos.x < self.width and biased_pos.y < self.height:
                if not self.maze_generator.isFree(biased_pos):
                    return False
                self.maze_generator.markReservedPosition(biased_pos)
        room = self.getRoom(pos)
        if room.isLinked(direction):
            raise
        if room.getDoorType(direction) != 0:
            raise
        if door_type == 3100:
            link_type = 2
        elif door_type == 3000:
            link_type = 1
        else:
            raise
        room.Link(direction, link_type)
        room.setDoorType(direction, door_type)
        return True

    def _generate_maze(self, floor_desc):
        crit_path_min = floor_desc.crit_path_min
        crit_path_max = floor_desc.crit_path_max
        if crit_path_min < 1:
            crit_path_min = 1
        if crit_path_max < 1:
            crit_path_max = 1
        if crit_path_min > crit_path_max:
            crit_path_min, crit_path_max = crit_path_max, crit_path_min
        self._create_critical_path(crit_path_min, crit_path_max)
        self._create_sub_path(self.coverageFactor, self.branchProbability)
        self._update_path_position()

    def _create_critical_path(self, crit_path_min, crit_path_max):
        while True:
            self.maze_generator.setSize(self.width, self.height)
            self._set_random_path_position()
            if self.maze_generator.generateCriticalPath(self.dungeon_structure.MT_maze, crit_path_min, crit_path_max):
                self.start_pos = self.maze_generator.getStartPosition()
                if self._set_traits(self.start_pos, self.maze_generator.getStartDir(), 3000):
                    break
            self.maze_generator = MazeGenerator()
            self._init_roomtraits()
        return self.maze_generator.getCriticalPath()

    def _create_sub_path(self, coverageFactor, branchProbability):
        self.maze_generator.generateSubPath(self.dungeon_structure.MT_maze, coverageFactor, branchProbability)
        return self._create_sub_path_recursive(self.start_pos)

    def _create_sub_path_recursive(self, pos):
        room = self.getRoom(pos)
        maze_room = self.maze_generator.getRoom(pos)
        room.roomType = 1
        for direction in range(4):
            if maze_room.GetPassageType(direction) == 2:
                biased_pos = pos.getBiasedPosition(direction)
                if room is not None:
                    room.Link(direction, 2)
                self._create_sub_path_recursive(biased_pos)

    def _update_path_position(self):
        pass  # TODO _update_path_position

    def _set_random_path_position(self):
        if self.prev_floor_structure is not None:
            start_direction = Direction().getOppositeDirection(self.prev_floor_structure.start_direction)
        else:
            start_direction = Direction.DOWN
        self.maze_generator.setStartDir(start_direction)
        mt = self.dungeon_structure.MT_maze
        if self.HasBossRoom:
            if "largebossroom" in self.dungeon_structure.option:  # <option largebossroom="true" />
                while True:
                    self.pos.x = mt.extract_number() % (self.width - 2) + 1
                    self.pos.y = mt.extract_number() % (self.height - 3) + 1
                    if self.maze_generator.isFree(self.pos):
                        if self.maze_generator.isFree(Position(self.pos.x - 1, self.pos.y)):
                            if self.maze_generator.isFree(Position(self.pos.x + 1, self.pos.y)):
                                if self.maze_generator.isFree(Position(self.pos.x, self.pos.y + 1)):
                                    if self.maze_generator.isFree(Position(self.pos.x - 1, self.pos.y + 1)):
                                        if self.maze_generator.isFree(Position(self.pos.x + 1, self.pos.y + 1)):
                                            if self.maze_generator.isFree(Position(self.pos.x, self.pos.y + 2)):
                                                if self.maze_generator.isFree(Position(self.pos.x - 1, self.pos.y + 2)):
                                                    if self.maze_generator.isFree(Position(self.pos.x + 1, self.pos.y + 2)):
                                                        break
                self.maze_generator.markReservedPosition(Position(self.pos.x - 1, self.pos.y))
                self.maze_generator.markReservedPosition(Position(self.pos.x + 1, self.pos.y))
                self.maze_generator.markReservedPosition(Position(self.pos.x, self.pos.y + 1))
                self.maze_generator.markReservedPosition(Position(self.pos.x - 1, self.pos.y + 1))
                self.maze_generator.markReservedPosition(Position(self.pos.x + 1, self.pos.y + 1))
                self.maze_generator.markReservedPosition(Position(self.pos.x, self.pos.y + 2))
                self.maze_generator.markReservedPosition(Position(self.pos.x - 1, self.pos.y + 2))
                self.maze_generator.markReservedPosition(Position(self.pos.x + 1, self.pos.y + 2))
            else:
                while True:
                    self.pos.x = mt.extract_number() % (self.width - 2) + 1
                    self.pos.y = mt.extract_number() % (self.height - 3) + 1
                    if self.maze_generator.isFree(self.pos):
                        if self.maze_generator.isFree(Position(self.pos.x - 1, self.pos.y)):
                            if self.maze_generator.isFree(Position(self.pos.x + 1, self.pos.y)):
                                if self.maze_generator.isFree(Position(self.pos.x, self.pos.y + 1)):
                                    if self.maze_generator.isFree(Position(self.pos.x - 1, self.pos.y + 1)):
                                        if self.maze_generator.isFree(Position(self.pos.x + 1, self.pos.y + 1)):
                                            if self.maze_generator.isFree(Position(self.pos.x, self.pos.y + 2)):
                                                break
                self.maze_generator.markReservedPosition(Position(self.pos.x - 1, self.pos.y))
                self.maze_generator.markReservedPosition(Position(self.pos.x + 1, self.pos.y))
                self.maze_generator.markReservedPosition(Position(self.pos.x, self.pos.y + 1))
                self.maze_generator.markReservedPosition(Position(self.pos.x - 1, self.pos.y + 1))
                self.maze_generator.markReservedPosition(Position(self.pos.x + 1, self.pos.y + 1))
                self.maze_generator.markReservedPosition(Position(self.pos.x, self.pos.y + 2))
        else:
            free = False
            while not free:
                self.pos.x = mt.extract_number() % self.width
                self.pos.y = mt.extract_number() % self.height
                free = self.maze_generator.isFree(self.pos)
        if not self.IsLastFloor and not self.HasBossRoom:
            rnd_dir = RandomDirection()
            while True:
                direction = rnd_dir.getDirection(mt)
                if self._set_traits(self.pos, direction, 3100):
                    self.start_direction = direction
                    break
            # core::ICommonAPI::stdapi_SetNPCDirection();  // Server stuff?
        self.maze_generator.setPathPosition(self.pos)


class DungeonStructure(object):
    item_dropped = 0
    seed = 0
    floorplan = 0
    option = ""
    MT_maze = None
    MT_puzzle = None
    floors = []

    def __init__(self, dungeon_class, instance_id, item_id, option, seed, floorplan):
        s_dungeon_class = load_dungeon_class(dungeon_class.lower())
        self.seed = seed
        self.item_id = item_id
        self.floorplan = floorplan
        self.option = option.lower()
        # init random generators
        self.MT_maze = MT.MersenneTwister(s_dungeon_class.base_seed + item_id + floorplan)
        self.MT_puzzle = MT.MersenneTwister(seed)
        # init floors
        self.floors = []
        prev = None
        for i in range(len(s_dungeon_class.floors)):
            last_floor = i == len(s_dungeon_class.floors) - 1
            floor = DungeonFloorStructure(self, s_dungeon_class.getFloorDesc(i), last_floor, prev)
            prev = floor
            self.floors.append(floor)



def print_maze(n):
    """ debug """
    floor = dungeon_structure.floors[n]
    rooms = floor.maze_generator.rooms
    print "\nmaze gen"
    print "  000102030405060708"
    for y in range(floor.height-1,-1,-1):
        row = [("{0:02}".format(y), "  ")]
        for x in range(floor.width):
            pseudoImage = pseudoImages().getPseudoImage(rooms[x][y].directions)
            row.append(pseudoImage)
        str1, str2 = zip(*row)
        print "".join(str1)
        print "".join(str2)


rooms = [
    [[1,0], [1,1], [4,1], [3,2], [4,2], [0,0], [1,2], [2,2], [3,1], [3,4], [3,5]],
]
# example 1
#dungeon_structure = DungeonStructure("tircho_alby_dungeon", 1, 2000, "", 326918577, 0)
# example 2
#dungeon_structure = DungeonStructure("tircho_alby_dungeon", 1, 60005, "", 327494389, 0)
# example 3
dungeon_structure = DungeonStructure("dunbarton_rabbie_dungeon", 1, 2000, "", 370545889, 0)


maze_gen = dungeon_structure.floors[0].maze_generator
print "finish"
#maze_gen.print_maze()
for i in range(len(dungeon_structure.floors)):
    print_maze(i)



