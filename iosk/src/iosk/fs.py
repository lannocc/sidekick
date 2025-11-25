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
        dir_name, file_name = posixpath.split(normalized_virtual_path)
        tombstone_dir_host = self._to_host_path(self.os.workspace_root, dir_name)

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
        Sandboxes a virtual path for reading, checking the workspace first, then the distribution.
        Returns the absolute host filesystem path to the file that should be used.
        """
        normalized_virtual_path = self._resolve_virtual_path(virtual_path_input, io_context)
        
        # 1. Check Workspace
        workspace_host_path = self._to_host_path(self.os.workspace_root, normalized_virtual_path)
        if exists(workspace_host_path):
            return workspace_host_path
        
        # Check for .py variant in workspace
        if isfile(workspace_host_path + '.py'):
            return workspace_host_path + '.py'
            
        # 2. Fallback to Distribution
        dist_host_path = self._to_host_path(self.os.dist_root, normalized_virtual_path)
        
        # Check for .py variant in distribution
        if not exists(dist_host_path) and isfile(dist_host_path + '.py'):
            return dist_host_path + '.py'
            
        return dist_host_path

    def box_for_write(self, virtual_path_input: str, io_context=None) -> str:
        """
        Sandboxes a virtual path for writing, ALWAYS targeting the workspace.
        Returns the absolute host filesystem path where the write should occur.
        """
        normalized_virtual_path = self._resolve_virtual_path(virtual_path_input, io_context)
        return self._to_host_path(self.os.workspace_root, normalized_virtual_path)

    # --- Core FS API ---

    async def exists(self, io:Context, path:str):
        """Test if path exists in the merged filesystem view."""
        normalized_virtual_path = self._resolve_virtual_path(path, io_context=io)

        # Rule 2a: Files with .iosk. prefix must never appear to exist.
        if posixpath.basename(normalized_virtual_path).startswith('.iosk.'):
            return False

        # 1. Check for a tombstone. If it exists, the file is considered deleted.
        dir_name, file_name = posixpath.split(normalized_virtual_path)
        tombstone_name = f'.iosk.rm.{file_name}'
        tombstone_py_name = f'.iosk.rm.{file_name}.py'
        tombstone_dir_host = self._to_host_path(self.os.workspace_root, dir_name)
        
        if isfile(os.path.join(tombstone_dir_host, tombstone_name)) or \
           isfile(os.path.join(tombstone_dir_host, tombstone_py_name)):
            return False

        # 2. Check for the physical file/directory in workspace, then distribution.
        workspace_host_path = self._to_host_path(self.os.workspace_root, normalized_virtual_path)
        if exists(workspace_host_path):
            return True
        dist_host_path = self._to_host_path(self.os.dist_root, normalized_virtual_path)
        if exists(dist_host_path):
            return True

        # 3. Check for the .py version for executables etc.
        if isfile(workspace_host_path + '.py') or isfile(dist_host_path + '.py'):
            return True
            
        # 4. Check for built-in python modules
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
        """Removes a file. If in workspace, it's deleted. If only in distribution, creates a tombstone."""
        if not await self.exists(io, path): # Checks merged view, respecting tombstones
            await io.error(f'!! remove path not found: {path}')
            return False

        resolved_host_path = self.box(path, io_context=io)
        if isdir(resolved_host_path):
            await io.error(f'!! path is a directory, use rmdir: {path}')
            return False

        normalized_virtual_path = self._resolve_virtual_path(path, io_context=io)
        workspace_path = self._to_host_path(self.os.workspace_root, normalized_virtual_path)
        dist_path = self._to_host_path(self.os.dist_root, normalized_virtual_path)

        # Also check for .py versions
        workspace_py_path = workspace_path + '.py'
        dist_py_path = dist_path + '.py'
        
        # If it exists in the workspace, delete it.
        if isfile(workspace_py_path):
            os.remove(workspace_py_path)
            return True
        if isfile(workspace_path):
            os.remove(workspace_path)
            return True

        # If it only exists in the distribution, create a tombstone.
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

        dir_name, file_name = posixpath.split(normalized_virtual_path)
        tombstone_dir_host = self._to_host_path(self.os.workspace_root, dir_name)

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

    async def list_dir(self, io: Context, path: str, recursive: bool = False) -> list:
        """Lists directory contents, merging workspace and distribution, handling tombstones."""
        normalized_virtual_path = self._resolve_virtual_path(path, io_context=io)
        workspace_dir_host = self._to_host_path(self.os.workspace_root, normalized_virtual_path)
        dist_dir_host = self._to_host_path(self.os.dist_root, normalized_virtual_path)
        
        # Check if the path exists as a directory in either layer
        is_ws_dir = isdir(workspace_dir_host)
        is_dist_dir = isdir(dist_dir_host)
        
        if not is_ws_dir and not is_dist_dir:
             if exists(workspace_dir_host) or exists(dist_dir_host):
                 raise NotADirectoryError(f"Path is not a directory: {path}")
             else:
                 raise FileNotFoundError(f"Path not found: {path}")

        async def _list_level(virtual_base_path):
            results = {}
            tombstones = set()

            # Layer 1: Distribution
            dist_path = self._to_host_path(self.os.dist_root, virtual_base_path)
            if isdir(dist_path):
                for name in os.listdir(dist_path):
                    # Rule 2a: Hide .iosk. files
                    if name.startswith('.iosk.'):
                        continue
                    host_p = os.path.join(dist_path, name)
                    results[name] = {'name': name, 'type': 'dir' if isdir(host_p) else 'file'}

            # Layer 2: Workspace
            ws_path = self._to_host_path(self.os.workspace_root, virtual_base_path)
            if isdir(ws_path):
                for name in os.listdir(ws_path):
                    # Rule 1: Check for new tombstone prefix
                    if name.startswith('.iosk.rm.'):
                        tombstones.add(name[9:])
                        continue
                    # Rule 2a: Hide .iosk. files
                    if name.startswith('.iosk.'):
                        continue
                    host_p = os.path.join(ws_path, name)
                    results[name] = {'name': name, 'type': 'dir' if isdir(host_p) else 'file'}

            # Filter and format
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
            return await _list_level(normalized_virtual_path)
        else:
            all_items = []
            queue = [normalized_virtual_path]
            while queue:
                current_path = queue.pop(0)
                try:
                    level_items = await _list_level(current_path)
                    if current_path != normalized_virtual_path: # Add the dir entry itself
                        dir_host_path = self.box(current_path)
                        try: size, mtime = getsize(dir_host_path), getmtime(dir_host_path)
                        except OSError: size, mtime = -1, -1
                        all_items.append({
                            'name': posixpath.basename(current_path),
                            'path': current_path, 'type': 'dir', 'size': size, 'mtime': mtime
                        })

                    for item in level_items:
                        if item['type'] == 'dir':
                            queue.append(item['path'])
                        else: # is a file
                           all_items.append(item)
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