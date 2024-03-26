import os
import sys

import requests
import six

from ayon_core.lib import Logger
from ayon_core.modules import AYONAddon, IPluginPaths


class DeadlineWebserviceError(Exception):
    """
    Exception to throw when connection to Deadline server fails.
    """


class DeadlineModule(AYONAddon, IPluginPaths):
    name = "deadline"

    def initialize(self, studio_settings):
        # This module is always enabled
        deadline_server_info = {}
        enabled = self.name in studio_settings
        if enabled:
            deadline_settings = studio_settings[self.name]
            deadline_server_info = {
                url_item["name"]: url_item
                for url_item in deadline_settings["deadline_urls"]
            }

        if enabled and not deadline_server_info:
            enabled = False
            self.log.warning((
                "Deadline Webservice URLs are not specified. Disabling addon."
            ))

        self.enabled = enabled
        self.deadline_server_info = deadline_server_info

    def get_plugin_paths(self):
        """Deadline plugin paths."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return {
            "publish": [os.path.join(current_dir, "plugins", "publish")]
        }

    @staticmethod
    def get_deadline_pools(webservice, auth=None, log=None):
        # type: (str) -> list
        """Get pools from Deadline.
        Args:
            webservice (str): Server url.
            log (Logger)
        Returns:
            list: Pools.
        Throws:
            RuntimeError: If deadline webservice is unreachable.

        """
        from .abstract_submit_deadline import requests_get

        if not log:
            log = Logger.get_logger(__name__)

        argument = "{}/api/pools?NamesOnly=true".format(webservice)
        try:
            kwargs = {}
            if auth:
                kwargs["auth"] = auth
            response = requests_get(argument, **kwargs)
        except requests.exceptions.ConnectionError as exc:
            msg = 'Cannot connect to DL web service {}'.format(webservice)
            log.error(msg)
            six.reraise(
                DeadlineWebserviceError,
                DeadlineWebserviceError('{} - {}'.format(msg, exc)),
                sys.exc_info()[2])
        if not response.ok:
            log.warning("No pools retrieved")
            return []

        return response.json()
