
import os
import sys
from pydantic import BaseModel, Field, model_validator, field_validator
from dotenv import load_dotenv
from typing import Any, Generator, cast
import random
import time
from collections import deque


class CMazeParams(BaseModel):
    """ Validate and store maze parameters """
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    entry: tuple[int, int]
    exit: tuple[int, int]
    output_file: str = Field(min_length=0, default="")
    perfect: bool = True
    seed: int | None = None
    insert_42: bool = True
    w_cell_size: int = Field(ge=2, default=25)
    w_wall_thickness: int = Field(ge=1, default=4)
    colors: dict[str, int] = {"wall": 0x959696,
                              "entry": 0xFF27C8F5,
                              "exit": 0xFF38F527,
                              "pattern": 0xFFFFFFFF
                              }
    # Probability to del deadend in procent (0-100%)
    # Only applicable to non-perfect maze
    probability_to_del_dead_end: int | float = Field(ge=0, le=100, default=99)

    @field_validator("entry", "exit", mode="before")
    @classmethod
    def parse_tuple(cls, v: Any) -> tuple[int, int] | Any:
        if isinstance(v, str):
            try:
                x, y = v.split(",")
                return int(x), int(y)
            except ValueError:
                raise ValueError("Expected format: 'x,y'")
        return v

    @model_validator(mode='after')
    def params_validator(self) -> 'CMazeParams':
        # Check:  Entry and exit are different
        if self.entry == self.exit:
            raise ValueError('Error: Entry and exit must be different. \n')
        # Check:  Entry and exit in maze
        x, y = self.entry
        if (x >= self.width) or (y >= self.height):
            raise ValueError('Error: Entry must be inside maze '
                             f'(Entry(x={x},y={y}) Width={self.width} '
                             f'Height={self.height})! \n')
        x, y = self.exit
        if (x >= self.width) or (y >= self.height):
            raise ValueError('Error: Exit must be inside maze '
                             f'(Exit(x={x},y={y}) Width={self.width} '
                             f'Height={self.height})! \n')
        return self

    def print(self) -> dict[str, Any]:
        res_ = {"width": self.width,
                "height": self.height,
                "entry": self.entry,
                "exit": self.exit,
                "output_file": self.output_file,
                "perfect": self.perfect}
        if not (self.seed is None):
            res_["seed"] = self.seed
        if not (self.insert_42):
            res_["insert_42"] = self.insert_42
        return res_

    @staticmethod
    def fm_read_config(file_name: str | None = None) -> bool:
        """
        Read data from config file in .env format
        Return True if reading was successful
        """
        if (not (file_name is None)) and len(file_name) > 0:
            if not (os.path.isfile(file_name)):
                print(f'ERROR: Config file "{file_name}" '
                      'is required but not found !', file=sys.stderr)
            return False
        try:
            load_dotenv(file_name, override=False)
        except Exception as e:
            print(f'ERROR: Can`t read config file "{file_name}":\n',
                  e, file=sys.stderr)
            return False
        return True

    @staticmethod
    def fm_check_param(params: dict[str, int]) -> bool:
        """
        Check that param from params is set and check minimul lenght of value
        """
        for p_ in params:
            val = os.getenv(p_)
            if val is None:
                print(f"Error: The {p_} parameters is not set. "
                      "Check parameters file!", file=sys.stderr)
                return False
            if len(val) < params[p_]:
                print(f"Error: Wrong value of parameter {p_}={val}. "
                      "Check parameters file!", file=sys.stderr)
        return True

    @classmethod
    def create_param_from_file(cls,
                               file_name: str | None = None) -> 'CMazeParams':
        if not (file_name is None):
            cls.fm_read_config(file_name)
            if not cls.fm_check_param({"WIDTH": 1,
                                       "HEIGHT": 1}):
                raise ValueError("Parameters WIDTH or HEIGHT not set")
        insert_42 = (not (os.getenv("INSERT_42") == 'False'))
        try:
            val_ = os.getenv("W_CELL_SIZE")
            if val_ is None:
                w_cell_size = 25
            else:
                w_cell_size = int(val_)
        except Exception:
            w_cell_size = 25
        return CMazeParams(width=cast(int, os.getenv("WIDTH")),
                           height=cast(int, os.getenv("HEIGHT")),
                           entry=cast(tuple[int, int],
                                      os.getenv("ENTRY")),
                           exit=cast(tuple[int, int],
                                     os.getenv("EXIT")),
                           output_file=cast(str,
                                            os.getenv("OUTPUT_FILE")),
                           perfect=cast(bool, os.getenv("PERFECT")),
                           seed=cast(int, os.getenv("SEED")),
                           insert_42=insert_42,
                           w_cell_size=w_cell_size
                           )


