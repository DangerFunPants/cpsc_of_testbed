
import pathlib as path

# output path used in "save_figure" calls
FIGURE_OUTPUT_PATH = path.Path("/home/cpsc-net-user/")

# Location of the legend for plots.
LEGEND_HEIGHT = 1.125

# Various parameters to control the look of generated plots
SOLUTION_LABELS         = ["rnd", "det", "df", "greedy", "optimal"]
LEGEND_LABELS           = ["$\\epsilon$-LPR", "LPR", "DuFi", "Greedy", "Optimal"]
BAR_PLOT_COLORS         = ["red", "green", "blue", "orange", "purple"]
BAR_PLOT_TEXTURES       = ["//", "\\", "//", "\\", "//"]
