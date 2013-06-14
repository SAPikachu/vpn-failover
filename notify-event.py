#!/usr/bin/env python
from __future__ import print_function

import argparse

from controlclient import ControlClient
import config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("event")
    parser.add_argument("ip")
    args = parser.parse_args()

    client = ControlClient(config.CONTROL_ENDPOINT)
    getattr(client, args.event)(args.ip)


if __name__ == "__main__":
    main()
