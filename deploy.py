#!/usr/bin/python
#
# $Id: build-websites.py 13345 2013-12-12 22:13:16Z aajain $
#
# Copyright 2011-2011 CoreLogic.
# All rights reserved.
#

"""
Creates a F:\deployjs hierarchy.
"""

import datetime,distutils.archive_util,glob,optparse,os,re,shutil,stat, \
       subprocess,sys, zipfile, os.path, json, socket, fnmatch


def get_config_dir():
  """Gets default src and dst directory for a machine"""
  machine_name = socket.gethostname().upper()
  if(machine_name == "ALMOND"):
    return ("/home/aajain/deploy")
  else:
    return None

def get_configuration(options):
    """Gets configuration for a machine"""
    config = {}

    # Defaults values
    logsettings = {
                   'fileLevel' : 'VERBOSE',
                   'emailLevel' : 'ERROR',
                   'smtpServer' : 'smtp.corelogic.com',
                   'emailSender' : 'logger@corelogic.com',
                   'logFilePath' : os.path.join(options.websites_dir, "log", "spatial.txt")
                 }
    usagedb = {
                'host': 'localhost',
                'user': 'web_user',
                'password': 'w3bus3r',
                'database': 'usagelog'
              }

    webusagedb = {
                'host': 'localhost',
                'user': 'web_user',
                'password': 'w3bus3r',
                'database': 'webusage'
              }


    machine_name = socket.gethostname().upper()

    config["machineName"] = machine_name
    config["appName"] = "spatial"
    config["serverPort"] = 8888
    config["salt"] = "0123456789abcdef"
    config["usageInsertTimeMS"] = 3000  # Insert usagdb record every n millisecond
    config["permissionsCacheTimeMS"] = 10000  #10min to update cache from users
    if(machine_name == "ALMOND"):
        logsettings["emailReceipient"] = 'aajain@corelogic.com'
    elif(machine_name == "BLD01WW72410TP6"):
        logsettings["emailReceipient"] = 'avinueza@corelogic.com'
    else:
        print "ERROR: Configuration for " + computer_name + " not found in"
        print "       " + __file__ + ":get_configuration()"
        print "       Edit %s and add the config for this machine." % __file__
        sys.exit(1)

    config["logsettings"] = logsettings
    config["usagedb"] = usagedb
    config["webusagedb"] = webusagedb

    return config

def minify(options):
  """Minifies all javascript source code. To be used in release mode"""

  dst_dir = os.path.join(options.websites_dir, "gisportal.com")
  if options.verbose:
    print "BUILD: jsmin(%s)" % (dst_dir)

  for root, dirnames, filenames in os.walk(dst_dir):
    for filename in fnmatch.filter(filenames, '*.js'):
      try:
          full_file_path = os.path.join(root, filename)
          subprocess.check_call('jsmin < "%s" > "%s.min"' % (full_file_path, full_file_path), shell=True)
          subprocess.check_call('rm -rf "%s"' % (full_file_path), shell=True)
          subprocess.check_call('mv "%s.min" "%s"' % (full_file_path, full_file_path), shell=True)

      except subprocess.CalledProcessError as e:
        print "ERROR: Error while minifying deployment directory - %s :" % e.message
        sys.exit(1)
      
      

def create_config(options, dst_dir):
    """Create Config.js file to deploy dst dir"""
    file = None
    try:
        config = get_configuration(options)
        file  = open(os.path.join(options.websites_dir, "gisportal.com", "config.js"),"w")
        file.write("//Auto-generated by deploy.py\n\n")
        file.write("//config.js\n")
        file.write("//Configuration file for node.js spatial server\n\n")
        file.write('"use strict";\n\n')
        file.write("var Logger = require('./spatial/lib/common/logger.js');\n\n")
        file.write("var config = \n")
        file.write(json.dumps(config, sort_keys=True,
                    indent=4, separators=(',', ': ')))
        file.write(';\n')
        file.write('var logger = new Logger(config);\n');
        file.write("config.logger = logger;\n\n");
        file.write('module.exports = config;')
    except Exception as e:
        print "ERROR: Writing conig.js file : %s" % e.message
        sys.exit(1)
    finally:
        if file != None:
          file.close()




def mkdir(options, dirname):
    """Create a directory."""
    if options.verbose:
        print "BUILD: mkdir(%s)" % dirname
    os.mkdir(dirname)


