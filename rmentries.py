#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2021  The SymbiFlow Authors.
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC
""" Remove a range of test run entries """

import os
import re
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('meta_dir', type=str)
parser.add_argument('from_no', type=int)
parser.add_argument('to_no', type=int)

args = parser.parse_args()

if not os.path.isdir(args.meta_dir):
    print('`meta_dir` has to be a valid directory path')
    exit(-1)

for subdir in os.listdir(args.meta_dir):
    subdir = os.path.join(args.meta_dir, subdir)
    if not os.path.isdir(subdir):
        continue

    for fpath in os.listdir(subdir):
        m = re.match('meta-([0-9]*)\\.json', fpath)
        if m:
            fpath = os.path.join(subdir, fpath)
            no = int(m.groups()[0])
            if (no >= args.from_no) and (no <= args.to_no):
                os.remove(fpath)
