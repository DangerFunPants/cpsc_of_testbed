
import pathlib      as path

# Root directory for solver inputs and outputs.
INPUT_FILE_DIR          = path.Path("/home/cpsc-net-user/repos/flow-mirroring-scheme/")

# Path to the file containing the topology given to the solver.
target_topo_path        = INPUT_FILE_DIR.joinpath("network/topo")

# Path to the file containing randomly generated flow defintions
flow_file_path          = INPUT_FILE_DIR.joinpath("network/flows")

# Path to the file containing the list of nodes in the network.
switch_file_path        = INPUT_FILE_DIR.joinpath("network/switches")

# Path to the solutions file containing the mirroring ports for each of the flows.
solution_file_path      = INPUT_FILE_DIR.joinpath("solutions/opt")

# Duration of a single trial in seconds.
trial_length            = 60

# IP Address of the collector machine
collector_ip_addr       = "10.10.0.18"

# Root directory of the results repository
base_repository_path    = path.Path("/home/cpsc-net-user/repos/flow-mirroring-results/")

# Schema string for the repository
repository_schema       = "/trial-name/"

# Name of the repository
repository_name         = "flow-mirroring"
