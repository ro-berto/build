# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to build the chromium master."""

from master.factory import annotator_factory
from master.factory import remote_run_factory


class _ChromiteRecipeFactoryFunc(object):
  """
  Factory generation function wrapper that supplies Chromite recipe defaults.

  This class is a callable wrapper to annotator_factory.AnnotatorFactory's
  BaseFactory method, and offers the "remote" method to wrap a RemoteRunFactory
  call.

  This class painfully avoids subclassing annotator_factory.AnnotatorFactory in
  order to preserve its status as a terminal factory.
  """

  # The remote repository URL for public recipes.
  PUBLIC = 'https://chromium.googlesource.com/chromium/tools/build.git'
  # The remote repository URL for internal recipes.
  INTERNAL = ('https://chrome-internal.googlesource.com/chrome/tools/'
              'build_limited/scripts/slave.git')

  # The default Chromite recipe timeout.
  _CHROMITE_TIMEOUT = 9000
  # The default maximum build time.
  _DEFAULT_MAX_TIME = 20 * 60 * 60

  @classmethod
  def _apply_defaults(cls, kwargs):
    kwargs.setdefault('timeout', cls._CHROMITE_TIMEOUT)

    factory_properties = kwargs.setdefault('factory_properties', {})
    # Set the 'cbb_debug' property if we're not running in a production master.
    if kwargs.pop('debug', False):
      factory_properties['cbb_debug'] = True
    kwargs.setdefault('max_time', cls._DEFAULT_MAX_TIME)
    return kwargs

  @classmethod
  def __call__(cls, factory_obj, recipe, **kwargs):
    """Returns a factory object to use for Chromite annotator recipes.

    Args:
      factory_obj (annotator_factory.AnnotatorFactory) The base factory
        generator.
      recipe: The name of the recipe to invoke.
      debug (bool): If True, override default debug logic.
      kwargs: Positional / keyword arguments (see factory_obj).
    """
    return factory_obj.BaseFactory(recipe, **cls._apply_defaults(kwargs))

  @classmethod
  def remote(cls, active_master, repository, recipe, **kwargs):
    """Returns a factory object to use for Chromite "remote_run" annotator
    recipes.

    Args:
      factory_obj (remote_run_factory.RemoteRunFactory) The base factory
        generator.
      active_master: is config_bootstrap.Master's subclass from master's
        master_site_config.py.
      repository: the URL of repository containing recipe to run, probably one
        of PUBLIC or INTERNAL.
      recipe: The name of the recipe to invoke.
      debug (bool): If True, override default debug logic.
      kwargs: Positional / keyword arguments (see factory_obj).
    """
    return remote_run_factory.RemoteRunFactory(
        active_master, repository, recipe, **cls._apply_defaults(kwargs))


# Callable instance of '_ChromiteRecipeFactoryFunc'.
ChromiteRecipeFactory = _ChromiteRecipeFactoryFunc()
