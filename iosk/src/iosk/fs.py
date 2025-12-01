# sk/iosk/fs.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import os
import posixpath
from os.path import isdir, isfile, exists, getsize, getmtime
import shutil
import random
import traceback
import importlib.util

from .io import Context
from binaryornot.check import is_binary

class FileSystemManager:
    """Manages all virtual filesystem operations for the IOSK kernel using an overlay model."""
    def __init__(self, kernel):
        self.os = kernel

    # --- Path Resolution Helpers ---

    def _resolve_virtual_path(self, virtual_path_input: str, io_context=None) -> str:
        """Helper to resolve and normalize a virtual path."""
        effective_virtual_path = virtual_path_input
        if io_context and io_context.pwd and not posixpath.isabs(virtual_path_input):
            effective_virtual_path = posixpath.join(io_context.pwd, virtual_path_input)
        return posixpath.normpath(effective_virtual_path)

    def _to_host_path(self, base_root: str, normalized_virtual_path: str) -> str:
        """Helper to convert a virtual path to a host path relative to a base root."""
        path_relative_to_virtual_root = normalized_virtual_path.lstrip('/')
        path_components = path_relative_to_virtual_root.split('/')
        host_path = os.path.join(base_root, *path_components)
        return os.path.abspath(host_path)

    def _remove_tombstone_if_exists(self, normalized_virtual_path: str):
        """Helper to remove a tombstone file for a given virtual path."""
        # The tombstone lives in the same writable layer as the file itself would.
        # We find its parent directory by getting the write path for the original
        # file and taking its host directory name.
        file_write_path = self.box_for_write(normalized_virtual_path)
        tombstone_dir_host = os.path.dirname(file_write_path)

        _, file_name = posixpath.split(normalized_virtual_path)
        tombstone_name = f'.iosk.rm.{file_name}'
        tombstone_py_name = f'.iosk.rm.{file_name}.py'
        
        tombstone_path = os.path.join(tombstone_dir_host, tombstone_name)
        if isfile(tombstone_path):
            os.remove(tombstone_path)

        tombstone_py_path = os.path.join(tombstone_dir_host, tombstone_py_name)
        if isfile(tombstone_py_path):
            os.remove(tombstone_py_path)

    def box(self, virtual_path_input: str, io_context=None) -> str:
        """
        Sandboxes a virtual path for reading, checking layers in the correct order of precedence.
        Returns the absolute host filesystem path to the file that should be used.
        """
        normalized_virtual_path = self._resolve_virtual_path(virtual_path_input, io_context)

        # In 3M mode, paths under the mount point are special. They only resolve to the User Media, with no fallback.
        if self.os.mount_point:
            mount_point = posixpath.normpath(self.os.mount_point)
            if normalized_virtual_path == mount_point or \
               normalized_virtual_path.startswith(mount_point + '/'):
                
                # The path needs to be calculated relative to the mount point, not from the virtual root.
                relative_path = posixpath.relpath(normalized_virtual_path, mount_point)
                path_components = [] if relative_path == '.' else relative_path.split('/')
                user_media_path = os.path.join(self.os.workspace_root, *path_components)
                user_media_path = os.path.abspath(user_media_path)

                # Per proposal, paths inside the mount point do not fall back to other layers.
                # This creates a "clean" mounted volume. `box` returns the potential host path,
                # and callers like `exists` or `get` will determine if it's actually present.
                # We must still check for the .py variant, as that's a resolution rule.
                if not exists(user_media_path) and isfile(user_media_path + '.py'):
                    return user_media_path + '.py'
                return user_media_path

        # For all other paths (or if not in 3M mode), check layers in order:
        # 1. System Workspace -> 2. Distribution

        # 1. Check System Workspace (this is workspace_root in standard mode)
        system_workspace_path = self._to_host_path(self.os.system_workspace_root, normalized_virtual_path)
        if exists(system_workspace_path):
            return system_workspace_path
        
        if isfile(system_workspace_path + '.py'):
            return system_workspace_path + '.py'
            
        # 2. Fallback to Distribution
        dist_host_path = self._to_host_path(self.os.dist_root, normalized_virtual_path)
        
        if not exists(dist_host_path) and isfile(dist_host_path + '.py'):
            return dist_host_path + '.py'
            
        return dist_host_path

    def box_for_write(self, virtual_path_input: str, io_context=None) -> str:
        """
        Sandboxes a virtual path for writing. In Mounted Media Mode, it routes
        writes to either the User Media (the workspace) or the System Workspace
        (a hidden subdirectory). Otherwise, it targets the main workspace.
        Returns the absolute host filesystem path where the write should occur.
        """
        normalized_virtual_path = self._resolve_virtual_path(virtual_path_input, io_context)

        # --- Mounted Media Mode (3M) Write Routing ---
        if self.os.mount_point:
            mount_point = posixpath.normpath(self.os.mount_point)

            # Check if the virtual path is at or below the mount point.
            if normalized_virtual_path == mount_point or \
               normalized_virtual_path.startswith(mount_point + '/'):

                # This write goes to the "User Media" (the main workspace directory).
                # We calculate the path relative to the mount point...
                relative_path = posixpath.relpath(normalized_virtual_path, mount_point)

                # ...and map it to the host filesystem under the workspace root.
                path_components = [] if relative_path == '.' else relative_path.split('/')
                host_path = os.path.join(self.os.workspace_root, *path_components)
                return os.path.abspath(host_path)

        # --- Standard Mode OR write outside mount point in 3M ---
        # The write goes to the "System Workspace".
        # In standard mode, system_workspace_root == workspace_root.
        # In 3M mode, system_workspace_root == <workspace_root>/.iosk.
        return self._to_host_path(self.os.system_workspace_root, normalized_virtual_path)

    # --- Core FS API ---

    async def exists(self, io:Context, path:str):
        """Test if path exists in the merged filesystem view."""
        normalized_virtual_path = self._resolve_virtual_path(path, io_context=io)

        # Rule 2a: Files with .iosk. prefix must never appear to exist.
        if posixpath.basename(normalized_virtual_path).startswith('.iosk.'):
            return False

        # 1. Check for a tombstone. A tombstone's location is determined by where the
        # original file *would have been written*.
        tombstone_write_dir_host = os.path.dirname(self.box_for_write(normalized_virtual_path))
        _, file_name = posixpath.split(normalized_virtual_path)
        tombstone_name = f'.iosk.rm.{file_name}'
        tombstone_py_name = f'.iosk.rm.{file_name}.py'
        
        if isfile(os.path.join(tombstone_write_dir_host, tombstone_name)) or \
           isfile(os.path.join(tombstone_write_dir_host, tombstone_py_name)):
            return False

        # 2. Check for the physical file/directory using the multi-layer read-path resolution.
        # box() returns the highest-precedence host path for a virtual path.
        host_path = self.box(normalized_virtual_path, io)
        if exists(host_path):
            return True
        # box() already resolves the .py variant, so we don't need a separate check.
            
        # 3. Check for built-in python modules
        mod_suffix = normalized_virtual_path.lstrip('/')
        if not mod_suffix: return False

        full_mod_name = f'iosk.{mod_suffix.replace("/", ".").replace("-", "_")}'
        try:
            if importlib.util.find_spec(full_mod_name) is not None:
                return True
        except (ModuleNotFoundError, ValueError):
            pass
            
        return False

    async def create(self, io:Context, path:str):
        """Create new (empty) file in the workspace."""
        normalized_virtual_path = self._resolve_virtual_path(path, io_context=io)
        if posixpath.basename(normalized_virtual_path).startswith('.iosk.'):
            await io.error("!! creating files with '.iosk.' prefix is forbidden (system reserved).")
            return False

        # If a tombstone exists for this path, remove it.
        self._remove_tombstone_if_exists(normalized_virtual_path)

        file_host_path = self.box_for_write(path, io_context=io)
        if exists(file_host_path): return True

        # Ensure parent directory exists in workspace
        parent_dir = os.path.dirname(file_host_path)
        if not exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        with open(file_host_path, 'w') as f: pass
        return True

    async def copy(self, io:Context, from_path:str, to_path:str):
        """Copy file. Source is from merged view, destination is always in workspace."""
        normalized_to_path = self._resolve_virtual_path(to_path, io_context=io)
        if posixpath.basename(normalized_to_path).startswith('.iosk.'):
            await io.error("!! creating files with '.iosk.' prefix is forbidden (system reserved).")
            return False

        # If a tombstone exists for the destination path, remove it.
        self._remove_tombstone_if_exists(normalized_to_path)

        from_file_host = self.box(from_path, io_context=io)
        if not exists(from_file_host):
            await io.error(f'!! copy from path not found: {from_path}')
            return False

        to_file_host = self.box_for_write(to_path, io_context=io)
        to_dir_host = os.path.dirname(to_file_host)
        if not exists(to_dir_host):
            os.makedirs(to_dir_host, exist_ok=True)

        shutil.copy(from_file_host, to_file_host)
        return True

    async def move(self, io:Context, from_path:str, to_path:str):
        """Move file/directory. Destination is always in workspace."""
        # Rule 2b: Prevent creation of .iosk. prefixed files.
        normalized_to_path = self._resolve_virtual_path(to_path, io_context=io)
        if posixpath.basename(normalized_to_path).startswith('.iosk.'):
            await io.error("!! creating files with '.iosk.' prefix is forbidden (system reserved).")
            return False

        # Implemented as a copy-then-remove to handle overlay logic correctly.
        from_host_path = self.box(from_path, io_context=io)
        if not exists(from_host_path):
            await io.error(f'!! move from path not found: {from_path}')
            return False

        if await self.copy(io, from_path, to_path):
            if isdir(from_host_path):
                return await self.remove_dir(io, from_path)
            else:
                return await self.remove(io, from_path)
        return False

    async def remove(self, io:Context, path:str):
        """Removes a file. If in a writable layer, it's deleted. If only in distribution, creates a tombstone."""
        if not await self.exists(io, path): # Checks merged view, respecting tombstones
            await io.error(f'!! remove path not found: {path}')
            return False

        resolved_host_path = self.box(path, io_context=io)
        if isdir(resolved_host_path):
            await io.error(f'!! path is a directory, use rmdir: {path}')
            return False

        normalized_virtual_path = self._resolve_virtual_path(path, io_context=io)
        
        # --- BEGIN FIX ---
        # The logic below must check for and delete the file from any applicable writable layer.
        
        deleted_something = False
        
        # 1. Check and delete from the System Workspace layer.
        #    In standard mode, this is the main workspace. In 3M mode, it's the .iosk directory.
        #    The path is a direct mapping from the virtual root.
        system_workspace_path = self._to_host_path(self.os.system_workspace_root, normalized_virtual_path)
        system_workspace_py_path = system_workspace_path + '.py'
        
        if isfile(system_workspace_py_path):
            os.remove(system_workspace_py_path)
            deleted_something = True
        if isfile(system_workspace_path):
            os.remove(system_workspace_path)
            deleted_something = True
        
        # 2. In 3M mode, also check and delete from the User Media layer if the path is under the mount point.
        #    In standard mode, this location is the same as the system workspace and was already checked.
        if self.os.mount_point and self.os.system_workspace_root != self.os.workspace_root:
            mount_point = posixpath.normpath(self.os.mount_point)
            if normalized_virtual_path == mount_point or \
               normalized_virtual_path.startswith(mount_point + '/'):
                
                # The host path is calculated relative to the mount point.
                relative_path = posixpath.relpath(normalized_virtual_path, mount_point)
                path_components = [] if relative_path == '.' else relative_path.split('/')
                user_media_path = os.path.join(self.os.workspace_root, *path_components)
                user_media_py_path = user_media_path + '.py'

                if isfile(user_media_py_path):
                    os.remove(user_media_py_path)
                    deleted_something = True
                if isfile(user_media_path):
                    os.remove(user_media_path)
                    deleted_something = True

        if deleted_something:
            return True
        # --- END FIX ---

        # If it only exists in the distribution, create a tombstone.
        dist_path = self._to_host_path(self.os.dist_root, normalized_virtual_path)
        dist_py_path = dist_path + '.py'
        tombstone_target = None
        if isfile(dist_py_path):
            tombstone_target = normalized_virtual_path + '.py'
        elif isfile(dist_path):
            tombstone_target = normalized_virtual_path

        if tombstone_target:
            # Rule 3: Store content in tombstone
            source_content = b''
            source_host_path = self._to_host_path(self.os.dist_root, tombstone_target)
            try:
                with open(source_host_path, 'rb') as f:
                    source_content = f.read()
            except OSError as e:
                await io.error(f"!! could not read original file to create tombstone: {e}")
                return False

            dir_name, file_name = posixpath.split(tombstone_target)
            tombstone_name = f'.iosk.rm.{file_name}' # Rule 1: New tombstone prefix
            tombstone_virtual_path = posixpath.join(dir_name, tombstone_name)
            tombstone_host_path = self.box_for_write(tombstone_virtual_path)
            
            parent_dir = os.path.dirname(tombstone_host_path)
            if not exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            
            with open(tombstone_host_path, 'wb') as f:
                f.write(source_content)
            return True

        return False # Should be unreachable if exists() check passed

    async def create_dir(self, io:Context, path:str, parents=False):
        """Create new directory in the workspace."""
        folder = self.box_for_write(path, io_context=io)
        if exists(folder): return True # Idempotent

        try:
            if parents: os.makedirs(folder, exist_ok=True)
            else: os.mkdir(folder)
            return True
        except OSError as e:
            await io.error(f"!! failed to create directory '{path}': {e}")
            return False

    async def remove_dir(self, io:Context, path:str):
        """Removes an empty directory from the workspace."""
        folder = self.box_for_write(path, io_context=io)
        if not exists(folder):
            await io.error(f'!! remove dir path not found in workspace: {path}')
            return False
        if not isdir(folder):
            await io.error(f'!! path is not a directory in workspace: {path}')
            return False

        try:
            os.rmdir(folder)
            return True
        except OSError as e:
            await io.error(f"!! failed to remove directory '{path}': {e}") # e.g., "Directory not empty"
            return False

    async def unremove(self, io: Context, path: str):
        """Restores a file by removing its tombstone from the workspace."""
        normalized_virtual_path = self._resolve_virtual_path(path, io_context=io)

        # First, check if the file already exists (not as a tombstone).
        # We can't unremove something that's not removed.
        if await self.exists(io, path):
             await io.error(f"!! unrm: cannot restore '{path}': file already exists.")
             return False

        # The tombstone lives in the same writable layer as the file itself would.
        # We find its parent directory by getting the write path for the original
        # file and taking its host directory name.
        file_write_path = self.box_for_write(normalized_virtual_path)
        tombstone_dir_host = os.path.dirname(file_write_path)
        _, file_name = posixpath.split(normalized_virtual_path)

        tombstone_name = f'.iosk.rm.{file_name}'
        tombstone_py_name = f'.iosk.rm.{file_name}.py'
        
        tombstone_path = os.path.join(tombstone_dir_host, tombstone_name)
        tombstone_py_path = os.path.join(tombstone_dir_host, tombstone_py_name)

        found_and_removed = False
        if isfile(tombstone_path):
            os.remove(tombstone_path)
            found_and_removed = True

        if isfile(tombstone_py_path):
            os.remove(tombstone_py_path)
            found_and_removed = True

        if not found_and_removed:
            await io.error(f"!! unrm: no removed version of '{path}' found to restore.")
            return False
        
        return True

    async def _get_ignore_set(self, io: Context, virtual_dir_path: str) -> set:
        """Reads a .skignore file from a virtual directory path."""
        ignore_file_path = posixpath.join(virtual_dir_path, '.skignore')
        if await self.exists(io, ignore_file_path):
            content = await self.get(io, ignore_file_path)
            if content:
                return set(line.strip() for line in content.splitlines() if line.strip())
        return set()

    def _is_standard_ignorable(self, item_name: str) -> bool:
        """Checks if a path item should be ignored by standard rules (dotfiles, backups, etc)."""
        return item_name.startswith('.') \
            or item_name.endswith('~') \
            or item_name.endswith('.bak') \
            or item_name.endswith('.orig') \
            or item_name == '__pycache__'

    async def list_dir(self, io: Context, path: str, recursive: bool = False, show_all: bool = False, honor_skignore: bool = True) -> list:
        """Lists directory contents, merging workspace and distribution, handling tombstones."""
        normalized_virtual_path = self._resolve_virtual_path(path, io_context=io)
        
        # Check if the path exists as a directory in any layer.
        system_ws_dir_host = self._to_host_path(self.os.system_workspace_root, normalized_virtual_path)
        dist_dir_host = self._to_host_path(self.os.dist_root, normalized_virtual_path)
        
        is_dir_in_layer = isdir(system_ws_dir_host) or isdir(dist_dir_host)
        exists_in_layer = exists(system_ws_dir_host) or exists(dist_dir_host)

        if self.os.mount_point:
            mount_point = posixpath.normpath(self.os.mount_point)
            if normalized_virtual_path == mount_point or \
               normalized_virtual_path.startswith(mount_point + '/'):
                user_media_dir_host = self._to_host_path(self.os.workspace_root, normalized_virtual_path)
                is_dir_in_layer = is_dir_in_layer or isdir(user_media_dir_host)
                exists_in_layer = exists_in_layer or exists(user_media_dir_host)
        
        if not is_dir_in_layer:
             if exists_in_layer:
                 raise NotADirectoryError(f"Path is not a directory: {path}")
             else:
                 raise FileNotFoundError(f"Path not found: {path}")

        async def _list_level_raw(virtual_base_path):
            """Lists all raw entries in a directory, merging all layers and filtering out tombstones."""
            results = {}
            tombstones = set()

            # Layer 1: Distribution (Base)
            dist_path = self._to_host_path(self.os.dist_root, virtual_base_path)
            if isdir(dist_path):
                for name in os.listdir(dist_path):
                    if name.startswith('.iosk.'):
                        continue
                    host_p = os.path.join(dist_path, name)
                    results[name] = {'name': name, 'type': 'dir' if isdir(host_p) else 'file'}

            # Layer 2: System Workspace (overlays Distribution)
            system_ws_path = self._to_host_path(self.os.system_workspace_root, virtual_base_path)
            if isdir(system_ws_path):
                for name in os.listdir(system_ws_path):
                    if name.startswith('.iosk.rm.'):
                        tombstones.add(name[9:])
                        continue
                    if name.startswith('.iosk.'):
                        continue
                    host_p = os.path.join(system_ws_path, name)
                    results[name] = {'name': name, 'type': 'dir' if isdir(host_p) else 'file'}

            # Layer 3: User Media (highest precedence, only applies under mount point in 3M)
            is_under_mount = False
            if self.os.mount_point:
                mount_point = posixpath.normpath(self.os.mount_point)
                if virtual_base_path == mount_point or \
                   virtual_base_path.startswith(mount_point + '/'):
                    is_under_mount = True
            
            if is_under_mount:
                # The path needs to be calculated relative to the mount point, not from the virtual root.
                relative_path = posixpath.relpath(virtual_base_path, mount_point)
                path_components = [] if relative_path == '.' else relative_path.split('/')
                user_media_path = os.path.join(self.os.workspace_root, *path_components)
                user_media_path = os.path.abspath(user_media_path)

                if isdir(user_media_path):
                    for name in os.listdir(user_media_path):
                        if name.startswith('.iosk.rm.'):
                            tombstones.add(name[9:])
                            continue
                        if name.startswith('.iosk.'):
                            continue
                        host_p = os.path.join(user_media_path, name)
                        results[name] = {'name': name, 'type': 'dir' if isdir(host_p) else 'file'}

            listing = []
            for name, data in sorted(results.items()):
                if name not in tombstones:
                    item_virtual_path = posixpath.join(virtual_base_path, name)
                    item_host_path = self.box(item_virtual_path)
                    try: size, mtime = (getsize(item_host_path), getmtime(item_host_path))
                    except OSError: size, mtime = -1, -1
                    data.update({'path': item_virtual_path, 'size': size, 'mtime': mtime})
                    listing.append(data)
            return listing

        if not recursive:
            items = await _list_level_raw(normalized_virtual_path)
            if show_all:
                return items

            final_items = []
            ignores = await self._get_ignore_set(io, normalized_virtual_path) if honor_skignore else set()
            for item in items:
                name = item['name']
                if self._is_standard_ignorable(name):
                    continue
                if honor_skignore and name in ignores:
                    continue
                final_items.append(item)
            return final_items

        else:
            all_items = []
            queue = [normalized_virtual_path]
            while queue:
                current_path = queue.pop(0)
                try:
                    level_items = await _list_level_raw(current_path)
                    ignores = await self._get_ignore_set(io, current_path) if honor_skignore else set()

                    if current_path != normalized_virtual_path: # Add the dir entry itself
                        dir_host_path = self.box(current_path)
                        try: size, mtime = getsize(dir_host_path), getmtime(dir_host_path)
                        except OSError: size, mtime = -1, -1
                        all_items.append({
                            'name': posixpath.basename(current_path),
                            'path': current_path, 'type': 'dir', 'size': size, 'mtime': mtime
                        })

                    for item in level_items:
                        # Always filter standard ignorables unless show_all is specified
                        if not show_all and self._is_standard_ignorable(item['name']):
                            continue

                        # Add item to the results. In recursive mode, we show skignored items.
                        if item['type'] == 'file':
                            all_items.append(item)

                        # Only queue directories for recursion if they are not in the ignore list.
                        if item['type'] == 'dir':
                            if not (honor_skignore and item['name'] in ignores):
                                queue.append(item['path'])
                except (FileNotFoundError, NotADirectoryError) as e:
                    await io.error(f"Error during recursive list of {current_path}: {e}")
            return all_items

    async def get(self, io:Context, path:str):
        """Get file contents from the merged view."""
        file = self.box(path, io_context=io)
        if not await self.exists(io, path):
            await io.error(f'!! path not found: {path}')
            return None
        if not isfile(file):
            await io.error(f'!! not a file: {path}')
            return None
        if is_binary(file):
            await io.error(f'!! refusing binary file: {path}')
            return None
        with open(file, 'r', encoding='utf-8') as f:
            return f.read()

    async def get_raw(self, io:Context, path:str):
        """Get raw file contents as bytes from the merged view."""
        file = self.box(path, io_context=io)
        if not await self.exists(io, path):
            return None, False, f'path not found: {path}'
        if not isfile(file):
            return None, False, f'not a file: {path}'
        try:
            is_binary_file = is_binary(file)
            with open(file, 'rb') as f: content = f.read()
            return content, is_binary_file, None
        except Exception as e:
            return None, False, f'could not read file: {e}'
            
    # --- Higher-level FS Ops (should work w/o changes) ---

    async def get_motd(self, io: Context) -> str:
        motd_path_virtual = '/etc/motd'
        if not await self.exists(io, motd_path_virtual): return ""
        motd_path_host = self.box(motd_path_virtual, io_context=io)
        if isdir(motd_path_host):
            try:
                files = [i['name'] for i in await self.list_dir(io, motd_path_virtual) if i['type'] == 'file']
                if not files: return ""
                random_motd_path = posixpath.join(motd_path_virtual, random.choice(files))
                return await self.get(io, random_motd_path) or ""
            except Exception as e:
                await self.os.system.error(f"!! Error reading MOTD from dir: {e}")
                return ""
        return await self.get(io, motd_path_virtual) or ""

    async def get_room_list(self, io: Context) -> list:
        room_dir_virtual = '/var/room'
        if not await self.exists(io, room_dir_virtual): return []
        try:
            room_names = [i['name'] for i in await self.list_dir(io, room_dir_virtual) if i['type'] == 'dir']
        except (FileNotFoundError, NotADirectoryError):
            return []
        room_data = []
        for name in sorted(room_names):
            topic_path = posixpath.join(room_dir_virtual, name, 'topic')
            topic = (await self.get(io, topic_path) or "").strip()
            room_data.append({'name': name, 'topic': topic})
        return room_data