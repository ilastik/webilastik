#!/usr/bin/bash

set -uxe

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

sudo mkdir -p /etc/systemd/system/webilastik@.service.d
sudo sh -c "echo '
[Service]
TTYPath=$(tty)
StandardOutput=tty
StandardError=inherit
' > /etc/systemd/system/webilastik@.service.d/output_to_tty.conf"

sudo systemctl daemon-reload
echo "Don't forget to restart webilasitk!"