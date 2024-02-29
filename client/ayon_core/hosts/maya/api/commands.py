# -*- coding: utf-8 -*-
"""OpenPype script commands to be used directly in Maya."""
from maya import cmds

from ayon_api import get_project

from ayon_core.client import get_asset_by_name
from ayon_core.pipeline import get_current_project_name, get_current_asset_name


class ToolWindows:

    _windows = {}

    @classmethod
    def get_window(cls, tool):
        """Get widget for specific tool.

        Args:
            tool (str): Name of the tool.

        Returns:
            Stored widget.

        """
        try:
            return cls._windows[tool]
        except KeyError:
            return None

    @classmethod
    def set_window(cls, tool, window):
        """Set widget for the tool.

        Args:
            tool (str): Name of the tool.
            window (QtWidgets.QWidget): Widget

        """
        cls._windows[tool] = window


def _resolution_from_document(doc):
    if not doc:
        print("Entered document is not valid. \"{}\"".format(
            str(doc)
        ))
        return None

    attributes = doc.get("attrib")
    if attributes is None:
        attributes = doc.get("data", {})

    resolution_width = attributes.get("resolutionWidth")
    resolution_height = attributes.get("resolutionHeight")
    # Backwards compatibility
    if resolution_width is None or resolution_height is None:
        resolution_width = attributes.get("resolution_width")
        resolution_height = attributes.get("resolution_height")

    # Make sure both width and height are set
    if resolution_width is None or resolution_height is None:
        cmds.warning(
            "No resolution information found for \"{}\"".format(doc["name"])
        )
        return None

    return int(resolution_width), int(resolution_height)


def reset_resolution():
    # Default values
    resolution_width = 1920
    resolution_height = 1080

    # Get resolution from asset
    project_name = get_current_project_name()
    asset_name = get_current_asset_name()
    asset_doc = get_asset_by_name(project_name, asset_name)
    resolution = _resolution_from_document(asset_doc)
    # Try get resolution from project
    if resolution is None:
        # TODO go through visualParents
        print((
            "Asset \"{}\" does not have set resolution."
            " Trying to get resolution from project"
        ).format(asset_name))
        project_entity = get_project(project_name)
        resolution = _resolution_from_document(project_entity)

    if resolution is None:
        msg = "Using default resolution {}x{}"
    else:
        resolution_width, resolution_height = resolution
        msg = "Setting resolution to {}x{}"

    print(msg.format(resolution_width, resolution_height))

    # set for different renderers
    # arnold, vray, redshift, renderman

    renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer").lower()
    # handle various renderman names
    if renderer.startswith("renderman"):
        renderer = "renderman"

    # default attributes are usable for Arnold, Renderman and Redshift
    width_attr_name = "defaultResolution.width"
    height_attr_name = "defaultResolution.height"

    # Vray has its own way
    if renderer == "vray":
        width_attr_name = "vraySettings.width"
        height_attr_name = "vraySettings.height"

    cmds.setAttr(width_attr_name, resolution_width)
    cmds.setAttr(height_attr_name, resolution_height)