def copy_file(options, src, dst):
    """Copy a single file."""
    if options.verbose:
        print "BUILD: copy_file(%s, %s)" % (src, dst)
    # Copy the file, permissions, and times.  copy2 is similar to the
    # Unix command cp -p.
    shutil.copy2(src, dst)


def copy_files(options, src, dst, quiet=False):
    """Copy multiple files specified by a glob."""
    if options.verbose:
        print "BUILD: copy_files(%s, %s)" % (src, dst)
    found = False
    for src_pathname in glob.iglob(src):
        found = True
        shutil.copy2(src_pathname, dst)

    if not found and not quiet:
        print "ERROR: %s not found." % src
        sys.exit(1)


def copy_hier(options, src, dst):
    """Copy a directory hierarchy."""
    if options.verbose:
        print "BUILD: copy_hier(%s, %s)" % (src, dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.md"))

def unzip(options, zip_pathname, dst_dir):
    """Unzip zip zip_pathname to dst_dir."""
    if options.verbose:
        print "BUILD: unzip(%s, %s)" % (zip_pathname, dst_dir)
    try:
        zfile = zipfile.ZipFile(zip_pathname)
        zfile.extractall(dst_dir)
    finally:
        zfile.close()


def copy_spatial(options):
    """Copy spatial director"""
    root_dst_dir = options.websites_dir
    dst_dir = os.path.join(options.websites_dir, "gisportal.com", "spatial");
    src_dir = options.src_dir

    # Copy lib & test to destination spatial folder
    copy_hier(options, os.path.join(src_dir, "lib"), os.path.join(dst_dir, "lib"))
    copy_hier(options, os.path.join(src_dir, "test"), os.path.join(dst_dir, "test"))

    # Copy executable server script
    copy_file(options, os.path.join(src_dir, "server.js"), dst_dir)

    # Copy client script
    mkdir(options, os.path.join(root_dst_dir, "gisportal.com", "client"))
    copy_file(options, os.path.join(src_dir, "client", "client.js"), os.path.join(root_dst_dir, "gisportal.com", "client"))

    # Create a configuration file
    create_config(options, dst_dir)

    # Create log  directory
    mkdir(options, os.path.join(root_dst_dir, "log"))

    # Setup for forever
    # Make .forever file


def main():

    default_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../spatial")
    default_dst_dir = get_config_dir()

    option_parser = optparse.OptionParser(
        usage="usage: %prog [options]\n" +\
            "  Build node.js websites distribution and zipfile.\n" +\
            "  Specify --help to show available options.",
        version="%prog " +"1",
    )
    option_parser.add_option(
        "--verbose",
        action="store_true",
        dest="verbose",
        default=False,
        help="be verbose (default=%default)"
    )

    option_parser.add_option(
        "--release",
        action="store_true",
        dest="release",
        default=False,
        help="minify *.js file in dest dir (default=%default)"
    )

    option_parser.add_option(
        "--src-dir",
        action="store",
        dest="src_dir",
        metavar="DIR",
        default=default_src_dir,
        help="source dir (default=%default)"
    )
    option_parser.add_option(
        "--websites-dir",
        action="store",
        dest="websites_dir",
        metavar="DIR",
        default=default_dst_dir,
        help="destination output dir (default=%default)"
    )
    option_parser.add_option(
        "--no-zip",
        action="store_false",
        dest="zip",
        default=True,
        help="do not create final zipfile"
    )

    (options, args) = option_parser.parse_args()
    
    if(options.websites_dir == None):
      print "ERROR: Either change get_config_dir() function to add your machine default_dst_dir \
              or specify destination folder with --websites-dir"
      return 1;

    options.websites_dir = options.websites_dir.rstrip(r"\/")
    if len(args) != 0:
        option_parser.error("invalid argument")

    # Split websites_dir into parent and leaf parts.
    websites_dir_parent, websites_dir_leaf = os.path.split(
        options.websites_dir
    )

    # Check for the existence of the parent of the destination dir.
    if not os.path.isdir(websites_dir_parent):
        print "ERROR: Parent directory '%s' not found." % websites_dir_parent
        return 1

    # Wipe the root destination directory.
    if os.path.isdir(options.websites_dir):
        if options.verbose:
            print "BUILD: rmtree %s" % options.websites_dir
        shutil.rmtree(options.websites_dir)

    # Copy and build spatial folder
    copy_spatial(options)

    # Minify js files in release mode
    if(options.release):
      minify(options)


if __name__ == '__main__':
    main()
