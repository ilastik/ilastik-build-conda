#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import re
import subprocess

from read_rpaths import read_rpaths, read_dylib_id

def main():
    """
    Example usage:

    # Print the dependencies of one shared object:
    $ python find-dependencies.py --subtree=/miniconda/envs/ilastik-release /miniconda/envs/ilastik-release/lib/python2.7/site-packages/pgmlink.so
    
    # Print dependencies of all python extension modules:
    $ find /miniconda/envs/ilastik-release/lib/python2.7 -name "*.so" \
        | xargs python find-dependencies.py --subtree=/miniconda/envs/ilastik-release \
        > all-python-module-dependencies
    """
    import argparse
    parser = argparse.ArgumentParser("Find all dependencies of a set of dylib/so files.")
    parser.add_argument("--subtree", help="Paths outside of this tree will be excluded from the output.", required=False)
    parser.add_argument("dylibs", nargs='+')
    parsed_args = parser.parse_args()
    
    dependencies = get_all_dependencies( parsed_args.dylibs, parsed_args.subtree )    
    for p in sorted( dependencies ):
        print(p)

def get_all_dependencies( dylib_paths, subtree=None ):
    """
    Find all the dependencies needed for the given list of dylibs, including symbolic links.
    The 'subtree' param is a directory. If provided, exclude any files that do not reside in that directory tree.
    """
    dependencies = set()
    excluded_set = set()
    subtree = subtree and os.path.abspath( subtree )
    for dylib_path in dylib_paths:
        _accumulate_dependencies( dylib_path, dependencies, subtree, excluded_set )
    return dependencies

def _accumulate_dependencies( dylib_path, existing_dependencies, subtree, excluded_set ):
    """
    Recursive helper function for get_all_dependencies(). 
    """
    if (dylib_path in existing_dependencies
        or dylib_path in excluded_set):
        return
    
    if subtree and not dylib_path.startswith(subtree):
        sys.stderr.write("Excluding {}\n".format( dylib_path ))
        excluded_set.add( os.path.normpath(dylib_path) )
        return

    links, abs_dylib_path = follow_links(dylib_path)
    existing_dependencies.update(links)
    existing_dependencies.add(abs_dylib_path)

    dylib_dependencies = get_dependencies(abs_dylib_path)
    for dependency in dylib_dependencies:
        _accumulate_dependencies( dependency, existing_dependencies, subtree, excluded_set )

install_name_rgx = re.compile(r'\t(.*) \(.*\)')
def get_dependencies( dylib_path, executable_path=sys.executable ):
    """
    Return the list of dependencies for the given dylib, as listed by `otool -L`.
    All returned paths will be absolute, and the list may include symbolic links.
    """
    try:
        otool_output = subprocess.check_output("otool -L " + dylib_path, shell=True)
    except subprocess.CalledProcessError as ex:
        sys.stderr.write("Error {} while calling otool -L {}\n".format( ex.returncode, dylib_path ) )
        raise

    dylib_id = read_dylib_id( dylib_path )
    raw_rpaths = read_rpaths( dylib_path )
    abs_rpaths = map( lambda rpath: rpath.replace( '@loader_path', os.path.split(dylib_path)[0] ),
                      raw_rpaths )

    dependencies = []
    for line in otool_output.split('\n')[1:]:
        if not line:
            continue
        match = install_name_rgx.match(line)
        assert match, "Can't parse line: {}".format( line )
        dylib_install_name = match.group(1)
        
        if dylib_id and dylib_id in dylib_install_name:
            # Skip the id line for the dylib itself.
            continue

        abs_dylib_path = None
        if dylib_install_name.startswith('@loader_path'):
            abs_dylib_path = dylib_install_name.replace('@loader_path', os.path.split(dylib_path)[0])
        elif dylib_install_name.startswith('@executable_path'):
            abs_dylib_path = dylib_install_name.replace('@executable_path', os.path.split(executable_path)[0])
        elif dylib_install_name.startswith("@rpath"):            
            for abs_rpath in abs_rpaths:
                possible_abspath = dylib_install_name.replace("@rpath", abs_rpath)
                if os.path.exists(possible_abspath):
                    abs_dylib_path = possible_abspath
                    break
        elif os.path.isabs(dylib_install_name):
            abs_dylib_path = dylib_install_name
        else:
            # TODO: We don't yet handle relative paths that don't use @loader_path, @rpath, etc.
            # For non-absolute install names, we would have to check DYLD_LIBRARY_PATH, DYLD_FALLBACK_LIBRARY_PATH, etc.
            # This is probably where we should be using the macholib package instead of this custom hack.
            sys.stderr.write("*** Can't handle relative install-name in {}: {}\n".format( dylib_path, dylib_install_name ))
            #raise Exception("Can't handle relative install-name in {}: {}\n".format( dylib_path, dylib_install_name ))
            
        if not abs_dylib_path or not os.path.exists(abs_dylib_path):
            sys.stderr.write("*** Dependency of {} does not exist: {}\n".format( dylib_path, dylib_install_name ))
            continue
        
        abs_dylib_path = os.path.normpath(abs_dylib_path)
        dependencies.append( abs_dylib_path )
    return dependencies

def follow_links( abs_file_path ):
    """
    For a given path, which may or may not be a symbolic link,
    return the absolute paths to any links in the chain, and the real file.
    Note: Even though the link *text* may be relative, we return the absolute paths of the symlink files themselves.
    
    For example, consider this case:

    $ ls -l /tmp/
    ... f1.txt@ -> f2.txt
    ... f2.txt@ -> f3.txt
    ... f3.txt
    
    >>> follow_links( '/tmp/f1.txt')
    (['/tmp/f1.txt', '/tmp/f2.txt'], '/tmp/f3.txt')
    """

    linkfile_abspaths = []
    while os.path.islink(abs_file_path):
        linkfile_abspaths.append(abs_file_path)
        link_text = os.readlink(abs_file_path)
        if os.path.isabs(link_text):
            abs_file_path = link_text
        else:
            abs_file_path = os.path.join(os.path.dirname(abs_file_path), link_text)
        if not os.path.exists(abs_file_path):
            raise Exception("File does not exist: " + abs_file_path)
    return linkfile_abspaths, abs_file_path

if __name__ == "__main__":
    main()
