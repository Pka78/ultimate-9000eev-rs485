#!/usr/bin/env python3
"""Linux receive-only serial capture. Never opens the serial device for writing."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import select
import sys
import termios
import time


def configure(fd, baud, parity, stops):
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0  # Preserve all received bytes; do not translate CR or strip bit 7.
    attrs[1] = 0
    attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8
    if parity != 'N':
        attrs[2] |= termios.PARENB
        if parity == 'O':
            attrs[2] |= termios.PARODD
    if stops == 2:
        attrs[2] |= termios.CSTOPB
    attrs[3] = 0  # No echo: received bytes must never be transmitted back.
    attrs[4] = attrs[5] = getattr(termios, 'B' + str(baud))
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('device', help='/dev/serial/by-id/... (use the selected channel)')
    ap.add_argument('--baud', type=int, default=9600)
    ap.add_argument('--parity', choices=['N', 'E', 'O'], default='N')
    ap.add_argument('--stops', type=int, choices=[1, 2], default=1)
    ap.add_argument('--output', type=Path, required=True, help='New session directory')
    ap.add_argument('--seconds', type=float, default=0, help='0: until Ctrl-C')
    args = ap.parse_args()
    if not hasattr(termios, 'B' + str(args.baud)):
        ap.error('Unsupported baud rate')
    args.output.mkdir(parents=True, exist_ok=False)
    fd = os.open(args.device, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    old = termios.tcgetattr(fd)
    try:
        configure(fd, args.baud, args.parity, args.stops)
        actual = termios.tcgetattr(fd)
        wanted = termios.tcgetattr(fd)[2]
        expected = (termios.PARENB if args.parity != 'N' else 0) | (termios.PARODD if args.parity == 'O' else 0) | (termios.CSTOPB if args.stops == 2 else 0)
        if wanted & (termios.PARENB | termios.PARODD | termios.CSTOPB) != expected:
            raise RuntimeError('Driver did not retain requested parity/stop settings')
        start = time.monotonic_ns()
        offset = 0
        metadata = vars(args).copy()
        metadata.update(output=str(args.output), started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), termios_cflag=actual[2], receive_only=True)
        (args.output / 'session.json').write_text(json.dumps(metadata, indent=2) + '\n')
        print('Receiving only. Type event descriptions + Enter; Ctrl-C stops.', flush=True)
        print('Chunks are USB read batches, NOT protocol frames.', flush=True)
        watch_stdin = sys.stdin.isatty()
        with (args.output / 'raw.bin').open('xb') as raw, (args.output / 'events.jsonl').open('x') as events:
            def record(kind, **values):
                row = dict(kind=kind, utc=dt.datetime.now(dt.timezone.utc).isoformat(), elapsed_ns=time.monotonic_ns()-start, **values)
                events.write(json.dumps(row, ensure_ascii=False) + '\n')
                events.flush()
            try:
                while not args.seconds or (time.monotonic_ns()-start)/1e9 < args.seconds:
                    ready, _, _ = select.select([fd] + ([sys.stdin] if watch_stdin else []), [], [], 0.1)
                    if fd in ready:
                        chunk = os.read(fd, 4096)
                        if chunk:
                            raw.write(chunk)
                            raw.flush()
                            record('rx', offset=offset, length=len(chunk), hex=chunk.hex())
                            offset += len(chunk)
                            print(f'{offset:8d} bytes | {chunk.hex(" ")}', flush=True)
                    if watch_stdin and sys.stdin in ready:
                        line = sys.stdin.readline()
                        if not line:
                            watch_stdin = False
                        else:
                            record('marker', text=line.strip())
            except KeyboardInterrupt:
                pass
            finally:
                record('stop', total_bytes=offset)
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old)
        os.close(fd)


if __name__ == '__main__':
    main()
