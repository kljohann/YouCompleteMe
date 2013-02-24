#!/usr/bin/env python
#
# Copyright (C) 2011, 2012  Strahinja Val Markovic  <val@markovic.io>
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import imp
import os
import ycm_core
import random
import string
import sys
import vimsupport

YCM_EXTRA_CONF_FILENAME = '.ycm_extra_conf.py'
NO_EXTRA_CONF_FILENAME_MESSAGE = ('No {0} file detected, so no compile flags '
  'are available. Thus no semantic support for C/C++/ObjC/ObjC++. See the '
  'docs for details.').format( YCM_EXTRA_CONF_FILENAME )
CONFIRM_CONF_FILE_MESSAGE = 'Found {0}. Load?'
GLOBAL_YCM_EXTRA_CONF_FILE = os.path.expanduser(
    vimsupport.GetVariableValue( "g:ycm_global_ycm_extra_conf" )
)

class Flags( object ):
  def __init__( self ):
    # It's caches all the way down...
    self.flags_for_file = {}
    self.flags_module_for_file = {}
    self.flags_module_for_flags_module_file = {}
    self.special_clang_flags = _SpecialClangIncludes()
    self.no_extra_conf_file_warning_posted = False


  def FlagsForFile( self, filename ):
    try:
      return self.flags_for_file[ filename ]
    except KeyError:
      flags_module = self._FlagsModuleForFile( filename )
      if not flags_module:
        if not self.no_extra_conf_file_warning_posted:
          vimsupport.PostVimMessage( NO_EXTRA_CONF_FILENAME_MESSAGE )
          self.no_extra_conf_file_warning_posted = True
        return None

      results = flags_module.FlagsForFile( filename )

      if not results.get( 'flags_ready', True ):
        return None

      results[ 'flags' ] += self.special_clang_flags
      sanitized_flags = _SanitizeFlags( results[ 'flags' ] )

      if results[ 'do_cache' ]:
        self.flags_for_file[ filename ] = sanitized_flags
      return sanitized_flags


  def _FlagsModuleForFile( self, filename ):
    """Return the module that will compute the flags necessary to compile the file.
    This will try all files returned by _FlagsModuleSourceFilesForFile in order
    and optionally ask the user for confirmation before loading.
    If no module was found or allowed to load None is returned."""

    flags_module = self.flags_module_for_file.get( filename )
    if flags_module:
      return flags_module

    for flags_module_file in _FlagsModuleSourceFilesForFile( filename ):
      if not self.flags_module_for_flags_module_file.has_key( flags_module_file ):
        # Ask if we should load this module (don't ask for global config)
        if ( flags_module_file != GLOBAL_YCM_EXTRA_CONF_FILE  and
              vimsupport.GetBoolValue( 'g:ycm_confirm_extra_conf' ) and
              not vimsupport.Confirm(
                CONFIRM_CONF_FILE_MESSAGE.format( flags_module_file ) ) ):
          # Otherwise disable module for this session
          self.flags_module_for_flags_module_file[ flags_module_file ] = None
          continue

        sys.path.insert( 0, _DirectoryOfThisScript() )
        flags_module = imp.load_source( _RandomName(), flags_module_file )
        del sys.path[ 0 ]

        self.flags_module_for_flags_module_file[
          flags_module_file ] = flags_module

      flags_module = self.flags_module_for_flags_module_file[ flags_module_file ]
      # Return first model we were allowed to load
      if flags_module:
        self.flags_module_for_file[ filename ] = flags_module
        return flags_module

    return None


def _FlagsModuleSourceFilesForFile( filename ):
  """For a given filename, search all parent folders for YCM_EXTRA_CONF_FILENAME
  files that will compute the flags necessary to compile the file.
  If GLOBAL_YCM_EXTRA_CONF_FILE exists it is returned as a fallback."""
  for folder in _PathsToAllParentFolders( filename ):
    candidate = os.path.join( folder, YCM_EXTRA_CONF_FILENAME )
    if os.path.exists( candidate ):
      yield candidate
  if ( GLOBAL_YCM_EXTRA_CONF_FILE and os.path.exists( GLOBAL_YCM_EXTRA_CONF_FILE ) ):
    yield GLOBAL_YCM_EXTRA_CONF_FILE


def _PathsToAllParentFolders( filename ):
  """Build a list of all parent folders of a file.
  The neares files will be returned first.
  Example: _PathsToAllParentFolders( '/home/user/projects/test/test.c' )
    [ '/home/user/projects/test', '/home/user/projects', '/home/user', '/home', '/' ]"""
  parent_folders = os.path.abspath( os.path.dirname( filename ) ).split( os.path.sep )
  if not parent_folders[0]:
    parent_folders[0] = os.path.sep
  parent_folders = [ os.path.join( *parent_folders[:i + 1] )
                     for i in xrange( len( parent_folders ) ) ]
  return reversed( parent_folders )


def _RandomName():
  """Generates a random module name."""
  return ''.join( random.choice( string.ascii_lowercase ) for x in range( 15 ) )


def _SanitizeFlags( flags ):
  """Drops unsafe flags. Currently these are only -arch flags; they tend to
  crash libclang."""

  sanitized_flags = []
  saw_arch = False
  for i, flag in enumerate( flags ):
    if flag == '-arch':
      saw_arch = True
      continue
    elif flag.startswith( '-arch' ):
      continue
    elif saw_arch:
      saw_arch = False
      continue

    sanitized_flags.append( flag )

  vector = ycm_core.StringVec()
  for flag in sanitized_flags:
    vector.append( flag )
  return vector


def _SpecialClangIncludes():
  libclang_dir = os.path.dirname( ycm_core.__file__ )
  path_to_includes = os.path.join( libclang_dir, 'clang_includes' )
  return [ '-I', path_to_includes ]


def _DirectoryOfThisScript():
  return os.path.dirname( os.path.abspath( __file__ ) )
