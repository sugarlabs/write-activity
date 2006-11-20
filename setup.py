#!/usr/bin/python

# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import os
import zipfile

from sugar.activity.bundle import Bundle

class SvnFileList(list):
	def __init__(self):
		f = os.popen('svn list -R')
		for line in f.readlines():
			filename = line.strip()
			if os.path.isfile(filename):
				self.append(filename)
		f.close()

class GitFileList(list):
	def __init__(self):
		f = os.popen('git-ls-files')
		for line in f.readlines():
			filename = line.strip()
			if not filename.startswith('.'):
				self.append(filename)
		f.close()

def get_source_path():
	return os.path.dirname(os.path.abspath(__file__))

def get_activities_path():
	path = os.path.expanduser('~/Activities')
	if not os.path.isdir(path):
		os.mkdir(path)
	return path

def get_bundle_dir():
	bundle_name = os.path.basename(get_source_path())
	return bundle_name + '.activity'	

def get_bundle_path():
	return os.path.join(get_activities_path(), get_bundle_dir())

def print_help():
	print 'Usage: \n\
setup.py dev     - setup for development \n\
setup.py package - create a bundle package \n\
setup.py help    - print this message \n\
'

def setup_dev():
	bundle_path = get_bundle_path()
	try:
		os.symlink(get_source_path(), bundle_path)
	except OSError:
		if os.path.islink(bundle_path):
			print 'ERROR - The bundle has been already setup for development.'
		else:
			print 'ERROR - A bundle with the same name is already installed.'	

def build_package():
	orig_path = os.getcwd()
	os.chdir(get_source_path())

	if os.path.isdir('.git'):
		file_list = GitFileList()
	elif os.path.isdir('.svn'):
		file_list = SvnFileList()
	else:
		print 'ERROR - The command works only with git or svn repositories.'

	bundle = Bundle(get_source_path())

	zipname = '%s-%d.zip' % (bundle.get_name(), bundle.get_activity_version())
	bundle_zip = zipfile.ZipFile(zipname, 'w')
	
	for filename in file_list:
		arcname = os.path.join(get_bundle_dir(), filename)
		bundle_zip.write(filename, arcname)

	bundle_zip.close()

	os.chdir(orig_path)

if len(sys.argv) < 2 or sys.argv[1] == 'help':
	print_help()
elif sys.argv[1] == 'dev':
	setup_dev()
elif sys.argv[1] == 'package':
	build_package()
