import ayon_api
from ayon_core.client import get_asset_by_name
from ayon_core.settings import get_studio_settings
from ayon_core.lib.local_settings import get_ayon_username


def get_general_template_data(settings=None):
    """General template data based on system settings or machine.

    Output contains formatting keys:
    - 'studio[name]'    - Studio name filled from system settings
    - 'studio[code]'    - Studio code filled from system settings
    - 'user'            - User's name using 'get_ayon_username'

    Args:
        settings (Dict[str, Any]): Studio or project settings.
    """

    if not settings:
        settings = get_studio_settings()
    core_settings = settings["core"]
    return {
        "studio": {
            "name": core_settings["studio_name"],
            "code": core_settings["studio_code"]
        },
        "user": get_ayon_username()
    }


def get_project_template_data(project_entity=None, project_name=None):
    """Extract data from project document that are used in templates.

    Project document must have 'name' and (at this moment) optional
        key 'data.code'.

    One of 'project_name' or 'project_entity' must be passed. With prepared
    project document is function much faster because don't have to query.

    Output contains formatting keys:
    - 'project[name]'   - Project name
    - 'project[code]'   - Project code

    Args:
        project_entity (Dict[str, Any]): Queried project entity.
        project_name (str): Name of project.

    Returns:
        Dict[str, Dict[str, str]]: Template data based on project document.
    """

    if not project_name:
        project_name = project_entity["name"]

    if not project_entity:
        project_entity = ayon_api.get_project(project_name, fields=["code"])

    project_code = project_entity["code"]
    return {
        "project": {
            "name": project_name,
            "code": project_code
        }
    }


def get_asset_template_data(asset_doc, project_name):
    """Extract data from asset document that are used in templates.

    Output dictionary contains keys:
    - 'asset'       - asset name
    - 'hierarchy'   - parent asset names joined with '/'
    - 'parent'      - direct parent name, project name used if is under project

    Required document fields:
        Asset: 'name', 'data.parents'

    Args:
        asset_doc (Dict[str, Any]): Queried asset document.
        project_name (str): Is used for 'parent' key if asset doc does not have
            any.

    Returns:
        Dict[str, str]: Data that are based on asset document and can be used
            in templates.
    """

    asset_parents = asset_doc["data"]["parents"]
    hierarchy = "/".join(asset_parents)
    if asset_parents:
        parent_name = asset_parents[-1]
    else:
        parent_name = project_name

    return {
        "asset": asset_doc["name"],
        "folder": {
            "name": asset_doc["name"]
        },
        "hierarchy": hierarchy,
        "parent": parent_name
    }


def get_task_type(asset_doc, task_name):
    """Get task type based on asset document and task name.

    Required document fields:
        Asset: 'data.tasks'

    Args:
        asset_doc (Dict[str, Any]): Queried asset document.
        task_name (str): Task name which is under asset.

    Returns:
        str: Task type name.
        None: Task was not found on asset document.
    """

    asset_tasks_info = asset_doc["data"]["tasks"]
    return asset_tasks_info.get(task_name, {}).get("type")


def get_task_template_data(project_entity, asset_doc, task_name):
    """"Extract task specific data from project and asset documents.

    Required document fields:
        Project: 'tasksTypes'
        Asset: 'data.tasks'.

    Args:
        project_entity (Dict[str, Any]): Queried project entity.
        asset_doc (Dict[str, Any]): Queried asset document.
        task_name (str): Name of task for which data should be returned.

    Returns:
        Dict[str, Dict[str, str]]: Template data
    """

    project_task_types = project_entity["taskTypes"]
    task_types_by_name = {task["name"]: task for task in project_task_types}
    task_type = get_task_type(asset_doc, task_name)
    task_code = task_types_by_name.get(task_type, {}).get("shortName")

    return {
        "task": {
            "name": task_name,
            "type": task_type,
            "short": task_code,
        }
    }


def get_template_data(
    project_entity,
    asset_doc=None,
    task_name=None,
    host_name=None,
    settings=None
):
    """Prepare data for templates filling from entered documents and info.

    This function does not "auto fill" any values except system settings and
    it's on purpose.

    Universal function to receive template data from passed arguments. Only
    required argument is project document all other arguments are optional
    and their values won't be added to template data if are not passed.

    Required document fields:
        Project: 'name', 'code', 'taskTypes.name'
        Asset: 'name', 'data.parents', 'data.tasks'

    Args:
        project_entity (Dict[str, Any]): Project entity.
        asset_doc (Dict[str, Any]): Mongo document of asset from MongoDB.
        task_name (Union[str, None]): Task name under passed asset.
        host_name (Union[str, None]): Used to fill '{app}' key.
        settings (Union[Dict, None]): Prepared studio or project settings.
            They're queried if not passed (may be slower).

    Returns:
        Dict[str, Any]: Data prepared for filling workdir template.
    """

    template_data = get_general_template_data(settings)
    template_data.update(get_project_template_data(project_entity))
    if asset_doc:
        template_data.update(get_asset_template_data(
            asset_doc, project_entity["name"]
        ))
        if task_name:
            template_data.update(get_task_template_data(
                project_entity, asset_doc, task_name
            ))

    if host_name:
        template_data["app"] = host_name

    return template_data


def get_template_data_with_names(
    project_name,
    asset_name=None,
    task_name=None,
    host_name=None,
    settings=None
):
    """Prepare data for templates filling from entered entity names and info.

    Copy of 'get_template_data' but based on entity names instead of documents.
    Only difference is that documents are queried.

    Args:
        project_name (str): Project name for which template data are
            calculated.
        asset_name (Union[str, None]): Asset name for which template data are
            calculated.
        task_name (Union[str, None]): Task name under passed asset.
        host_name (Union[str, None]):Used to fill '{app}' key.
            because workdir template may contain `{app}` key.
        settings (Union[Dict, None]): Prepared studio or project settings.
            They're queried if not passed.

    Returns:
        Dict[str, Any]: Data prepared for filling workdir template.
    """

    project_entity = ayon_api.get_project(project_name)
    asset_doc = None
    if asset_name:
        asset_doc = get_asset_by_name(
            project_name,
            asset_name,
            fields=["name", "data.parents", "data.tasks"]
        )
    return get_template_data(
        project_entity, asset_doc, task_name, host_name, settings
    )
