# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class DockerApi(recipe_api.RecipeApi):
  """Provides steps to connect and run Docker images."""

  def __init__(self, *args, **kwargs):
    super(DockerApi, self).__init__(*args, **kwargs)
    self._config_file = None
    self._project = None
    self._server = None

  def login(self, server='gcr.io', project='chromium-container-registry',
            service_account=None, step_name=None, **kwargs):
    """Connect to a Docker registry.

    This step must be executed before any other step in this module that
    requires authentication.

    Args:
      server: Docker server to connect to.
      project: Name of the Cloud project where Docker images are hosted.
      service_account: service_account.api.ServiceAccount used for
          authenticating with the container registry. Defaults to the task's
          associated service account.
      step_name: Override step name. Default is 'docker login'.
    """
    # We store config file in the cleanup dir to ensure that it is deleted after
    # the build finishes running. This way no subsequent builds running on the
    # same bot can re-use credentials obtained below.
    self._config_file = self.m.path['cleanup'].join('.docker')
    self._project = project
    self._server = server
    if not service_account:
      service_account = self.m.service_account.default()
    token = service_account.get_access_token(
        ['https://www.googleapis.com/auth/cloud-platform'])
    self.m.python(
        step_name or 'docker login',
        self.resource('docker_login.py'),
        args=[
          '--server', server,
          '--service-account-token-file', self.m.raw_io.input(token),
          '--config-file', self._config_file,
        ],
        **kwargs)

  def run(self, image, step_name=None, cmd_args=None, dir_mapping=None,
          **kwargs):
    """Run a command in a Docker image as the current user:group.

    Args:
      image: Name of the image to run.
      cmd_args: Used to specify command to run in an image as a list of
          arguments. If not specified, then the default command embedded into
          the image is executed.
      dir_mapping: List of tuples (host_dir, docker_dir) mapping host
          directories to directories in a Docker container. Directories are
          mapped as read-write.
      step_name: Override step name. Default is 'docker run'.
    """
    assert self._config_file, 'Did you forget to call docker.login?'
    args = [
      '--config-file', self._config_file,
      '--image', '%s/%s/%s' % (self._server, self._project, image),
    ]

    if dir_mapping:
      for host_dir, docker_dir in dir_mapping:
        args.extend(['--dir-map', host_dir, docker_dir])

    if cmd_args:
      args.append('--')
      args += cmd_args

    self.m.python(
        step_name or 'docker run',
        self.resource('docker_run.py'),
        args=args, **kwargs)

  def __call__(self, *args, **kwargs):
    """Executes specified docker command.

    Please make sure to use api.docker.login method before if specified command
    requires authentication.

    Args:
      args: arguments passed to the 'docker' command including subcommand name,
          e.g. api.docker('push', 'my_image:latest').
      kwargs: arguments passed down to api.step module.
    """
    cmd = ['docker']
    if '--config' not in args and self._config_file:
      cmd += ['--config', self._config_file]
    step_name = kwargs.pop('step_name', 'docker %s' % args[0])
    return self.m.step(step_name, cmd + list(args), **kwargs)
