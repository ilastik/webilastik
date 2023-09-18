# pyright: strict

import sys

class Logger:
    debug_escape = "\033[32m" if sys.stderr.isatty()  else ""
    info_escape =  "\033[34m" if sys.stderr.isatty()  else ""
    warn_escape =  "\033[33m" if sys.stderr.isatty()  else ""
    error_escape = "\033[31m" if sys.stderr.isatty()  else ""
    end_escape =   "\033[0m"  if sys.stderr.isatty()  else ""

    def debug(self, message: str):
        print(f"{self.debug_escape}[DEBUG]{message}{self.end_escape}", file=sys.stderr)

    def info(self, message: str):
        print(f"{self.info_escape}[INFO]{message}{self.end_escape}", file=sys.stderr)

    def warn(self, message: str):
        print(f"{self.warn_escape}[WARNING]{message}{self.end_escape}", file=sys.stderr)

    def error(self, message: str):
        print(f"{self.error_escape}[ERROR]{message}{self.end_escape}", file=sys.stderr)