#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: Workflow

$namespaces:
  cwltool:
    "http://commonwl.org/cwltool#"
hints:
  cwltool:LoadListingRequirement:
    loadListing: no_listing

inputs:
  environment_yml: {type: File}

  major_version: {type: int}
  minor_version: {type: int}
  package_revision_version: {type: int}
  package_tree_template: {type: Directory}
  webilastik_module_root: {type: Directory}

outputs:
    deb_package:
        type: File
        outputSource: create_deb/deb_package

steps:
  create_conda_environment:
    run: steps/create_conda_environment.cwl
    in:
        environment_yml: environment_yml
    out: [environment]

  create_package_tree:
    run: steps/create_package_tree.cwl
    in:
      major_version: major_version
      minor_version: minor_version
      package_revision_version: package_revision_version

      package_tree_template: package_tree_template
      packed_conda_environment: create_conda_environment/environment
      webilastik_module_root: webilastik_module_root
    out:
      [package_tree]

  create_deb:
    run: steps/create_deb.cwl
    in:
      package_tree: create_package_tree/package_tree
    out:
      [deb_package]
