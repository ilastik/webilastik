#!/bin/bash

set -x
set -e
set -u

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cwltool \
        $SCRIPT_DIR/build_package.cwl \
            --major_version 0 \
            --minor_version 1 \
            --package_revision_version 1 \
            --environment_yml $SCRIPT_DIR/../environment.yml \
            --package_tree_template $SCRIPT_DIR/package_tree \
            --webilastik_module_root $SCRIPT_DIR/../webilastik \
