# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Provides classes for managing android gce instances."""

import datetime
import logging
import psutil
import re
import subprocess

import googleapiclient.errors

# Default adbd port
_ADBD_PORT = 5555

# Configuration properties for the android instances
_MACHINE_TYPE = 'n1-standard-2'
_INSTANCE_PROPERTIES = {
    'cfg_sta_initial_locale': 'en_US',
    'cfg_sta_ephemeral_data_size_mb': '4096',
    'cfg_sta_data_preimage_device': '/dev/block/sda2',
    'cfg_sta_ephemeral_cache_size_mb': '512',
    'cfg_sta_display_resolution': '800x1280x16x150',
}


def build_instance_properties(p):
    res = []
    for k, v in p.iteritems():
      res.append({'key': k, 'value': v})
    return res


class AndroidGCEInstance(object):
  """Provides methods to launch/provision/shutdown an android gce instance."""

  def __init__(self, project, zone, prefix, compute, snapshot,
               path_to_adb, localport, ssh_key_file):
    """Init an AndroidCloudInstance

    Args:
      project: Name of gce project
      zone: Zone name to spawn resources in
      prefix: Prefix for the name of the disk and instance under gcloud
      compute: Initialized google compute engine api object
      snapshot: Name of the snapshot to create a disk from
      path_to_adb: Path to adb binary
      localport: Local port to redirect adb traffic out of. Each host's 
                 instance needs a unique port.
      ssh_key_file: Location of temporary ssh key that will be used to
                    communicate with the instance.
    """
    self.project = project
    self.zone = zone
    self.compute = compute
    self.snapshot = snapshot
    self.path_to_adb = path_to_adb
    self.localport = localport
    self.ssh_key_file = ssh_key_file

    self.disk_name = '%s-disk' % (prefix)
    self.instance_name = '%s-instance' % (prefix)
    self.instance_ip = None

  def create_disk(self):
    """Creates a disk for the android instance."""
    config = {
      'name': self.disk_name,
      'sourceSnapshot': 'global/snapshots/' + self.snapshot,
    }
    operation = self.compute.disks().insert(project=self.project,
        zone=self.zone, body=config).execute()
    return AndroidGCEOperation(operation, self.compute, self.zone,
                               self.project, self.instance_name)

  def launch_instance(self):
    """Launches the android instance."""
    config = {
      'name': self.instance_name,
      'machineType': 'zones/%s/machineTypes/%s' % (self.zone, _MACHINE_TYPE),
      'disks': [
        {
          'boot': True,
          'autoDelete': True,
          'source': 'zones/%s/disks/%s' % (self.zone, self.disk_name)
        }
      ],
      'networkInterfaces': [{
        'network': 'global/networks/default',
        'accessConfigs': [
          {'type': 'ONE_TO_ONE_NAT', 'name': 'external-nat'}
        ]
      }],
      'serviceAccounts': [{
        'email': 'default',
        'scopes': [
          'https://www.googleapis.com/auth/devstorage.read_write',
          'https://www.googleapis.com/auth/logging.write'
        ]
      }],
      'metadata': {
        'items': build_instance_properties(_INSTANCE_PROPERTIES)
      }
    }
    operation = self.compute.instances().insert(project=self.project,
        zone=self.zone, body=config).execute()
    return AndroidGCEOperation(operation, self.compute, self.zone,
                               self.project, self.instance_name)

  @property
  def is_done_launching(self):
    try:
      result = self.compute.instances().getSerialPortOutput(zone=self.zone, 
          project=self.project, instance=self.instance_name).execute()
      if 'VIRTUAL_DEVICE_BOOT_COMPLETED' in result['contents']:
        return True
      else:
        logging.info('Still waiting on %s...', self.instance_name)
        return False
    except googleapiclient.errors.HttpError:
      logging.exception('Error getting instance output')
      return False

  def get_ip(self):
    """Fetches and records the instance's external ip address."""
    result = self.compute.instances().get(project=self.project,
        zone=self.zone, instance=self.instance_name).execute()
    networks = result['networkInterfaces']
    self.instance_ip = networks[0]['accessConfigs'][0]['natIP']

  def send_ssh_key(self):
    """Sends a public key to the instance.

    The key will be used to establish an ssh tunnel between the host
    and the instance, along with copying files between the two.
    """
    # Get the instance's current metadata fingerprint, which is used for
    # locking when changing the metadata
    result = self.compute.instances().get(project=self.project,
        zone=self.zone, instance=self.instance_name).execute()
    fingerprint = result['metadata']['fingerprint']
    with open(self.ssh_key_file + '.pub', 'r') as f:
      pub_key = f.read().split()
    # Set the key to expire in 24 hours
    expire_time = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    expire_time_formatted = expire_time.strftime('%Y-%m-%dT%H:%M:%S+0000')
    config = {
      'kind': 'compute#metadata',
      'fingerprint': fingerprint,
      'items': [
        {
          'key': 'sshKeys',
          'value': '%s:%s %s android-gce-ssh {"expireOn":"%s"}'
              % ('root', pub_key[0], pub_key[1], expire_time_formatted)
        }
      ]
    }
    operation = self.compute.instances().setMetadata(project=self.project,
        zone=self.zone, instance=self.instance_name, body=config).execute()
    return AndroidGCEOperation(operation, self.compute, self.zone,
                               self.project, self.instance_name)

  # TODO(bpastene): Come up with a more reliable & scalable method for
  # managing the ssh tunnel if android-gce gets adopted at a larger scale
  def forward_port(self):
    """Establishes an ssh tunnel from the localhost to the gce instance.

    Traffic to the android instance's adbd port (_ADBD_PORT) is
    protected. Since traffic between the host's adb and a device's adbd
    is unencrypted, a secure channel needs to be established between the host
    and the instance. This function forwards and encrypts all traffic from a
    local port to the instance's adbd port. The ssh tunnel is spawned in the
    background and runs until it's killed. These processes are cleaned up in
    kill_ssh_tunnel().
    """ 
    self.get_ip()
    try:
      cmd = [
          'ssh',
          '-i', self.ssh_key_file,
          '-Nfn',
          '-o UserKnownHostsFile=/dev/null',
          '-o StrictHostKeyChecking=no',
          '-o ServerAliveInterval=30',
          '-L %d:127.0.0.1:%d' % (self.localport, _ADBD_PORT),
          'root@%s' % (self.instance_ip)
      ]
      subprocess.check_call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (TypeError, OSError, subprocess.CalledProcessError):
        logging.exception("Unable to forward port.")
        raise

  def connect_adb(self):
    """Connects adb to the android instance."""
    cmd = [self.path_to_adb, 'connect', '127.0.0.1:%d' % self.localport]
    output = subprocess.check_output(cmd)
    if 'unable to connect' in output:
      return False
    else:
      self.wait_for_device()
      return True

  def set_props(self):
    """Records the instance name and ip address as properties on the device."""
    cmd = [
        self.path_to_adb,
        '-s', '127.0.0.1:%d' % self.localport,
        'shell',
        'setprop net.gce.vm_name %s' % self.instance_name
    ]
    subprocess.check_call(cmd)
    cmd = [
        self.path_to_adb,
        '-s', '127.0.0.1:%d' % self.localport,
        'shell',
        'setprop net.gce.ip_address %s' % self.instance_ip]
    subprocess.check_call(cmd)

  def root_device(self):
    """Roots the instance."""
    cmd = [self.path_to_adb, '-s', '127.0.0.1:%d' % self.localport, 'root']
    subprocess.check_call(cmd)

  def unlock_screen(self):
    """Unlocks the screen."""
    cmd = [
        self.path_to_adb,
        '-s', '127.0.0.1:%d' % self.localport,
        'shell',
        'input keyevent 82'
    ]
    subprocess.check_call(cmd)

  def wait_for_device(self):
    """Waits for the device to be ready."""
    cmd = [
        self.path_to_adb,
        '-s', '127.0.0.1:%d' % self.localport,
        'wait-for-device'
    ]
    subprocess.check_call(cmd)

  def kill_ssh_tunnel(self):
    """Kills the ssh tunnel established in forward_port.

    This looks for the ssh tunnel process' signature in the list of running
    processes and kills it.
    """
    self.get_ip()
    for proc in psutil.process_iter():
      # A process is the ssh tunnel if it's an ssh command that's using the
      # instance's ssh key and is connected to the instance
      if (proc.name == 'ssh' and len(proc.cmdline) == 9
          and proc.cmdline[2] == self.ssh_key_file
          and proc.cmdline[8] == 'root@%s' % self.instance_ip):
        logging.info('Killing process %d, its cmd: %s', proc.pid, proc.cmdline)
        proc.kill()
        return

  def delete_instance(self):
    """Deletes the android instance, along with its disk."""
    operation = self.compute.instances().delete(project=self.project,
        zone=self.zone, instance=self.instance_name).execute()
    return AndroidGCEOperation(operation, self.compute, self.zone,
                               self.project, self.instance_name)

class AndroidGCEOperation(object):
  """Wrapper class around a gce api operation."""

  def __init__(self, operation, compute, zone, project, instance_name):
    """Init a AndroidGCEOperation

    Args:
      operation: The gce api request response.
      compute: Initialized google compute engine api object.
      project: ID of gce project
      zone: GCE zone of operation
    """
    self.operation = operation
    self.compute = compute
    self.zone = zone
    self.project = project
    self.instance_name = instance_name

  @property
  def is_complete(self):
    try:
      result = self.compute.zoneOperations().get(project=self.project,
          zone=self.zone, operation=self.operation['name']).execute()
      if result['status'] == 'DONE':
        if 'error' in result:
          logging.warning('Operation was not successful: %s', result['error'])
        return True
      else:
        logging.info('Status of %s for %s: %s',
                     self.operation['operationType'],
                     self.instance_name,
                     result['status'])
        return False
    except googleapiclient.errors.HttpError:
      logging.exception('Http error when requesting operation status')
      return False
