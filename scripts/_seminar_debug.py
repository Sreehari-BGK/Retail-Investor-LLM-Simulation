#!/usr/bin/env python3
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

src = open('scripts/curate_and_freeze.py', encoding='utf-8').read()
start = src.index('THREAD_DECISIONS = [')
depth = 0
for i, ch in enumerate(src[start:], start):
    if ch == '[': depth += 1
    elif ch == ']': depth -= 1
    if depth == 0:
        end = i + 1
        break
sl = src[start:end]
print('start:', start, 'end:', end, 'len(sl):', len(sl))
print('first 50:', repr(sl[:50]))
print('last 50:', repr(sl[-50:]))
print('has equals?', '=' in sl)
