#!/bin/bash

# Starts a training session orchestrator, which exposes an API that allocates local training sessions.
# Each new spawned session will ssh back to the orchestrator machine and create a
# reverse tunnel, through which the communication between client and session can take place.
#
# The local sessions mimic the HPC sessions as much as possible, so they will also do the reverse tunnelling even when
# running locally, which means you need sshd running on the local machine and that master-username (e.g.: www-data)
# must be able to login using only ssh keys (e.g. add its key to your ~/.ssh/authorized_keys)
#
# The user from the example is www-data, since we're assuming that the web server (e.g.: nginx) is running as www-data.

set -x
set -u
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

export SESSION_SECRET=123
export PYTHONPATH="$SCRIPT_DIR/..:$SCRIPT_DIR/../ndstructs"
python $SCRIPT_DIR/../webilastik/server/__init__.py \
    --session-type=Local \
    --master-host=localhost \
    --master-username=www-data \
    --external-url=http://dev.web.ilastik.org \
    "$@"
