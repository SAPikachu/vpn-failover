#!/usr/bin/env python
from __future__ import print_function

import os
from time import time
from collections import deque
from itertools import islice
import logging
import subprocess
import random
import argparse

import pyping

import config
from controlserver import ControlServer

DEAD = 0x7fffffff


def ping(ip):
    # Packet size must be 0, otherwise timeout rate may rise significantly
    result = pyping.ping(
        ip, count=1, timeout=config.PING_TIMEOUT * 1000,
        packet_size=0, own_id=random.randrange(0xffff),
    )
    rtt = float(result.avg_rtt) / 1000 if result.avg_rtt else None

    logging.debug("Ping: %s, %s", ip, rtt if rtt else "timeout")
    return rtt


def calc_score(samples):
    if len([x for x in islice(samples, config.DEAD_SAMPLES) if x is None]) > \
            config.DEAD_THRESHOLD:
        return DEAD

    return sum(int(x * config.SCORE_SCALE) if x is not None
               else config.TIMEOUT_SCORE
               for x in samples) / len(samples)


class Daemon(ControlServer):
    def __init__(self):
        os.umask(0o177)
        super(Daemon, self).__init__(config.CONTROL_ENDPOINT)
        self.vpns = set()
        self.changed = False
        self.active_vpn = None

    def vpn_up(self, ip):
        logging.info("Got message: VPN up: " + ip)
        self.vpns.add(ip)
        self.changed = True

    def vpn_down(self, ip):
        logging.info("Got message: VPN down: " + ip)
        self.vpns.discard(ip)
        self.changed = True

    def vpn_switch(self, ip):
        logging.info("Got message: VPN switch: " + ip)
        if ip not in self.vpns:
            logging.warning(
                "Invalid VPN switch message: IP {} is not in VPN list".
                format(ip)
            )
            return

        self.active_vpn = ip

    def _main(self):
        ping_samples = {}
        while True:
            start = time()
            scores = {}
            for ip in self.vpns:
                ping_samples[ip].appendleft(ping(ip))
                scores[ip] = calc_score(ping_samples[ip])

            sorted_scores = list(sorted(scores.items(), key=lambda x: x[1]))
            best_vpn, best_score = (sorted_scores[0] if sorted_scores
                                    else (None, DEAD))
            active_score = scores[self.active_vpn] if self.active_vpn else DEAD
            logging.debug("active_score: %s, best_score: %s",
                          active_score, best_score,)
            if active_score > best_score * config.SWITCH_THRESHOLD:
                self.active_vpn = best_vpn
                reason = "dead" if active_score == DEAD else "slow"
                logging.info("VPN switch: %s, reason: %s", best_vpn, reason)
                subprocess.Popen(config.SWITCH_CMD.format(
                    ip=best_vpn,
                    reason=reason,
                ).split(" "))

            while True:
                remaining_time = config.PING_INTERVAL - (time() - start)
                self.handle_requests(max(0, remaining_time) * 1000)
                if time() - start >= config.PING_INTERVAL:
                    break

            if self.changed:
                [ping_samples.pop(x) for x in list(ping_samples.keys())
                    if x not in self.vpns]
                [ping_samples.setdefault(
                    x, deque(maxlen=config.MAX_PING_SAMPLES),
                ) for x in self.vpns if x not in ping_samples]
                if self.active_vpn not in ping_samples:
                    self.active_vpn = None

                self.changed = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)
    Daemon()._main()
