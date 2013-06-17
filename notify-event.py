#!/usr/bin/env python
from __future__ import print_function

import argparse

from controlclient import ControlClient
import config


def pairs(value):
    if not value:
        return {}

    return {
        k: v for k, v in (
            x.split("=") for x in value.split(":")
        )
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("event")
    parser.add_argument("ip")
    parser.add_argument("--timeout", type=int, default=500)
    parser.add_argument("--extra-args", type=pairs)
    args = parser.parse_args()

    client = ControlClient(config.CONTROL_ENDPOINT, resp_timeout=args.timeout)
    getattr(client, args.event)(args.ip, **(args.extra_args or {}))


if __name__ == "__main__":
    main()
