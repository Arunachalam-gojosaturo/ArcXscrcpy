#!/usr/bin/env python3
"""
ARC-LINK Privileged Sniffer Helper.
Executes with root privileges via polkit/pkexec to capture hotspot packets
using Scapy, serializing packet records as newline-delimited JSON on stdout.
"""

import datetime
import json
import os
import signal
import sys

try:
    from scapy.all import IP, TCP, UDP, ICMP, sniff
except ImportError:
    sys.stderr.write("Scapy not found. Install python-scapy.\n")
    sys.exit(1)


def signal_handler(sig, frame):
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def packet_handler(pkt):
    if not pkt.haslayer(IP):
        return

    ip = pkt[IP]
    proto = "OTHER"
    summary = pkt.summary()

    if pkt.haslayer(TCP):
        proto = "TCP"
        tcp = pkt[TCP]
        flags = tcp.flags
        summary = f"{tcp.sport} -> {tcp.dport} [{flags}]"
    elif pkt.haslayer(UDP):
        proto = "UDP"
        udp = pkt[UDP]
        summary = f"{udp.sport} -> {udp.dport} Len={udp.len}"
    elif pkt.haslayer(ICMP):
        proto = "ICMP"
        icmp = pkt[ICMP]
        summary = f"Type={icmp.type} Code={icmp.code}"

    now_str = datetime.datetime.fromtimestamp(float(pkt.time)).strftime("%H:%M:%S.%f")[:-3]

    record = {
        "time": now_str,
        "src": ip.src,
        "dst": ip.dst,
        "proto": proto,
        "length": len(pkt),
        "summary": summary,
    }

    try:
        sys.stdout.write(json.dumps(record) + "\n")
        sys.stdout.flush()
    except (BrokenPipeError, IOError):
        sys.exit(0)


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: arc-link-sniffer <interface> [target_ip]\n")
        sys.exit(1)

    iface = sys.argv[1]
    target_ip = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "0.0.0.0" else None

    bpf_filter = f"host {target_ip}" if target_ip else "ip"

    try:
        sniff(
            iface=iface,
            filter=bpf_filter,
            prn=packet_handler,
            store=False,
        )
    except Exception as e:
        sys.stderr.write(f"Sniffer error on {iface}: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
