# MazeGen Library

A Python library for work with 2d maze - generation and finding shortest path.


## Installation

```bash
pip install mazegen-1.0.0-py3-none-any.whl
```

## Quick Start

```python
from mazegen import MazeGenerator, CMazeParams

m_param = CMazeParams(width=20,
                      height=20,
                      entry=(2,3),
                      exit=(19,18),
                      output_file="maze_write_file.txt",
                      perfect=False
                     )

maze_ = MazeGenerator.generate(m_param)
path_ = MazeGenerator.find_path_BFS(maze_, m_param)

# save maze to file
MazeGenerator.write_to_file(maze_, m_param)
```

### MazeGenerator Class
**metods:**
```
    generate(mzParam: CMazeParams) -> maze: list[list[int]]

    do_not_prefect(maze: list[list[int]], mzParam: CMazeParams) -> maze: list[list[int]]:

    write_to_file(maze: list[list[int]],
                  mzParam: CMazeParams,
                  path: list[list[int]] = [],
                  file_name: str) -> bool:
```


### CMazeParams Class

**Attributes:**
```
    width: int                  # Maze width in cells
    height: int                 # Maze height in cells
    entry: tuple[int, int]      # Entry position (x, y)
    exit: tuple[int, int]       # Exit position (x, y)
    output_file: str            # Output file path/name
    perfect: bool = True		# Perfect maze flag
    seed: int | None = None     # Seed for initialize randomizer
    insert_42: bool = True      # Flag - try to place "42" pattern in a maze	
    w_cell_size: int = 25		
    w_wall_thickness: int = 4
    colors: dict[str, int] = {"wall": 0x959696,
                              "entry": 0xFF27C8F5,
                              "exit": 0xFF38F527,
                              "pattern": 0xFFFFFFFF
                              }
    probability_to_del_dead_end: int = 99 # Probability to del dead end in procent (0-100%)
```


## Requirements

- Python 3.10 or later
- Pydantic
- Dotenv

## License

Part of the 42 curriculum project.