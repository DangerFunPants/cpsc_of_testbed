
import pathlib              as path
import nw_control.util      as util
import shutil               as shutil
import json                 as json
import pickle               as pickle

from functools              import reduce

# The repository will be rooted at {base_path}.
# When a repository, or a handle to a repository is created, is created a schema is provided.
# Schemas are a sequence of labels whose values are interpolated for particular trial instances.
# The format of the schema string is a unix path where root (/) is the location specified by
# {base_path}
# 
# The behavior of the ResultsRepository differs depending whether a repository at {base_path} already
# exists. If a repository already exists at {base_path} then a handle to the existing 
# repository will be created. If a repository does not exist, one will be created.
# 
# Also need to define an API for accessing the results stored in a repository should be able to reconstruct
# the FlowMirroringTrial object plus the utilization results and allow consumers to load these from 
# a repository handle.
class ResultsRepository:
    REPO_METADATA_FILE = path.Path(".results_repo")
    
    def __init__(self, base_path, schema, repository_name):
        self._base_path         = base_path
        self._schema            = schema
        self._repository_name   = repository_name

    @property
    def base_path(self):
        return self._base_path

    @property
    def schema(self):
        return self._schema

    @property
    def repository_name(self):
        return self._repository_name

    @staticmethod
    def create_repository(base_path, schema, repository_name):
        if ResultsRepository.repository_exists(base_path):
            repository_metadata = ResultsRepository.read_repository_metadata(base_path)
            if (repository_metadata["repository_name"] != repository_name 
                    or repository_metadata["schema"] != schema):
                raise ValueError("Attempting to create repository %s in base directory that contains repository %s" %
                        (repository_name, repository_metadata["repository_name"]))
        else:
            base_path.mkdir(parents=True)
            metadata = { "repository_name"      : repository_name
                       , "schema"               : schema
                       }
            base_path.joinpath(ResultsRepository.REPO_METADATA_FILE).write_text(json.dumps(metadata))

        return ResultsRepository(base_path, schema, repository_name)

    def build_output_path(self, schema_variables):
        output_path_segments = [schema_variables[schema_label] for schema_label in
                self.schema.split("/") if schema_label != ""]
        output_path = reduce(lambda acc, v: acc / path.Path(v), output_path_segments,
                self.base_path)
        return output_path

    def write_trial_results( self
                           , schema_variables
                           , results
                           , overwrite          = False):
        # output_path_segments = [schema_variables[schema_label] for schema_label in 
        #         self.schema.split("/") if schema_label != ""]
        # output_path = reduce(lambda acc, v: acc.joinpath(path.Path(v)), output_path_segments,
        #         self.base_path)
        output_path = self.build_output_path(schema_variables)
        output_path.mkdir(parents=True, exist_ok=overwrite)
        for file_name, results_data in results.items():
            output_file = output_path.joinpath(file_name)
            output_file.write_text(results_data)

    def write_trial_provider( self
                            , schema_variables
                            , trial_provider
                            , overwrite             = False
                            , merge_existing        = False):
        output_path = self.build_output_path(schema_variables)
        output_path.mkdir(parents=True, exist_ok=True)
        provider_output_file = output_path / "trial-provider.p"
        name_intersection = set()
        if provider_output_file.exists():
            with provider_output_file.open("rb") as fd:
                the_existing_provider = pickle.load(fd)
            # Check if we should be overwriting the trial.
            # Are there any trials with identical IDs?
            # Two trials are considered the same if they have the same name. If overwrite 
            # is true then any existing trials with the same name as trials in the new provider
            # will be removed. if trials have identical IDs they will not be overwritten 
            # regardless of the value of the override parameter.
            id_intersection = ({t_i.get_parameter("id") for t_i in the_existing_provider} &
                    {t_j.get_parameter("id") for t_j in trial_provider})
            if (len(id_intersection) != 0):
                raise ValueError("Attempting to overwrite trials with the same ID.")

            name_intersection = ({t_i.get_parameter("trial-name") for t_i in the_existing_provider} &
                    {t_j.get_parameter("trial-name") for t_j in trial_provider})
            if len(name_intersection) != 0 and not overwrite:
                raise ValueError("Attempting to overwrite trials with the same name without specifying overwrite")
            for duplicated_name in name_intersection:
                the_existing_provider.remove_all_trials_that_match(
                        lambda t: t.get_parameter("trial-name") == duplicated_name)

            if merge_existing:
                for t_i in the_existing_provider:
                    trial_provider.add_trial(t_i)

        with provider_output_file.open("wb") as fd:
            pickle.dump(trial_provider, fd)

    def read_trial_results(self, schema_variables, file_names):
        output_path_segments = [schema_variables[schema_label] for schema_label in
                self.schema.split("/") if schema_label != ""]
        output_path = reduce(lambda acc, v: acc.joinpath(path.Path(v)), output_path_segments,
                self.base_path)
        output_files = {}
        for file_name in file_names:
            results_file = output_path.joinpath(file_name)
            file_text = results_file.read_text()
            output_files[file_name] = file_text

        return output_files

    def read_trial_provider(self, provider_name):
        provider_file = self.base_path / provider_name / "trial-provider.p"
        with provider_file.open("rb") as fd:
            trial_provider = pickle.load(fd)
        return trial_provider

    @staticmethod
    def repository_exists(base_path):
        if not base_path.exists() or not base_path.is_dir():
            return False
        files_in_base_path = base_path.iterdir()
        metadata_file = base_path.joinpath(ResultsRepository.REPO_METADATA_FILE)
        return metadata_file in files_in_base_path

    @staticmethod
    def read_repository_metadata(base_path):
        file_path = base_path / ResultsRepository.REPO_METADATA_FILE
        repo_file_json = util.read_json_from_file(file_path)
        return repo_file_json
