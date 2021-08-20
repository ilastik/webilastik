#!/usr/bin/env cwl-runner

cwlVersion: v1.1
class: CommandLineTool

$namespaces:
  cwltool:
    "http://commonwl.org/cwltool#"
hints:
  cwltool:LoadListingRequirement:
    loadListing: no_listing

baseCommand: bash
arguments: ["create_deb.sh"]

requirements:
  InitialWorkDirRequirement:
    listing:
      - entryname: create_deb.sh
        entry: |-
          set -x
          set -u
          set -e

          PACKAGE_VERSION="\$(grep -E '^Version:' $(inputs.package_tree.path)/DEBIAN/control | cut -d ' ' -f2)"

          cp -rHT $(inputs.package_tree.path) webilastik_package_tree
          dpkg-deb --build webilastik_package_tree webilastik_\${PACKAGE_VERSION}.deb

inputs:
  package_tree: {type: Directory}

outputs:
  deb_package:
    type: File
    outputBinding:
      glob: "*.deb"
