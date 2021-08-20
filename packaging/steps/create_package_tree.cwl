#!/usr/bin/env cwl-runner

cwlVersion: v1.0
class: CommandLineTool

$namespaces:
  cwltool:
    "http://commonwl.org/cwltool#"
hints:
  cwltool:LoadListingRequirement:
    loadListing: no_listing


baseCommand: "bash"
arguments: ["create_package_tree.sh"]

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: create_package_tree.sh
        entry: |-
          set -x
          set -u
          set -e

          PACKAGE_VERSION="$(inputs.major_version).$(inputs.minor_version).$(inputs.package_revision_version)"
          PACKAGE_NAME="webilastik_\$PACKAGE_VERSION"

          cp -rHT $(inputs.package_tree_template.path) \$PACKAGE_NAME

          cat > \${PACKAGE_NAME}/DEBIAN/control <<EOF
          Package: webilastik
          Version: \$PACKAGE_VERSION
          Section: base
          Priority: optional
          Architecture: amd64
          Depends:
          Maintainer: ilastik Team <team@ilastik.org>
          Description: Webilastik
           Server and frontend for the web version of ilastik
          EOF

          tar -xzf $(inputs.packed_conda_environment.path) -C \${PACKAGE_NAME}/opt/webilastik_conda_env

          cp -rHT $(inputs.webilastik_module_root.path) \${PACKAGE_NAME}/opt/webilastik
          find \${PACKAGE_NAME}/opt/webilastik -name __pycache__ | xargs rm -r


inputs:
  major_version: {type: int}
  minor_version: {type: int}
  package_revision_version: {type: int}
  package_tree_template: {type: Directory}
  packed_conda_environment: {type: File}
  webilastik_module_root: {type: Directory}

outputs:
  package_tree:
    type: Directory
    outputBinding:
      glob: webilastik_$(inputs.major_version).$(inputs.minor_version).$(inputs.package_revision_version)
