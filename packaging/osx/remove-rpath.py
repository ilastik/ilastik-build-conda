#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import re
import subprocess
import collections
from itertools import groupby

from read_rpaths import read_rpaths, read_dylib_id

install_name_rgx = re.compile(r'\t(.*) \(.*\)')
def remove_rpath( dylib_path, make_relative_to='loader_path', executable_path=sys.executable ):
    """
    For the given dylib, inspect the output of "otool -L" and use install_name_tool to replace 
    all references to @rpath with a new relative path beginning with either @loader_path 
    or @executable_path, as specified by the 'relative_to' parameter.

    (The correct replacement strings are found by inspecting the LC_RPATH entries in "otool -l"
    and searching those paths for the referenced libraries.)
    
    Lastly, the LC_RPATH entries are deleted.
    
    Motivation: What's wrong with keeping @rpath?
                Nothing, in principle, except for the following minor points:
                - It isn't supported in old versions of OSX
                - It adds a level of indirection that can make it tricky to debug linking problems.
                - I'm not 100% sure that py2app handles @rpath correctly when building a bundle.
    """
    assert make_relative_to in ['loader_path', 'executable_path']
    try:
        otool_output = subprocess.check_output("otool -L " + dylib_path, shell=True)
    except subprocess.CalledProcessError as ex:
        sys.stderr.write("Error {} while calling otool -L {}".format( ex.returncode, dylib_path ) )
        raise
    else:
        dylib_id = read_dylib_id( dylib_path )
        raw_rpaths = read_rpaths( dylib_path )
        if raw_rpaths:
            print("*** Removing rpath from: {}".format(dylib_path))

        abs_rpaths = map( lambda rpath: rpath.replace( '@loader_path', os.path.split(dylib_path)[0] ),
                          raw_rpaths )

        if make_relative_to == 'executable_path':
            if not os.path.isdir(executable_path):
                executable_path = os.path.split(executable_path)[0]

            relative_rpaths = map( lambda rpath: os.path.relpath( rpath, executable_path ),
                                   abs_rpaths )

            rpath_replacements = map( lambda rpath: "@executable_path/" + rpath,
                                      relative_rpaths )
        else:
            relative_rpaths = map( lambda rpath: os.path.relpath( rpath, os.path.split(dylib_path)[0] ),
                                   abs_rpaths )

            rpath_replacements = map( lambda rpath: "@loader_path/" + rpath,
                                      relative_rpaths )


        for line in otool_output.split('\n')[1:]:
            if not line:
                continue
            match = install_name_rgx.match(line)
            assert match, "Can't parse line: {}".format( line )
            old_install_name = match.group(1)
            if old_install_name.startswith("@rpath"):
                if dylib_id and dylib_id in old_install_name:
                    cmd = "install_name_tool -id {} {}".format( os.path.split(dylib_id)[1], dylib_path )
                    print(cmd)
                    subprocess.check_call(cmd, shell=True)
                    continue
                
                found_file = False
                for abs_rpath, rpath_replacement in zip(abs_rpaths, rpath_replacements):
                    new_install_name = old_install_name.replace("@rpath", rpath_replacement)
                    if os.path.exists(abs_rpath):
                        cmd = "install_name_tool -change {} {} {}".format( old_install_name, new_install_name, dylib_path )
                        print(cmd)
                        subprocess.check_call(cmd, shell=True)
                        found_file = True
                        break
                if not found_file:
                    raise Exception( "{}, linked from {} does not exist on rpaths: {}"
                                     .format( old_install_name, dylib_path, raw_rpaths ) )
        
        # Lastly remove the LC_RPATH commands
        for rpath in raw_rpaths:
            cmd ="install_name_tool -delete_rpath {} {}".format( rpath, dylib_path )
            print(cmd)
            subprocess.check_call(cmd, shell=True)
                    
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-e","--with_executable_path", required=False)
    parser.add_argument("-l","--with_loader_path", action='store_true')
    parser.add_argument("dylib_paths", nargs="+")
    parsed_args = parser.parse_args()

    if parsed_args.with_executable_path and parsed_args.with_loader_path:
        sys.stderr.write("Options -e and -l cannot be used together.  Choose one.\n")
        sys.exit(1)

    if not parsed_args.with_executable_path and not parsed_args.with_loader_path:
        parsed_args.with_executable_path = sys.executable
        print("Assuming python for default --executable_path={}".format(parsed_args.executable_path))

    if parsed_args.with_loader_path:
        relative_to='loader_path'
    else:
        relative_to='executable_path'

    for dylib_path in parsed_args.dylib_paths:
        remove_rpath( dylib_path, relative_to, parsed_args.with_executable_path )