class MazeGenerator():
    """
    Value in cell:
        1 - top wall (North),
        2 - right (East), 3 - top + right
        f - pattern

    """
    p_42: list[list[int]] = [[15, 0, 0, 0, 15, 15, 15],
                             [15, 0, 0, 0, 0, 0, 15],
                             [15, 15, 15, 0, 15, 15, 15],
                             [0, 0, 15, 0, 15, 0, 0],
                             [0, 0, 15, 0, 15, 15, 15]]

    @classmethod
    def place_42(cls, maze: list[list[int]],
                 in_: tuple[int, int], out_: tuple[int, int]) -> bool:
        """ Trying to place the "42" pattern in the maze. """

        def check_palace(x: int, y: int) -> bool:
            # exit and entry on one side of pattern
            if (
                ((y > in_[1]) and (y > out_[1]))
                or ((x > in_[0]) and (x > out_[0]))
                or ((in_[1] >= y + s_42_h) and (out_[1] >= y + s_42_h))
                or ((in_[0] >= x + s_42_w) and (out_[1] >= x + s_42_w))
               ):
                return True

            # check that exit and entry not in pattern
            if (
                ((y > in_[1]) or (in_[1] >= y + s_42_h)
                 or (x > in_[0]) or (in_[0] >= x + s_42_w))
                and ((y > out_[1]) or (out_[1] >= y + s_42_h)
                     or (x > out_[0]) or (out_[0] >= x + s_42_w))
               ):
                return (
                    (s_42_h < len(maze))
                    or ((x > in_[0]) and (x > out_[0]))
                    or ((x < in_[0]) and (x < out_[0]))
                    )

            # There could be a check for case when exit or entry in pattern
            return False

        s_42_h: int = len(cls.p_42)
        if s_42_h > len(maze):
            return False

        s_42_w: int = 0
        if s_42_h > 0:
            s_42_w = len(cls.p_42[0])
        else:
            return False

        if s_42_w > len(maze[0]):
            return False

        # Trying to place in center

        p_42_x: int = int((len(maze[0]) - s_42_w) / 2)
        p_42_y: int = int((len(maze) - s_42_h) / 2)

        # print(f"42 place: x={p_42_x}, y={p_42_y}")

        if not check_palace(p_42_x, p_42_y):
            return False

        for y in range(0, s_42_h):
            for x in range(0, s_42_w):
                if cls.p_42[y][x] == 15:
                    maze[y + p_42_y][x + p_42_x] = 15

        return True

    @classmethod
    def check_point_in_path(cls, path: list[list[int]], x: int, y: int) -> int:
        for i in range(0, len(path)):
            if (x == path[i][0]) and (y == path[i][1]):
                return i + 1
        return 0

    @classmethod
    def clear_tmp_data(cls, maze: list[list[int]]) -> list[list[int]]:
        for y in range(0, len(maze)):
            for x in range(0, len(maze[0])):
                if maze[y][x] > 0xf:
                    maze[y][x] = maze[y][x] & 0xf
        return maze

    @classmethod
    def find_path_BFS(cls, maze: list[list[int]],
                      mzParam: CMazeParams) -> list[list[int]]:
        height = len(maze)
        width = len(maze[0])
        start = mzParam.entry
        end = mzParam.exit

        queue = deque([start])
        visited = set([start])
        parent: dict[tuple[int, int], tuple[int, int]] = {}

        while queue:
            x, y = queue.popleft()

            if (x, y) == end:
                # reconstruct path
                path = []
                while (x, y) != start:
                    path.append([x, y, 0])
                    x, y = parent[(x, y)]
                path.append([start[0], start[1], 0])
                path.reverse()
                return path

            cell = maze[y][x] & 3
            if (x == 0) or (maze[y][x - 1] & 2):
                cell = cell | 8
            if (y >= (height-1)) or (maze[y+1][x] & 1):
                cell = cell | 4
            if (y == 0):
                cell = cell | 1
            if (x >= (width-1)):
                cell = cell | 2

            # ----- TOP -----
            if not (cell & 1):  # no top wall
                nx, ny = x, y - 1
                if 0 <= ny < height and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    parent[(nx, ny)] = (x, y)
                    queue.append((nx, ny))

            # ----- RIGHT -----
            if not (cell & 2):  # no right wall
                nx, ny = x + 1, y
                if 0 <= nx < width and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    parent[(nx, ny)] = (x, y)
                    queue.append((nx, ny))

            # ----- BOTTOM -----
            if not (cell & 4):  # no bottom wall
                nx, ny = x, y + 1
                if 0 <= ny < height and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    parent[(nx, ny)] = (x, y)
                    queue.append((nx, ny))

            # ----- LEFT -----
            if not (cell & 8):  # no left wall
                nx, ny = x - 1, y
                if 0 <= nx < width and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    parent[(nx, ny)] = (x, y)
                    queue.append((nx, ny))
        return []

    @classmethod
    def find_path_DFS(cls, maze: list[list[int]],
                      mzParam: CMazeParams,
                      best_path:  list[list[int]] = []) -> list[list[int]]:
        """ Trying to find paths from entrance to exit.
            Go at first in directions to the exit

        m_path [x,y,q] - current path
        there q - walls directions we could go
            1 - (xxx1) Top wall (North),
            2 - (xx1x) Right (East),
            4 - (x1xx) Bottom (South)
            8 - (1xxx) Left (West)
        """
        paths_q: int = 0  # quantity of available paths
        x, y = mzParam.entry
        out_x, out_y = mzParam.exit

        # c_path - current path
        c_path: list[list[int]] = [[x, y, 0xf]]
        if len(best_path) > 1:
            c_path = [[i[0], i[1], 0xf] for i in best_path]

        start = time.monotonic()
        # exit if we fond some path and time more than 25 sec
        while ((len(c_path) > 0) and
               ((len(best_path) == 0) or (time.monotonic() - start < 20))):
            i = len(c_path) - 1
            x, y, q = c_path[i]

            if (len(best_path) > 0):
                min_distance = abs(out_x - x) + abs(out_y - y)
                if (((len(c_path) + min_distance) > len(best_path)) or
                   (len(c_path) >= len(best_path))):
                    c_path.pop()
                    continue

            # print("p(i,(x,y,q)):", i, ":", c_path[i])

            # check if we found exit
            if (x == out_x) and (out_y == y):
                paths_q += 1
                if (len(best_path) == 0) or (len(best_path) > len(c_path)):
                    best_path = c_path.copy()
                # print("found path N:", paths_q, " leng:", len(c_path))
                # for i in range(0, len(c_path) - 1):
                #     l_: int = (len(c_path) - i - 1) << 8
                #     x, y, q = c_path[i]
                #     # print('x:', x, 'y:', y, 'q:', q, 'l:', l_, l_ >> 8)
                #     if ((maze[y][x] & 0xffffff00 == 0) or
                #        (maze[y][x] & 0xffffff00 > l_)):
                #         maze[y][x] = (l_ | (maze[y][x] & 0xff))
                c_path.pop()
                if (paths_q == 1) and (time.monotonic() - start > 15):
                    start = time.monotonic() - 15
                continue

            if (i > 0):
                old_ = (maze[y][x] & 0xffffff00) >> 8
                if (old_ == 0) or old_ > i:
                    maze[y][x] = (maze[y][x] & 0xff) | (i << 8)
                    if old_ > 0:
                        l_ = cls.check_point_in_path(best_path, x, y)
                        if l_ > 0:
                            # print(f"!!!!!Best!!!! x={x},y={y},len={i} ")
                            # print("before", len(best_path),":",best_path)
                            best_path = c_path.copy() + best_path[l_:]
                            # print("after", len(best_path),":",best_path)
                            for j_ in range(i + 1, len(best_path)):
                                x, y, _ = best_path[j_]
                                maze[y][x] = (maze[y][x] & 0xff) | (j_ << 8)
                            c_path.pop()
                            continue
                elif (old_ > 0) and ((old_ < i) or
                                     ((q == 0xf) and (old_ == i))):
                    # print("old:", old_,", i:",i, ", p:", c_path)
                    c_path.pop()
                    continue

            # check if we can go through top passage
            if y == 0:
                q = q & 14  # top 1110 = e = 14
            elif (((maze[y-1][x] & 0xc) == 0xc) or
                  (maze[y][x] & 1) or
                  (maze[y-1][x] & 0x20) or
                  (cls.check_point_in_path(c_path, x, y-1) > 0)):
                q = q & 14  # top 1110 = e = 14

            # check if we can go through the reight passage
            if x == mzParam.width - 1:
                q = q & 13  # reight 1101 = d = 13
            elif (((maze[y][x+1] & 0xc) == 0xc) or
                  (maze[y][x] & 2) or
                  (maze[y][x+1] & 0x20) or
                  (cls.check_point_in_path(c_path, x+1, y) > 0)):
                q = q & 13   # reight 1101 = d = 13

            # check if we can go through the bottom passage
            if (q & 4):
                if y == mzParam.height - 1:
                    q = q & 11  # bottom 1011 = b = 11
                elif (((maze[y+1][x] & 0xc) == 0xc) or
                      (maze[y+1][x] & 0x21) or    # wall or dead end
                      (cls.check_point_in_path(c_path, x, y+1) > 0)):
                    q = q & 11  # bottom 1011 = b = 11

            # check if we can go through the left passage
            if (q & 8):
                if (x == 0):
                    q = q & 7   # left 0111 = 7
                # check - pattern, wall, path
                elif (((maze[y][x-1] & 0xc) == 0xc) or
                      (maze[y][x-1] & 0x22) or  # wall or dead end
                      (cls.check_point_in_path(c_path, x-1, y) > 0)):
                    q = q & 7   # left 0111 = 7

            if q == 0:  # there no wall that could be opened
                # if (maze[y][x] & 0xffffff00) == 0:
                #     #  maze[y][x] = maze[y][x] | 0x20   # dead end
                # print(f"end: x={x}, y={y}, len={i}")  # , path:", c_path)
                c_path.pop()
                continue

            if (abs(out_x - x) > abs(out_y - y)):
                # go by x first ---
                if (out_x > x) and (q & 2):
                    # 2 - (xx1x) Right (East)
                    c_path[i][2] = q & 0xd
                    c_path.append([x+1, y, 0xf])
                    continue
                if (out_x < x) and (q & 8):
                    # 8 - (1xxx) Left (West)
                    c_path[i][2] = q & 0x7
                    c_path.append([x-1, y, 0xf])
                    continue
                # then by y ...
                if (out_y > y) and (q & 4):
                    # 4 - (x1xx) Bottom (South)
                    c_path[i][2] = q & 0xb
                    c_path.append([x, y+1, 0xf])
                    continue
                if (out_y < y) and (q & 1):
                    # 1 - (xxx1) Top wall (North)
                    c_path[i][2] = q & 0xe
                    c_path.append([x, y-1, 0xf])
                    continue
            else:
                # go by y first ---
                if (out_y > y) and (q & 4):
                    # 4 - (x1xx) Bottom (South)
                    c_path[i][2] = q & 0xb
                    c_path.append([x, y+1, 0xf])
                    continue
                if (out_y < y) and (q & 1):
                    # 1 - (xxx1) Top wall (North)
                    c_path[i][2] = q & 0xe
                    c_path.append([x, y-1, 0xf])
                    continue
                # then by x ...
                if (out_x > x) and (q & 2):
                    # 2 - (xx1x) Right (East)
                    c_path[i][2] = q & 0xd
                    c_path.append([x+1, y, 0xf])
                    continue
                if (out_x < x) and (q & 8):
                    # 8 - (1xxx) Left (West)
                    c_path[i][2] = q & 0x7
                    c_path.append([x-1, y, 0xf])
                    continue
            # no step in direction to out
            if (q & 1):
                # 1 - (xxx1) Top wall (North)
                c_path[i][2] = q & 0xe
                c_path.append([x, y-1, 0xf])
                continue
            if (q & 2):
                # 2 - (xx1x) Right (East)
                c_path[i][2] = q & 0xd
                c_path.append([x+1, y, 0xf])
                continue
            if (q & 4):
                # 4 - (x1xx) Bottom (South)
                c_path[i][2] = q & 0xb
                c_path.append([x, y+1, 0xf])
                continue
            if (q & 8):
                # 8 - (1xxx) Left (West)
                c_path[i][2] = q & 0x7
                c_path.append([x-1, y, 0xf])
                continue
            c_path[i][2] = q
            print("Error")
            c_path.pop()
        if len(c_path) > 0:
            print("It may be not the shortest path...")
        return best_path

    @classmethod
    def gen_DFS(cls, maze: list[list[int]],
                mzParam: CMazeParams) -> list[list[int]]:
        """
        Used Depth-first search (DFS) algorithm to generate perfect maze.

        Start from EXIT point

        maze - value 1xxxx - flag "visited"

        m_path [x,y,q] - current path
        there q - quantity of walls that could be opened
            1 - (xxx1) Top wall (North),
            2 - (xx1x) Right (East),
            4 - (x1xx) Bottom (South)
            8 - (1xxx) Left (West)
        """

        x, y = mzParam.exit
        maze[y][x] = maze[y][x] | 0x10  # set visited flag
        m_path: list[list[int]] = [[x, y, 0xf]]

        while (len(m_path) > 0):
            i = len(m_path) - 1
            x, y, q = m_path[i]

            # check if top wall can be opened
            if (q & 1):
                if y == 0:
                    q = q & 14  # top 1110 = e = 14
                elif (maze[y-1][x] & 0x1c) >= 0xc:     # pattern ot visited
                    q = q & 14  # top 1110 = e = 14

            # check if reight wall can be opened
            if (q & 2):
                if x == mzParam.width - 1:
                    q = q & 13  # reight 1101 = d = 13
                elif (maze[y][x+1] & 0x1c) >= 0xc:     # pattern ot visited
                    q = q & 13  # reight 1101 = d = 13

            # check if bottom wall can be opened
            if (q & 4):
                if y == mzParam.height - 1:
                    q = q & 11  # bottom 1011 = b = 11
                elif (maze[y+1][x] & 0x1c) >= 0xc:     # pattern ot visited
                    q = q & 11  # bottom 1011 = b = 11

            # check if left wall can be opened
            if (q & 8):
                if (x == 0):
                    q = q & 7   # left 0111 = 7
                elif (maze[y][x-1] & 0x1c) >= 0xc:     # pattern ot visited
                    q = q & 7   # left 0111 = 7

            if q == 0:  # there no wall that could be opened
                m_path.pop()
                continue

            # Randomly choose one of the walls to open
            chosen_wall = random.choice([(1 << i)
                                         for i in range(4) if (q >> i) & 1])
            match chosen_wall:
                case 1:
                    # 1 - (xxx1) Top wall (North)
                    m_path[i][2] = q & 0xe
                    m_path.append([x, y-1, 0xf])
                    maze[y][x] = maze[y][x] & 0xfffe  # remove Top wall
                    maze[y-1][x] = maze[y-1][x] | 0x10  # set visited flag
                case 2:
                    # 2 - (xx1x) Right (East)
                    m_path[i][2] = q & 0xd
                    m_path.append([x+1, y, 0xf])
                    maze[y][x] = maze[y][x] & 0xfffd  # remove Right wall
                    maze[y][x+1] = maze[y][x+1] | 0x10  # set visited flag
                case 4:
                    # 4 - (x1xx) Bottom (South)
                    m_path[i][2] = q & 0xb
                    m_path.append([x, y+1, 0xf])
                    maze[y+1][x] = (maze[y+1][x] & 0xfffe)  # remove Top wall
                    maze[y+1][x] = maze[y+1][x] | 0x10  # set visited flag
                case 8:
                    # 8 - (1xxx) Left (West)
                    m_path[i][2] = q & 0x7
                    m_path.append([x-1, y, 0xf])
                    maze[y][x-1] = maze[y][x-1] & 0xfffd  # remove Right wall
                    maze[y][x-1] = maze[y][x-1] | 0x10  # set visited flag
                case _:
                    m_path[i][2] = q
                    print("Error")
                    m_path.pop()
            # if animated:
            #     yield maze
        return maze

    @classmethod
    def gen_DFS_animated(cls, maze: list[list[int]],
                         mzParam: CMazeParams,
                         animated: bool = False
                         ) -> Generator[tuple[int, int, int, int] |
                                        None, None, None]:
        """
        Used Depth-first search (DFS) algorithm to generate perfect maze.

        Start from EXIT point

        maze - value 1xxxx - flag "visited"

        m_path [x,y,q] - current path
        there q - quantity of walls that could be opened
            1 - (xxx1) Top wall (North),
            2 - (xx1x) Right (East),
            4 - (x1xx) Bottom (South)
            8 - (1xxx) Left (West)
        """

        x, y = mzParam.exit
        maze[y][x] = maze[y][x] | 0x10  # set visited flag
        m_path: list[list[int]] = [[x, y, 0xf]]

        while (len(m_path) > 0):
            i = len(m_path) - 1
            x, y, q = m_path[i]

            # check if top wall can be opened
            if (q & 1):
                if y == 0:
                    q = q & 14  # top 1110 = e = 14
                elif (maze[y-1][x] & 0x1c) >= 0xc:     # pattern ot visited
                    q = q & 14  # top 1110 = e = 14

            # check if reight wall can be opened
            if (q & 2):
                if x == mzParam.width - 1:
                    q = q & 13  # reight 1101 = d = 13
                elif (maze[y][x+1] & 0x1c) >= 0xc:     # pattern ot visited
                    q = q & 13  # reight 1101 = d = 13

            # check if bottom wall can be opened
            if (q & 4):
                if y == mzParam.height - 1:
                    q = q & 11  # bottom 1011 = b = 11
                elif (maze[y+1][x] & 0x1c) >= 0xc:     # pattern ot visited
                    q = q & 11  # bottom 1011 = b = 11

            # check if left wall can be opened
            if (q & 8):
                if (x == 0):
                    q = q & 7   # left 0111 = 7
                elif (maze[y][x-1] & 0x1c) >= 0xc:     # pattern ot visited
                    q = q & 7   # left 0111 = 7

            if q == 0:  # there no wall that could be opened
                m_path.pop()
                continue

            # Randomly choose one of the walls to open
            chosen_wall = random.choice([(1 << i)
                                         for i in range(4) if (q >> i) & 1])
            match chosen_wall:
                case 1:
                    # 1 - (xxx1) Top wall (North)
                    m_path[i][2] = q & 0xe
                    m_path.append([x, y-1, 0xf])
                    maze[y][x] = maze[y][x] & 0xfffe  # remove Top wall
                    maze[y-1][x] = maze[y-1][x] | 0x10  # set visited flag
                case 2:
                    # 2 - (xx1x) Right (East)
                    m_path[i][2] = q & 0xd
                    m_path.append([x+1, y, 0xf])
                    maze[y][x] = maze[y][x] & 0xfffd  # remove Right wall
                    maze[y][x+1] = maze[y][x+1] | 0x10  # set visited flag
                case 4:
                    # 4 - (x1xx) Bottom (South)
                    m_path[i][2] = q & 0xb
                    m_path.append([x, y+1, 0xf])
                    maze[y+1][x] = (maze[y+1][x] & 0xfffe)  # remove Top wall
                    maze[y+1][x] = maze[y+1][x] | 0x10  # set visited flag
                case 8:
                    # 8 - (1xxx) Left (West)
                    m_path[i][2] = q & 0x7
                    m_path.append([x-1, y, 0xf])
                    maze[y][x-1] = maze[y][x-1] & 0xfffd  # remove Right wall
                    maze[y][x-1] = maze[y][x-1] | 0x10  # set visited flag
                case _:
                    m_path[i][2] = q
                    print("Error")
                    m_path.pop()
            if animated:
                yield (x-1, y-1, x+1, y+1)
        yield None
        return

    @classmethod
    def do_not_prefect(cls, maze: list[list[int]],
                       mzParam: CMazeParams) -> list[list[int]]:
        pr = mzParam.probability_to_del_dead_end
        if pr <= 0:
            return maze
        for y in range(0, len(maze)):
            for x in range(0, len(maze[0])):
                # check for dead end - there is 3 wall
                v = maze[y][x]
                if v & 0xc:   # skeep pattern, entry, exit
                    continue
                v = v & 3
                if y == 0:
                    v = v | 1
                if x == 0:
                    v = v | 8
                elif (maze[y][x-1] & 2):
                    v = v | 8
                if y == (len(maze)-1):
                    v = v | 4
                elif (maze[y+1][x] & 1):
                    v = v | 4
                if x == (len(maze[0])-1):
                    v = v | 2
                w = v
                if len([(1 << i) for i in range(4) if (v >> i) & 1]) == 3:
                    # dead end found
                    # print(f"dead end x={x}, y={y}, w={w}")
                    if ((pr >= 100) or (random.random() < (0.01 * pr))):
                        # Trying to delete wall
                        # At first try to find walls that could be removed
                        if w & 1:   # top
                            if y == 0:
                                w = w & 0xe  # e  1110
                            elif (maze[y-1][x] & 0xc) == 0xc:     # pattern
                                w = w & 0xe
                        if w & 2:   # reight
                            if x == (len(maze[0])-1):
                                w = w & 13   # d  1101
                            elif (maze[y][x+1] & 0xc) == 0xc:     # pattern
                                w = w & 13
                        if w & 4:   # bottom
                            if y == (len(maze)-1):
                                w = w & 11   # b  1011
                            elif (maze[y+1][x] & 0xc) == 0xc:     # pattern
                                w = w & 11
                        if w & 8:   # left
                            if x == 0:
                                w = w & 7   # 7  0111
                            elif (maze[y][x-1] & 0xc) == 0xc:     # pattern
                                w = w & 7
                        if (w == 0):     # walls can`t be removed
                            continue
                        chosen_wall = random.choice([(1 << i) for i in range(4)
                                                     if (w >> i) & 1])
                        #  print("wall:", chosen_wall)
                        match chosen_wall:
                            case 1:
                                # 1 - (xxx1) Top wall (North)
                                maze[y][x] = maze[y][x] & 0xfffe
                                continue
                            case 2:
                                # 2 - (xx1x) Right (East)
                                maze[y][x] = maze[y][x] & 0xfffd
                                continue
                            case 4:
                                # 4 - (x1xx) Bottom (South)
                                maze[y+1][x] = (maze[y+1][x] & 0xfffe)
                                continue
                            case 8:
                                maze[y][x-1] = (maze[y][x-1] & 0xfffd)
                                continue

        return maze

    @classmethod
    def do_not_prefect_animated(cls, maze: list[list[int]],
                                mzParam: CMazeParams,
                                animated: bool = True
                                ) -> Generator[tuple[int, int, int, int]
                                               | None, None, None]:
        pr = mzParam.probability_to_del_dead_end
        if pr <= 0:
            return
        for y in range(0, len(maze)):
            for x in range(0, len(maze[0])):
                # check for dead end - there is 3 wall
                v = maze[y][x]
                if v & 0xc:   # skeep pattern, entry, exit
                    continue
                v = v & 3
                if y == 0:
                    v = v | 1
                if x == 0:
                    v = v | 8
                elif (maze[y][x-1] & 2):
                    v = v | 8
                if y == (len(maze)-1):
                    v = v | 4
                elif (maze[y+1][x] & 1):
                    v = v | 4
                if x == (len(maze[0])-1):
                    v = v | 2
                w = v
                if len([(1 << i) for i in range(4) if (v >> i) & 1]) == 3:
                    # dead end found
                    # print(f"dead end x={x}, y={y}, w={w}")
                    if ((pr >= 100) or (random.random() < (0.01 * pr))):
                        # Trying to delete wall
                        # At first try to find walls that could be removed
                        if w & 1:   # top
                            if y == 0:
                                w = w & 0xe  # e  1110
                            elif (maze[y-1][x] & 0xc) == 0xc:     # pattern
                                w = w & 0xe
                        if w & 2:   # reight
                            if x == (len(maze[0])-1):
                                w = w & 13   # d  1101
                            elif (maze[y][x+1] & 0xc) == 0xc:     # pattern
                                w = w & 13
                        if w & 4:   # bottom
                            if y == (len(maze)-1):
                                w = w & 11   # b  1011
                            elif (maze[y+1][x] & 0xc) == 0xc:     # pattern
                                w = w & 11
                        if w & 8:   # left
                            if x == 0:
                                w = w & 7   # 7  0111
                            elif (maze[y][x-1] & 0xc) == 0xc:     # pattern
                                w = w & 7
                        if (w == 0):     # walls can`t be removed
                            continue
                        chosen_wall = random.choice([(1 << i) for i in range(4)
                                                     if (w >> i) & 1])
                        #  print("wall:", chosen_wall)
                        match chosen_wall:
                            case 1:
                                # 1 - (xxx1) Top wall (North)
                                maze[y][x] = maze[y][x] & 0xfffe
                            case 2:
                                # 2 - (xx1x) Right (East)
                                maze[y][x] = maze[y][x] & 0xfffd
                            case 4:
                                # 4 - (x1xx) Bottom (South)
                                maze[y+1][x] = (maze[y+1][x] & 0xfffe)
                            case 8:
                                maze[y][x-1] = (maze[y][x-1] & 0xfffd)
                        if animated:
                            yield (x-1, y-1, x+1, y+1)
        yield None
        return

    @classmethod
    def generate_animated(cls, mzParam: CMazeParams,
                          maze: list[list[int]]
                          ) -> Generator[tuple[int, int, int, int] |
                                         None, None, None]:

        maze.clear
        for _ in range(mzParam.height):
            maze.append([3] * mzParam.width)

        # place entry
        maze[mzParam.entry[1]][mzParam.entry[0]] = 7
        # place exit
        maze[mzParam.exit[1]][mzParam.exit[0]] = 11

        yield None

        if mzParam.insert_42:
            if not (cls.place_42(maze, mzParam.entry, mzParam.exit)):
                print('Error: It is impossible to place the "42" pattern '
                      'in the maze.', file=sys.stderr)
        yield None

        if not (mzParam.seed is None):
            random.seed(mzParam.seed)

        yield None

        for a_ in cls.gen_DFS_animated(maze, mzParam, animated=True):
            yield a_

        if not (mzParam.perfect):
            for a_ in cls.do_not_prefect_animated(maze,
                                                  mzParam,
                                                  animated=True):
                yield a_

        return

    @classmethod
    def generate(cls, mzParam: CMazeParams) -> list[list[int]]:

        """
        Return list[hieght][width] of int.
        Value in cell:
            1 - (xxx1) Top wall (North),
            2 - (xx1x) Right (East),
            4 - (01xx) - entry
            8 - (10xx) - exit
            f - (1111) - pattern
        """
        maze: list[list[int]] = [[3] * mzParam.width
                                 for _ in range(mzParam.height)]
        # place entry
        maze[mzParam.entry[1]][mzParam.entry[0]] = 7
        # place exit
        maze[mzParam.exit[1]][mzParam.exit[0]] = 11

        if mzParam.insert_42:
            if not (cls.place_42(maze, mzParam.entry, mzParam.exit)):
                print('Error: It is impossible to place the "42" pattern '
                      'in the maze.', file=sys.stderr)

        if not (mzParam.seed is None):
            random.seed(mzParam.seed)

        maze = cls.gen_DFS(maze, mzParam)
        if not (mzParam.perfect):
            maze = cls.do_not_prefect(maze, mzParam)

        return maze

    @classmethod
    def write_to_file(cls, maze: list[list[int]],
                      mzParam: CMazeParams,
                      path: list[list[int]] = [],
                      file_name: str = "") -> bool:
        if (not (type(file_name) is str)) or (len(file_name) <= 0):
            file_name = mzParam.output_file
        # print(f"file:'{file_name}', {len(file_name)}")
        if (not (type(file_name) is str)) or (len(file_name) <= 0):
            print("Can`t save the maze to file, file name not defined!")
            return False
        with open(file_name, "w", encoding="utf-8") as f:
            for y in range(0, len(maze)):
                for x in range(0, len(maze[0])):
                    v = maze[y][x] & 3
                    if y == 0:
                        v = v | 1
                    if x == 0:
                        v = v | 8
                    elif (maze[y][x-1] & 2):
                        v = v | 8
                    if y == (len(maze)-1):
                        v = v | 4
                    elif (maze[y+1][x] & 1):
                        v = v | 4
                    if x == (len(maze[0])-1):
                        v = v | 2
                    f.write(format(v, "X"))
                f.write("\n")
            f.write("\n")
            f.write(f"{mzParam.entry[0]},{mzParam.entry[1]}\n")
            f.write(f"{mzParam.exit[0]},{mzParam.exit[1]}\n")
            if len(path) == 0:
                path = cls.find_path_BFS(maze, mzParam)
            for i in range(1, len(path)):
                s = "-"
                if path[i][0] > path[i-1][0]:
                    s = "E"
                elif path[i][0] < path[i-1][0]:
                    s = "W"
                elif path[i][1] > path[i-1][1]:
                    s = "S"
                elif path[i][1] < path[i-1][1]:
                    s = "N"
                f.write(s)
            f.write("\n")
        return True
