import sys
import os
import time
from dotenv import load_dotenv
from typing import cast, Any
import random
from pydantic import ValidationError
from mazegen import CMazeParams, MazeGenerator
# import mlx
from mlx import Mlx
import atexit
import signal


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


def main() -> None:

    def draw_filled_rect(x: int, y: int, w: int, h: int,
                         color: int = 0xffffffff) -> None:
        """ x,y - top left point
            color: aRGB
        """
        color = 0xffffffff & color
        if (color & 0xff000000) == 0:
            color += 0xff000000
        for j in range(h):
            for i in range(w):
                m.mlx_pixel_put(mlx_ptr, m_win_ptr, x + i, y + j, color)

    def draw_maze(maze_: list[list[int]],
                  param: CMazeParams,
                  path_: list[list[int]] = [],
                  draw_area: tuple[int, int, int, int] | None = None) -> None:
        wall_color = param.colors.get("wall", 0xff959696)
        pattern_color = param.colors.get("pattern", 0xffffffff)
        # outer wall - top
        draw_filled_rect(0, 0, WIN_W, param.w_wall_thickness, wall_color)
        # outer wall - left
        draw_filled_rect(0, 0, param.w_wall_thickness, WIN_MH, wall_color)
        # outer wall - bottom
        draw_filled_rect(0, WIN_MH - param.w_wall_thickness,
                         WIN_W, param.w_wall_thickness, wall_color)
        # outer wall - reight
        draw_filled_rect(WIN_W - param.w_wall_thickness, 0,
                         param.w_wall_thickness, WIN_MH, wall_color)

        y_from: int = 0
        y_to: int = len(maze_)
        x_from: int = 0
        if y_to > 0:
            x_to: int = len(maze_[0])
        else:
            x_to = 0

        if not (draw_area is None):
            x_from, y_from, x_to, y_to = draw_area

            y_from = max(0, y_from)
            y_from = min(y_from, len(maze_))

            y_to = max(0, y_to)
            y_to = min(y_to, len(maze_))

            x_from = max(0, x_from)
            x_to = max(0, x_to)
            if len(maze_) > 0:
                x_from = min(x_from, len(maze_[0]))
                x_to = min(x_to, len(maze_[0]))

        for y in range(y_from, y_to):
            y_l = y * (param.w_wall_thickness+param.w_cell_size)
            for x in range(x_from, x_to):
                x_l = x * (param.w_wall_thickness+param.w_cell_size)
                val = maze_[y][x]
                # print(f"x, y : {x},{y} = val: {val}, ({val & 0xf})")
                if (val & 0xf) == 0xf:   # pattern
                    draw_filled_rect(x_l + param.w_wall_thickness,
                                     y_l + param.w_wall_thickness,
                                     param.w_cell_size,
                                     param.w_cell_size, pattern_color)
                elif (val & 0xc) == 0x4:   # entry
                    draw_filled_rect(x_l + param.w_wall_thickness,
                                     y_l + param.w_wall_thickness,
                                     param.w_cell_size,
                                     param.w_cell_size,
                                     param.colors.get("entry", 0xFF27C8F5))
                elif (val & 0xc) == 0x8:   # exit
                    draw_filled_rect(x_l + param.w_wall_thickness,
                                     y_l + param.w_wall_thickness,
                                     param.w_cell_size,
                                     param.w_cell_size,
                                     param.colors.get("exit", 0xFF38F527))
                if (val & 0x1) == 1:   # Top wall (Nord)
                    draw_filled_rect(x_l,
                                     y_l,
                                     (param.w_cell_size +
                                      param.w_wall_thickness * 2),
                                     param.w_wall_thickness,
                                     wall_color)
                else:
                    draw_filled_rect(x_l+param.w_wall_thickness,
                                     y_l,
                                     (param.w_cell_size),
                                     param.w_wall_thickness,
                                     0xff000000)

                if (val & 0x2) == 2:   # Reight wall (East)
                    draw_filled_rect((x_l + param.w_cell_size
                                      + param.w_wall_thickness),
                                     y_l,
                                     param.w_wall_thickness,
                                     (param.w_cell_size
                                      + param.w_wall_thickness * 2),
                                     wall_color)
                else:
                    draw_filled_rect((x_l + param.w_cell_size
                                      + param.w_wall_thickness),
                                     y_l + param.w_wall_thickness,
                                     param.w_wall_thickness,
                                     param.w_cell_size,
                                     0xff000000)

        if draw_area is None:
            m.mlx_string_put(mlx_ptr, m_win_ptr, 10,
                             WIN_H - 80, 0xf0f0f0,
                             "=== A-Maze-ing ===")
            m.mlx_string_put(mlx_ptr, m_win_ptr, 10,
                             WIN_H - 60, 0xf0f0f0,
                             "1 - Regenerate")
            m.mlx_string_put(mlx_ptr, m_win_ptr, 10,
                             WIN_H - 40, 0xf0f0f0,
                             "2 - Path, 3 - Color")
            if len(path_) > 0:
                m.mlx_string_put(mlx_ptr, m_win_ptr, 10,
                                 WIN_H - 20, 0xf0f0f0,
                                 "4 - Quit, A - Animation")
            else:
                m.mlx_string_put(mlx_ptr, m_win_ptr, 10,
                                 WIN_H - 20, 0xf0f0f0,
                                 "4 - Quit")

        else:
            m.mlx_string_put(mlx_ptr, m_win_ptr, 0,
                             WIN_H - 20, 0xf0f0f0,
                             " ")

        path_color = param.colors.get("path", 0xFFe0e020)
        for i in range(1, len(path_)-1):
            x, y, _ = path_[i]
            old_x, old_y, _ = path_[i-1]

            if x == old_x:
                if old_y > y:
                    draw_filled_rect(
                        (x*(param.w_wall_thickness+param.w_cell_size) +
                         param.w_wall_thickness),
                        (old_y*(param.w_wall_thickness+param.w_cell_size)),
                        param.w_cell_size,
                        param.w_wall_thickness,
                        path_color)
                else:
                    draw_filled_rect(
                        (x*(param.w_wall_thickness+param.w_cell_size) +
                         param.w_wall_thickness),
                        (y*(param.w_wall_thickness+param.w_cell_size)),
                        param.w_cell_size,
                        param.w_wall_thickness,
                        path_color)
            else:
                if old_x > x:
                    draw_filled_rect(
                        (old_x*(param.w_wall_thickness+param.w_cell_size)),
                        (y*(param.w_wall_thickness+param.w_cell_size) +
                         param.w_wall_thickness),
                        param.w_wall_thickness,
                        param.w_cell_size,
                        path_color)
                else:
                    draw_filled_rect(
                        (x*(param.w_wall_thickness+param.w_cell_size)),
                        (y*(param.w_wall_thickness+param.w_cell_size) +
                         param.w_wall_thickness),
                        param.w_wall_thickness,
                        param.w_cell_size,
                        path_color)

            draw_filled_rect((x*(param.w_wall_thickness+param.w_cell_size) +
                              param.w_wall_thickness),
                             (y*(param.w_wall_thickness+param.w_cell_size) +
                              param.w_wall_thickness),
                             param.w_cell_size,
                             param.w_cell_size,
                             path_color)

            # m.mlx_sync(mlx_ptr, 0 , m_win_ptr)
            # Delay for 0.1 second
            # print(i)
            m.mlx_string_put(mlx_ptr, m_win_ptr, 0,
                             WIN_H - 20, 0xf0f0f0,
                             " ")

            time.sleep(0.01)

        if len(path_) > 1:
            i = len(path_)-1
            x, y, _ = path_[i]
            old_x, old_y, _ = path_[i-1]

            if x == old_x:
                if old_y > y:
                    draw_filled_rect(
                        (x*(param.w_wall_thickness+param.w_cell_size) +
                         param.w_wall_thickness),
                        (old_y*(param.w_wall_thickness+param.w_cell_size)),
                        param.w_cell_size,
                        param.w_wall_thickness,
                        path_color)
                else:
                    draw_filled_rect(
                        (x*(param.w_wall_thickness+param.w_cell_size) +
                         param.w_wall_thickness),
                        (y*(param.w_wall_thickness+param.w_cell_size)),
                        param.w_cell_size,
                        param.w_wall_thickness,
                        path_color)
            else:
                if old_x > x:
                    draw_filled_rect(
                        (old_x*(param.w_wall_thickness+param.w_cell_size)),
                        (y*(param.w_wall_thickness+param.w_cell_size) +
                         param.w_wall_thickness),
                        param.w_wall_thickness,
                        param.w_cell_size,
                        path_color)
                else:
                    draw_filled_rect(
                        (x*(param.w_wall_thickness+param.w_cell_size)),
                        (y*(param.w_wall_thickness+param.w_cell_size) +
                         param.w_wall_thickness),
                        param.w_wall_thickness,
                        param.w_cell_size,
                        path_color)

    if len(sys.argv) != 2:
        print("Error: Wrong parameters\n"
              "Usage: python3 ", sys.argv[0], " <config_file>",
              file=sys.stderr)
        sys.exit(1)
    print("Hi in a Maze!")
    if not fm_read_config(sys.argv[1]):  # config file not fond
        sys.exit(1)
    if not fm_check_param({"WIDTH": 1,
                           "HEIGHT": 1,
                           "ENTRY": 3,
                           "EXIT": 3,
                           "OUTPUT_FILE": 1,
                           "PERFECT": 4
                           }):
        sys.exit(1)
    insert_42 = (not (os.getenv("INSERT_42") == 'False'))
    try:
        val_ = os.getenv("W_CELL_SIZE")
        if val_ is None:
            w_cell_size = 25
        else:
            w_cell_size = int(val_)
    except Exception:
        w_cell_size = 25

    try:
        c_mz_param = CMazeParams(width=cast(int, os.getenv("WIDTH")),
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
    except ValidationError as e:
        # for err in e.errors():
        #     print(err["msg"])
        print(e, file=sys.stderr)
        sys.exit(1)

    print("Maze config:", c_mz_param.print())
    maze_ = MazeGenerator.generate(c_mz_param)

    # print("Maze:", maze_)
    start = time.monotonic()
    # path_ = MazeGenerator.find_path_DFS(maze_, c_mz_param)
    path_ = MazeGenerator.find_path_BFS(maze_, c_mz_param)
    # path_ = []
    print("Time:",  time.monotonic() - start, "sec.")
    print("Path lenght:", len(path_))
    # print("Path:", path_)
    # print("Maze:", maze_)

    # save maze to file
    MazeGenerator.write_to_file(maze_, c_mz_param, path_)

    ROWS = len(maze_)
    COLS = len(maze_[0])

    WIN_W = (COLS * (c_mz_param.w_cell_size + c_mz_param.w_wall_thickness)
             + c_mz_param.w_wall_thickness)
    WIN_MH = (ROWS * (c_mz_param.w_cell_size + c_mz_param.w_wall_thickness)
              + c_mz_param.w_wall_thickness)

    WIN_H = WIN_MH + 80

    # print(dir(Mlx))

    def m_mymouse(button: int, x: int, y: int, mystuff: Any) -> None:
        print(f"Got mouse event! button {button} at {x},{y}.")

    def m_gere_close(dummy: Any) -> None:
        m.mlx_loop_exit(mlx_ptr)

    def m_mykey(keynum: int, stuff: int) -> None:
        stuff
        nonlocal maze_
        nonlocal path_

        if keynum == 49:                        # 1 - regenerate maze
            maze_ = MazeGenerator.generate(c_mz_param)
            m.mlx_clear_window(mlx_ptr, m_win_ptr)
            if len(path_) > 0:
                draw_maze(maze_, c_mz_param, [])
                path_ = MazeGenerator.find_path_BFS(maze_, c_mz_param)
            draw_maze(maze_, c_mz_param, path_)

        elif keynum == 97:                      # a - generate with animation
            maze_ = []
            m.mlx_clear_window(mlx_ptr, m_win_ptr)
            for area_ in MazeGenerator.generate_animated(c_mz_param, maze_):
                draw_maze(maze_, c_mz_param, [], area_)
                # time.sleep(0.001)
            if len(path_) > 0:
                path_ = MazeGenerator.find_path_BFS(maze_, c_mz_param)
            m.mlx_clear_window(mlx_ptr, m_win_ptr)
            draw_maze(maze_, c_mz_param, path_)

        elif keynum == 65307 or keynum == 52:   # Esc or 4 - Exit
            m.mlx_loop_exit(mlx_ptr)

        elif keynum == 50:                      # 2 - path
            if len(path_) < 1:
                maze_ = MazeGenerator.clear_tmp_data(maze_)
                path_ = MazeGenerator.find_path_BFS(maze_, c_mz_param)
                draw_maze(maze_, c_mz_param, path_)
            else:
                path_ = []
                m.mlx_clear_window(mlx_ptr, m_win_ptr)
                draw_maze(maze_, c_mz_param, path_)

        elif keynum == 51:                      # 3 - cange color
            argb = random.randint(0x101010, 0xFFFFFF) | 0xff000000
            c_mz_param.colors["wall"] = argb
            argb = random.randint(0x101010, 0xFFFFFF) | 0xff000000
            c_mz_param.colors["pattern"] = argb
            m.mlx_clear_window(mlx_ptr, m_win_ptr)
            draw_maze(maze_, c_mz_param, path_)

        elif keynum == 115:                     # s - save
            MazeGenerator.write_to_file(maze_, c_mz_param, path_)
            print(f"The maze saved to file '{c_mz_param.output_file}'")
        elif keynum == 32:
            m.mlx_mouse_hook(m_win_ptr, None, None)
        else:
            print(f"Got key {keynum}, and got my stuff back:")

    def cleanup() -> None:
        # try:
        #     print("Try close windows")
        # except Exception:
        #     pass
        try:
            m.mlx_loop_exit(mlx_ptr)
        except Exception:
            pass
        try:
            m.mlx_destroy_window(mlx_ptr, m_win_ptr)
        except Exception:
            pass

    def signal_handler(sig: int, frame: Any) -> None:
        sig
        frame
        cleanup()
        sys.exit(0)

    m = Mlx()
    mlx_ptr = m.mlx_init()

    name = "Maze"
    if (c_mz_param.perfect):
        name = "The perfect maze"
    m_win_ptr = m.mlx_new_window(mlx_ptr, max(WIN_W, 240), WIN_H, name)

    m.mlx_clear_window(mlx_ptr, m_win_ptr)

    stuff = [1, 2]
    m.mlx_mouse_hook(m_win_ptr, m_mymouse, None)
    m.mlx_key_hook(m_win_ptr, m_mykey, stuff)
    m.mlx_hook(m_win_ptr, 33, 0, m_gere_close, None)

    draw_maze(maze_, c_mz_param, path_)

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGCONT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    m.mlx_loop(mlx_ptr)


if __name__ == "__main__":
    main()
