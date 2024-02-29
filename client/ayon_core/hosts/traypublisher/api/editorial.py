import re
from copy import deepcopy

from ayon_core.client import get_asset_by_id
from ayon_core.pipeline.create import CreatorError


class ShotMetadataSolver:
    """ Solving hierarchical metadata

    Used during editorial publishing. Works with input
    clip name and settings defining python formatable
    template. Settings also define searching patterns
    and its token keys used for formatting in templates.
    """

    NO_DECOR_PATERN = re.compile(r"\{([a-z]*?)\}")

    def __init__(self, logger):
        self.clip_name_tokenizer = []
        self.shot_rename = {
            "enabled": False,
            "shot_rename_template": "",
        }
        self.shot_hierarchy = {
            "enabled": False,
            "parents": [],
            "parents_path": "",
        }
        self.shot_add_tasks = []
        self.log = logger

    def update_data(
        self,
        clip_name_tokenizer,
        shot_rename,
        shot_hierarchy,
        shot_add_tasks
    ):
        self.clip_name_tokenizer = clip_name_tokenizer
        self.shot_rename = shot_rename
        self.shot_hierarchy = shot_hierarchy
        self.shot_add_tasks = shot_add_tasks

    def _rename_template(self, data):
        """Shot renaming function

        Args:
            data (dict): formatting data

        Raises:
            CreatorError: If missing keys

        Returns:
            str: formatted new name
        """
        shot_rename_template = self.shot_rename[
            "shot_rename_template"]
        try:
            # format to new shot name
            return shot_rename_template.format(**data)
        except KeyError as _error:
            raise CreatorError((
                "Make sure all keys in settings are correct:: \n\n"
                f"From template string {shot_rename_template} > "
                f"`{_error}` has no equivalent in \n"
                f"{list(data.keys())} input formatting keys!"
            ))

    def _generate_tokens(self, clip_name, source_data):
        """Token generator

        Settings defines token pairs key and regex expression.

        Args:
            clip_name (str): name of clip in editorial
            source_data (dict): data for formatting

        Raises:
            CreatorError: if missing key

        Returns:
            dict: updated source_data
        """
        output_data = deepcopy(source_data["anatomy_data"])
        output_data["clip_name"] = clip_name

        if not self.clip_name_tokenizer:
            return output_data

        parent_name = source_data["selected_asset_doc"]["name"]

        search_text = parent_name + clip_name

        for clip_name_item in self.clip_name_tokenizer:
            token_key = clip_name_item["name"]
            pattern = clip_name_item["regex"]
            p = re.compile(pattern)
            match = p.findall(search_text)
            if not match:
                raise CreatorError((
                    "Make sure regex expression works with your data: \n\n"
                    f"'{token_key}' with regex '{pattern}' in your settings\n"
                    "can't find any match in your clip name "
                    f"'{search_text}'!\n\nLook to: "
                    "'project_settings/traypublisher/editorial_creators"
                    "/editorial_simple/clip_name_tokenizer'\n"
                    "at your project settings..."
                ))

            #  QUESTION:how to refactor `match[-1]` to some better way?
            output_data[token_key] = match[-1]

        return output_data

    def _create_parents_from_settings(self, parents, data):
        """formatting parent components.

        Args:
            parents (list): list of dict parent components
            data (dict): formatting data

        Raises:
            CreatorError: missing formatting key
            CreatorError: missing token key
            KeyError: missing parent token

        Returns:
            list: list of dict of parent components
        """
        # fill the parents parts from presets
        shot_hierarchy = deepcopy(self.shot_hierarchy)
        hierarchy_parents = shot_hierarchy["parents"]

        # fill parent keys data template from anatomy data
        try:
            _parent_tokens_formatting_data = {
                parent_token["name"]: parent_token["value"].format(**data)
                for parent_token in hierarchy_parents
            }
        except KeyError as _error:
            raise CreatorError((
                "Make sure all keys in settings are correct : \n"
                f"`{_error}` has no equivalent in \n{list(data.keys())}"
            ))

        _parent_tokens_type = {
            parent_token["name"]: parent_token["parent_type"]
            for parent_token in hierarchy_parents
        }
        for _index, _parent in enumerate(
            shot_hierarchy["parents_path"].split("/")
        ):
            # format parent token with value which is formatted
            try:
                parent_name = _parent.format(
                    **_parent_tokens_formatting_data)
            except KeyError as _error:
                raise CreatorError((
                    "Make sure all keys in settings are correct : \n\n"
                    f"`{_error}` from template string "
                    f"{shot_hierarchy['parents_path']}, "
                    f" has no equivalent in \n"
                    f"{list(_parent_tokens_formatting_data.keys())} parents"
                ))

            parent_token_name = (
                self.NO_DECOR_PATERN.findall(_parent).pop())

            if not parent_token_name:
                raise KeyError(
                    f"Parent token is not found in: `{_parent}`")

            # find parent type
            parent_token_type = _parent_tokens_type[parent_token_name]

            # in case selected context is set to the same asset
            if (
                _index == 0
                and parents[-1]["entity_name"] == parent_name
            ):
                continue

            # in case first parent is project then start parents from start
            if (
                _index == 0
                and parent_token_type == "project"
            ):
                project_parent = parents[0]
                parents = [project_parent]
                continue

            parents.append({
                "entity_type": parent_token_type,
                "entity_name": parent_name
            })

        return parents

    def _create_hierarchy_path(self, parents):
        """Converting hierarchy path from parents

        Args:
            parents (list): list of dict parent components

        Returns:
            str: hierarchy path
        """
        return "/".join(
            [
                p["entity_name"] for p in parents
                if p["entity_type"] != "project"
            ]
        ) if parents else ""

    def _get_parents_from_selected_asset(
        self,
        asset_doc,
        project_entity
    ):
        """Returning parents from context on selected asset.

        Context defined in Traypublisher project tree.

        Args:
            asset_doc (db obj): selected asset doc
            project_entity (dict[str, Any]): Project entity.

        Returns:
            list:  list of dict parent components
        """
        project_name = project_entity["name"]
        visual_hierarchy = [asset_doc]
        current_doc = asset_doc

        # looping through all available visual parents
        # if they are not available anymore than it breaks
        while True:
            visual_parent_id = current_doc["data"]["visualParent"]
            visual_parent = None
            if visual_parent_id:
                visual_parent = get_asset_by_id(project_name, visual_parent_id)

            if not visual_parent:
                break
            visual_hierarchy.append(visual_parent)
            current_doc = visual_parent

        # add current selection context hierarchy
        output = []
        for entity in reversed(visual_hierarchy):
            output.append({
                "entity_type": entity["data"]["entityType"],
                "entity_name": entity["name"]
            })
        output.append({
            "entity_type": "project",
            "entity_name": project_name,
        })
        return output

    def _generate_tasks_from_settings(self, project_entity):
        """Convert settings inputs to task data.

        Args:
            project_entity (dict): Project entity.

        Raises:
            KeyError: Missing task type in project doc

        Returns:
            dict: tasks data
        """
        tasks_to_add = {}

        project_task_types = project_entity["taskTypes"]
        task_type_names = {
            task_type["name"]
            for task_type in project_task_types
        }
        for task_item in self.shot_add_tasks:
            task_name = task_item["name"]
            task_type = task_item["task_type"]

            # check if task type in project task types
            if task_type not in task_type_names:
                raise KeyError(
                    "Missing task type `{}` for `{}` is not"
                    " existing in `{}``".format(
                        task_type,
                        task_name,
                        list(task_type_names)
                    )
                )
            tasks_to_add[task_name] = {"type": task_type}

        return tasks_to_add

    def generate_data(self, clip_name, source_data):
        """Metadata generator.

        Converts input data to hierarchy mentadata.

        Args:
            clip_name (str): clip name
            source_data (dict): formatting data

        Returns:
            (str, dict): shot name and hierarchy data
        """

        tasks = {}
        asset_doc = source_data["selected_asset_doc"]
        project_entity = source_data["project_entity"]

        # match clip to shot name at start
        shot_name = clip_name

        # parse all tokens and generate formatting data
        formatting_data = self._generate_tokens(shot_name, source_data)

        # generate parents from selected asset
        parents = self._get_parents_from_selected_asset(
            asset_doc, project_entity
        )

        if self.shot_rename["enabled"]:
            shot_name = self._rename_template(formatting_data)
            self.log.info(f"Renamed shot name: {shot_name}")

        if self.shot_hierarchy["enabled"]:
            parents = self._create_parents_from_settings(
                parents, formatting_data)

        if self.shot_add_tasks:
            tasks = self._generate_tasks_from_settings(
                project_entity)

        # generate hierarchy path from parents
        hierarchy_path = self._create_hierarchy_path(parents)
        if hierarchy_path:
            folder_path = f"/{hierarchy_path}/{shot_name}"
        else:
            folder_path = f"/{shot_name}"

        return shot_name, {
            "hierarchy": hierarchy_path,
            "folderPath": folder_path,
            "parents": parents,
            "tasks": tasks
        }
