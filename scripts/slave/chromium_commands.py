# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A subclass of commands.SVN that allows more flexible error recovery.

This code is only used on the slave but it is living in common/ because it is
directly imported from buildbot/slave/bot.py."""

import os
import re
import sys

from twisted.python import log
from twisted.internet import defer
from buildbot.slave import commands
from buildbot.slave.registry import registerSlaveCommand

from common import chromium_utils

# Local errors.
class InvalidPath(Exception): pass


def FixDiffLineEnding(diff):
  """Fix patch files generated on windows and applied on mac/linux.

  For files with svn:eol-style=crlf, svn diff puts CRLF in the diff hunk header.
  patch on linux and mac barfs on those hunks. As usual, blame svn."""
  output = ''
  for line in diff.splitlines(True):
    if (line.startswith('---') or line.startswith('+++') or
        line.startswith('@@ ') or line.startswith('\\ No')):
      # Strip any existing CRLF on the header lines
      output += line.rstrip() + '\n'
    else:
      output += line
  return output


class GClient(commands.SourceBase):
  """Source class that handles gclient checkouts.

  In addition to the arguments handled by commands.SourceBase, this command
  reads the following keys:

  ['gclient_spec']:
    if not None, then this specifies the text of the .gclient file to use.
    this overrides any 'svnurl' argument that may also be specified.

  ['rm_timeout']:
    if not None, a different timeout used only for the 'rm -rf' operation in
    doClobber.  Otherwise the svn timeout will be used for that operation too.

  ['svnurl']:
    if not None, then this specifies the svn url to pass to 'gclient config'
    to create a .gclient file.

  ['branch']:
    if not None, then this specifies the module name to pass to 'gclient sync'
    in --revision argument.

  ['env']:
    Augment os.environ.
  """

  header = 'gclient'

  def setup(self, args):
    """Our implementation of command.Commands.setup() method.
    The method will get all the arguments that are passed to remote command
    and is invoked before start() method (that will in turn call doVCUpdate()).
    """
    commands.SourceBase.setup(self, args)
    self.vcexe = commands.getCommand('gclient')
    self.svnurl = args['svnurl']
    self.branch =  args.get('branch')
    self.revision = args.get('revision')
    self.patch = args.get('patch')
    self.sudo_for_remove = args.get('sudo_for_remove')
    self.gclient_spec = args['gclient_spec']
    self.gclient_deps = args.get('gclient_deps')
    self.sourcedata = '%s\n' % self.svnurl
    self.rm_timeout = args.get('rm_timeout', self.timeout)
    self.env = args.get('env')
    self.env['CHROMIUM_GYP_SYNTAX_CHECK'] = '1'

  def start(self):
    """Start the update process.

    start() is cut-and-paste from the base class, the block calling
    self.sourcedirIsPatched() and the revert support is the only functional
    difference from base."""
    self.sendStatus({'header': "starting " + self.header + "\n"})
    self.command = None

    # self.srcdir is where the VC system should put the sources
    if self.mode == "copy":
      self.srcdir = "source" # hardwired directory name, sorry
    else:
      self.srcdir = self.workdir
    self.sourcedatafile = os.path.join(self.builder.basedir,
                                       self.srcdir,
                                       ".buildbot-sourcedata")

    d = defer.succeed(None)
    # Do we need to clobber anything?
    if self.mode in ("copy", "clobber", "export"):
      d.addCallback(self.doClobber, self.workdir)
    was_patched = False
    if not (self.sourcedirIsUpdateable() and self.sourcedataMatches()):
      # the directory cannot be updated, so we have to clobber it.
      # Perhaps the master just changed modes from 'export' to
      # 'update'.
      d.addCallback(self.doClobber, self.srcdir)
    elif self.sourcedirIsPatched():
      # The directory is patched. Revert the sources.
      d.addCallback(self.doRevert)
      was_patched = True

    d.addCallback(self.doVC)

    if self.mode == "copy":
      d.addCallback(self.doCopy)
    if self.patch:
      d.addCallback(self.doPatch)
    if self.patch or was_patched:
      # Always run doRunHooks if there *is* or there *was* a patch because
      # revert is run with --nohooks and `gclient sync` will not regenerate the
      # output files if the input files weren't updated..
      d.addCallback(self.doRunHooks)
    d.addCallbacks(self._sendRC, self._checkAbandoned)
    return d

  def sourcedirIsPatched(self):
    return os.path.exists(os.path.join(self.builder.basedir,
                                       self.srcdir, '.buildbot-patched'))

  def sourcedirIsUpdateable(self):
    # Patched directories are updatable.
    return os.path.exists(os.path.join(self.builder.basedir,
                                       self.srcdir, '.gclient'))

  # TODO(pamg): consolidate these with the copies above.
  def _RemoveDirectoryCommand(self, rm_dir):
    """Returns a command list to delete a directory using Python."""
    # Use / instead of \ in paths to avoid issues with escaping.
    cmd = ['python', '-c',
           'import chromium_utils; '
           'chromium_utils.RemoveDirectory("%s")' % rm_dir.replace('\\', '/')]
    if self.sudo_for_remove:
      cmd = ['sudo'] + cmd
    return cmd

  def _RenameDirectoryCommand(self, src_dir, dest_dir):
    """Returns a command list to rename a directory (or file) using Python."""
    # Use / instead of \ in paths to avoid issues with escaping.
    return ['python', '-c',
            'import os; '
            'os.rename("%s", "%s")' %
                (src_dir.replace('\\', '/'), dest_dir.replace('\\', '/'))]

  def _RemoveFileCommand(self, file):
    """Returns a command list to remove a directory (or file) using Python."""
    # Use / instead of \ in paths to avoid issues with escaping.
    return ['python', '-c',
            'import chromium_utils; '
            'chromium_utils.RemoveFile("%s")' % file.replace('\\', '/')]

  def _RemoveFilesWildCardsCommand(self, file_wildcard):
    """Returns a command list to delete files using Python.

    Due to shell mangling, the path must not be using the character \\."""
    if file_wildcard.find('\\') != -1:
      raise InvalidPath(r"Contains unsupported character '\' :" +
                        file_wildcard)
    return ['python', '-c',
            'import chromium_utils; '
            'chromium_utils.RemoveFilesWildcards("%s")' % file_wildcard]

  def doGclientUpdate(self):
    """Sync the client
    """
    dir = os.path.join(self.builder.basedir, self.srcdir)
    command = [chromium_utils.GetGClientCommand(),
               'sync', '--verbose', '--reset', '--manually_grab_svn_rev',
               '--delete_unversioned_trees']
    # GClient accepts --revision argument of two types 'module@rev' and 'rev'.
    if self.revision:
      command.append('--revision')
      branch = self.branch
      if not branch:
        command.append(str(self.revision))
      else:
        # Make the revision look like branch@revision.
        command.append('%s@%s' % (branch, self.revision))

    if self.gclient_deps:
      command.append('--deps=' + self.gclient_deps)

    c = commands.ShellCommand(self.builder, command, dir,
                              sendRC=False, timeout=self.timeout,
                              keepStdout=True, environ=self.env)
    self.command = c
    return c.start()

  def getGclientConfigCommand(self):
    """Return the command to run the gclient config step.
    """
    dir = os.path.join(self.builder.basedir, self.srcdir)
    command = [chromium_utils.GetGClientCommand(), 'config']

    if self.gclient_spec:
      command.append('--spec=%s' % self.gclient_spec)
    else:
      command.append(self.svnurl)

    c = commands.ShellCommand(self.builder, command, dir,
                              sendRC=False, timeout=self.timeout,
                              keepStdout=True, environ=self.env)
    return c

  def doVCUpdate(self):
    """Sync the client
    """
    # Make sure the .gclient is updated.
    os.remove(os.path.join(self.builder.basedir, self.srcdir, '.gclient'))
    c = self.getGclientConfigCommand()
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    d.addCallback(lambda _: self.doGclientUpdate())
    return d

  def doVCFull(self):
    """Setup the .gclient file and then sync
    """
    dir = os.path.join(self.builder.basedir, self.srcdir)
    os.mkdir(dir)

    c = self.getGclientConfigCommand()
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    d.addCallback(lambda _: self.doGclientUpdate())
    return d

  def doClobber(self, dummy, dirname):
    """Move the old directory aside, or delete it if that's already been done.

    This function is designed to be used with a source dir.  If it's called
    with anything else, the caller will need to be sure to clean up the
    <dirname>.dead directory once it's no longer needed.

    If this is the first time we're clobbering since we last finished a
    successful update or checkout, move the old directory aside so a human
    can try to recover from it if desired.  Otherwise -- if such a backup
    directory already exists, because this isn't the first retry -- just
    remove the old directory.

    Args:
      dummy: unused
      dirname: the directory within self.builder.basedir to be clobbered
    """
    old_dir = os.path.join(self.builder.basedir, dirname)
    dead_dir = old_dir + '.dead'
    if os.path.isdir(old_dir):
      if os.path.isdir(dead_dir):
        command = self._RemoveDirectoryCommand(old_dir)
      else:
        command = self._RenameDirectoryCommand(old_dir, dead_dir)
      c = commands.ShellCommand(self.builder, command, self.builder.basedir,
                                sendRC=0, timeout=self.rm_timeout,
                                environ=self.env)
      self.command = c
      # See commands.SVN.doClobber for notes about sendRC.
      d = c.start()
      d.addCallback(self._abandonOnFailure)
      return d
    return None

  def doRevert(self, dummy):
    """Revert any modification done by a previous patch.

    This is done in 2 parts to trap potential errors at each step. Note that
    it is assumed that .orig and .rej files will be reverted, e.g. deleted by
    the 'gclient revert' command. If the try bot is configured with
    'global-ignores=*.orig', patch failure will occur."""
    dir = os.path.join(self.builder.basedir, self.srcdir)
    command = [chromium_utils.GetGClientCommand(), 'revert', '--nohooks']
    c = commands.ShellCommand(self.builder, command, dir,
                              sendRC=False, timeout=self.timeout,
                              keepStdout=True, environ=self.env)
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    # Remove patch residues.
    d.addCallback(lambda _: self._doRevertRemoveSignalFile())
    return d

  def _doRevertRemoveSignalFile(self):
    """Removes the file that signals that the checkout is patched.

    Must be called after a revert has been done and the patch residues have
    been removed."""
    command = self._RemoveFileCommand(os.path.join(self.builder.basedir,
                           self.srcdir, '.buildbot-patched'))
    dir = os.path.join(self.builder.basedir, self.srcdir)
    c = commands.ShellCommand(self.builder, command, dir,
                              sendRC=False, timeout=self.timeout,
                              keepStdout=True, environ=self.env)
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    return d

  def doPatch(self, res):
    patchlevel = self.patch[0]
    diff = FixDiffLineEnding(self.patch[1])
    root = None
    if len(self.patch) >= 3:
      root = self.patch[2]
    command = [
        commands.getCommand("patch"),
        '-p%d' % patchlevel,
        '--remove-empty-files',
        '--force',
        '--forward',
    ]
    dir = os.path.join(self.builder.basedir, self.workdir)
    # Mark the directory so we don't try to update it later.
    open(os.path.join(dir, ".buildbot-patched"), "w").write("patched\n")

    # Update 'dir' with the 'root' option. Make sure it is a subdirectory
    # of dir.
    if (root and
        os.path.abspath(os.path.join(dir, root)
                        ).startswith(os.path.abspath(dir))):
      dir = os.path.join(dir, root)

    # Now apply the patch.
    c = commands.ShellCommand(self.builder, command, dir,
                              sendRC=False, timeout=self.timeout,
                              initialStdin=diff, environ=self.env)
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    if diff.find('DEPS') != -1:
      d.addCallback(self.doVCUpdateOnPatch)
      d.addCallback(self._abandonOnFailure)
    return d

  def doVCUpdateOnPatch(self, res):
    if self.revision and not self.branch:
      self.branch = 'src'
    return self.doVCUpdate()

  def doRunHooks(self, dummy):
    """Runs "gclient runhooks" after patching."""
    dir = os.path.join(self.builder.basedir, self.srcdir)
    command = [chromium_utils.GetGClientCommand(), 'runhooks']
    c = commands.ShellCommand(self.builder, command, dir,
                              sendRC=False, timeout=self.timeout,
                              keepStdout=True, environ=self.env)
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    return d

  def writeSourcedata(self, res):
    """Write the sourcedata file and remove any dead source directory."""
    dead_dir = os.path.join(self.builder.basedir, self.srcdir + '.dead')
    if os.path.isdir(dead_dir):
      msg = 'Removing dead source dir'
      self.sendStatus({'header': msg + '\n'})
      log.msg(msg)
      command = self._RemoveDirectoryCommand(dead_dir)
      c = commands.ShellCommand(self.builder, command, self.builder.basedir,
                                sendRC=0, timeout=self.rm_timeout,
                                environ=self.env)
      self.command = c
      d = c.start()
      d.addCallback(self._abandonOnFailure)
    open(self.sourcedatafile, 'w').write(self.sourcedata)
    return res

  def parseGotRevision(self):
    """Extract the Chromium and WebKit revision numbers from the svn output.

    svn checkout operations finish with 'Checked out revision 16657.'
    svn update operations finish the line 'At revision 16654.' when there
    is no change. They finish with 'Updated to revision 16655.' otherwise.

    A tuple of the two revisions is always returned, although either or both
    may be None if they could not be found.
    """
    SVN_REVISION_RE = re.compile(
        r'^(Checked out|At|Updated to) revision ([0-9]+)\.')
    def findRevisionNumber(line):
      m = SVN_REVISION_RE.search(line)
      if m:
        return int(m.group(2))
      return None

    WEBKIT_UPDATE_RE = re.compile(
        r'svn (checkout|update) .*src/third_party/WebKit/WebCore ')
    def findWebKitUpdate(line):
      return WEBKIT_UPDATE_RE.search(line)

    chromium_revision = None
    webkit_revision = None
    found_webkit_update = False

    for line in self.command.stdout.splitlines():
      revision = findRevisionNumber(line)
      if revision:
        if not found_webkit_update and not chromium_revision:
          chromium_revision = revision
        elif found_webkit_update and not webkit_revision:
          webkit_revision = revision

      # No revision number found, look for the svn update for WebKit.
      elif not found_webkit_update:
        found_webkit_update = findWebKitUpdate(line)

      # Exit if we're done.
      if chromium_revision and webkit_revision:
        break

    return chromium_revision, webkit_revision

  def _handleGotRevision(self, res):
    """Send parseGotRevision() return values as status updates to the master."""
    d = defer.maybeDeferred(self.parseGotRevision)
    def sendStatusUpdatesToMaster(revisions):
      chromium_revision, webkit_revision = revisions
      self.sendStatus({'got_revision': chromium_revision})
      self.sendStatus({'got_webkit_revision': webkit_revision})
    d.addCallback(sendStatusUpdatesToMaster)
    return d

  def maybeDoVCFallback(self, rc):
    """Called after doVCUpdate."""
    if type(rc) is int and rc == 2:
      # Non-VC failure, return 2 to turn the step red.
      return rc

    # super
    return commands.SourceBase.maybeDoVCFallback(self, rc)

  def maybeDoVCRetry(self, res):
    """Called after doVCFull."""
    if type(res) is int and res == 2:
      # Non-VC failure, return 2 to turn the step red.
      return res

    # super
    return commands.SourceBase.maybeDoVCRetry(self, res)


try:
  # We run this code in a try because it fails with an assertion if
  # the module is loaded twice.
  registerSlaveCommand('gclient', GClient, commands.command_version)
except AssertionError:
  pass
