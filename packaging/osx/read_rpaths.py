#!/usr/bin/env python
from __future__ import print_function
import sys
import re
import subprocess
import collections
import operator
from itertools import groupby

rpath_rgx = re.compile(' *path (.*) \(offset .*\)')
def read_rpaths( dylib_path ):
    """
    Read all rpath loader commands from the given dylib path and return the path for each.
    """
    commands = read_load_commands( dylib_path )
    rpath_commands = filter(lambda c: c.cmd == "LC_RPATH", commands)

    rpaths = []
    for command in rpath_commands:
        match = rpath_rgx.match(command.lines[3])
        assert match
        rpaths.append( match.group(1) )
    return rpaths

id_rgx = re.compile(' *name (.*) \(offset .*\)')
def read_dylib_id( dylib_path ):
    commands = read_load_commands( dylib_path )
    id_commands = filter(lambda c: c.cmd == "LC_ID_DYLIB", commands)
    if not id_commands:
        return None
    assert len(id_commands) == 1, \
        "Exepected 1 or 0 LC_ID_DYLIB commands, but found {} in {}"\
        .format(len(id_commands), dylib_path) 
    match = id_rgx.match(id_commands[0].lines[3])
    assert match
    return match.group(1)

LoadCommand = collections.namedtuple("LoadCommand", "cmd index lines")
def read_load_commands( dylib_path ):
    """
    Parse the output of 'otool -l' into groups of lines (one for each loader command).
    """
    try:
        otool_output = subprocess.check_output("otool -l " + dylib_path, shell=True)
    except subprocess.CalledProcessError as ex:
        sys.stderr.write("Error {} while calling otool -l {}".format( ex.returncode, dylib_path ) )
        raise
    else:
        lines = otool_output.split('\n')[1:]
        command_starts = [int(line.startswith('Load command')) for line in lines]
        command_indexes = accumulate(command_starts)
        
        commands = []
        for command_index, group in groupby(zip(command_indexes, lines), lambda (i,l): i):
            _, cmd_lines = zip(*group)
            assert cmd_lines[0].startswith("Load command ")
            index = int(cmd_lines[0].split()[2])
            assert cmd_lines[1].strip().startswith("cmd LC_"), cmd_lines
            cmd = cmd_lines[1].split()[1]
            commands.append( LoadCommand(cmd, index, cmd_lines) )
        return commands

def accumulate(iterable, func=operator.add):
    """
    Copied from Python 3 itertools.accumulate() docs.
    """
    it = iter(iterable)
    total = next(it)
    yield total
    for element in it:
        total = func(total, element)
        yield total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("dylib_path")
    parsed_args = parser.parse_args()

    rpaths = read_rpaths( parsed_args.dylib_path )
    for rpath in rpaths:
        print(rpath)
