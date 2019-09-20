
import pathlib as path

# output path used in "save_figure" calls
FIGURE_OUTPUT_PATH = path.Path("/home/cpsc-net-user/")

# Location of the legend for plots.
LEGEND_HEIGHT = 1.125

# Various parameters to control the look of generated plots
# SOLUTION_LABELS         = ["rnd", "det", "df", "greedy", "optimal"]
# LEGEND_LABELS           = ["$\\epsilon$-LPR", "LPR", "DuFi", "Greedy", "Optimal"]
SOLUTION_LABELS         = { "rnd"       : "$\\epsilon$-LPR"
                          , "det"       : "LPR"
                          , "df"        : "DuFi"
                          , "optimal"   : "Optimal"
                          }

LEGEND_LABELS           = ["$\\epsilon$-LPR$", "LPR", "DuFi", "Optimal"]
# BAR_PLOT_COLORS         = ["red", "green", "royalblue", "orange", "purple"]
# BAR_PLOT_COLORS         = ["white", "white", "white", "white", "white"]
BAR_PLOT_COLORS         = ["palegreen", "skyblue", "lightpink", "silver"]
# BAR_PLOT_TEXTURES       = ["//", "O", "x", "*", "|"]
BAR_PLOT_TEXTURES       = ["//", ".", "*", "\\", "|"]

MARKER_STYLE            = ["x", "^", "o", "+", "1", "s"]
MARKER_COLOR            = ["red", "lime", "palegreen"]
# LINE_STYLE              = ["--", "-", "-."]
LINE_STYLE              = ["-", "-.", "--"]
LINE_COLOR              = ["lime", "royalblue", "red", "blue", "saddlebrown", "darkorange"]
FONT                    = { "family"        : "serif"
                          , "size"          : 16
                          }

TICK_FONT               = { "family"        : "sans-serif"
                          , "size"          : 10
                          }

LEGEND                  = { "shadow"            : False
                          , "fontsize"          : 10
                          , "handletextpad"     : 0.3
                          , "columnspacing"     : 1.0
                          , "fancybox"          : False
                          , "edgecolor"         : "black"
                          , "loc"               : "upper center"
                          , "bbox_to_anchor"    : (0.5, 1.15)
                          # , "size"          : 10
                          }

AXIS_LABELS             = { "fontsize"  : 22
                          , "family"    : "serif"
                          }

BOX_WIDTH               = 0.75

GRID                    = { "b"         : True
                          , "which"     : "both"
                          , "color"     : "lightgray"
                          , "linestyle" : "--"
                          }

BASIC_CDF_PARAMS        = { "marker"        : "x"
                          , "linestyle"     : "-."
                          }
