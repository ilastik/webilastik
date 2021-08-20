#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool

baseCommand: "bash"
arguments: ["create_and_pack_environment.sh"]

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: create_and_pack_environment.sh
        entry: |-
          set -x
          set -u
          set -e

          conda env create --prefix $(runtime.tmpdir)/webilastik_conda_env -f $(inputs.environment_yml.path)
          conda pack -p $(runtime.tmpdir)/webilastik_conda_env

inputs:
  environment_yml: {type: File}

outputs:
  environment:
    type: File
    outputBinding:
      glob: webilastik_conda_env.tar.gz
