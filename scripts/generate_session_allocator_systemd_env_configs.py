#!/usr/bin/env python3

from webilastik.config import SessionAllocatorConfig
from webilastik.utility import eprint

config_result = SessionAllocatorConfig.require()
if isinstance(config_result, Exception):
    eprint(f"Could not get session allocator config from environment: {config_result}")
    exit(1)

print(
    "\n".join(v.to_systemd_env_conf() for v in config_result.to_env_vars())
)
