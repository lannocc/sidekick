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
    """Manages all virtual filesystem operations for the IOSK kernel."""
    def __init__(self, kernel):
        self.os = kernel

    def box(self, virtual_path_input: str, io_context=None) -> str:
        """
        Sandboxes a given virtual path to the host filesystem, handling OS-specific separators.
        If io_context is provided and the path is relative, it resolves it relative to io_context.pwd.
        Returns the absolute host filesystem path.
        """
        # Step 1: Determine the effective virtual path using posixpath for virtual FS logic.
        effective_virtual_path = virtual_path_input
        if io_context and io_context.pwd and not posixpath.isabs(virtual_path_input):
            # Path is relative, resolve it against the current working directory.
            effective_virtual_path = posixpath.join(io_context.pwd, virtual_path_input)

        # Step 2: Normalize the virtual path to handle '.', '..', and multiple slashes using posixpath.
        normalized_virtual_path = posixpath.normpath(effective_virtual_path)

        # Step 3: Convert the virtual path to a host path.
        # Strip the leading '/' from the virtual path for os.path.join.
        path_relative_to_virtual_root = normalized_virtual_path.lstrip('/')

        # Split the sanitized virtual path by its separator '/' and join the components
        # to the host root path using the host OS's native separator via os.path.join.
        # This is the bridge between the virtual (posix) and host filesystems.
        path_components = path_relative_to_virtual_root.split('/')
        host_path = os.path.join(self.os.root, *path_components)

        # Return the absolute path on the host filesystem for consistency.
        return os.path.abspath(host_path)

    async def get_motd(self, io: Context) -> str:
        """
        Gets the Message of the Day.
        If /etc/motd is a file, returns its content.
        If /etc/motd is a directory, returns the content of a randomly selected file from it.
        """
        motd_path_virtual = '/etc/motd'
        motd_path_host = self.box(motd_path_virtual, io_context=io)

        if not await self.exists(io, motd_path_virtual):
            return ""  # No MOTD found

        if isdir(motd_path_host):
            try:
                # Use kernel's list_dir to get contents
                dir_contents = await self.list_dir(io, motd_path_virtual)

                # Filter for files only
                files = [item['name'] for item in dir_contents if item['type'] == 'file']

                if not files:
                    return ""  # Directory is empty

                random_motd_filename = random.choice(files)
                random_motd_path_virtual = posixpath.join(motd_path_virtual, random_motd_filename)

                # Now, use self.get() to read the file content.
                content = await self.get(io, random_motd_path_virtual)
                return content or ""

            except Exception as e:
                await self.os.system.error(f"!! Error reading MOTD from directory {motd_path_virtual}: {e}")
                traceback.print_exc()
                return ""

        elif isfile(motd_path_host):
            # It's a file, use self.get() as before.
            content = await self.get(io, motd_path_virtual)
            return content or ""

        else:
            # It exists but is not a file or directory.
            return ""

    async def get_room_list(self, io: Context) -> list:
        """
        Lists all created rooms on the local system.
        Returns a list of dictionaries, each with 'name' and 'topic'.
        """
        room_dir_virtual = '/var/room'
        room_dir_host = self.box(room_dir_virtual, io_context=io)

        if not exists(room_dir_host) or not isdir(room_dir_host):
            return []

        try:
            room_names = sorted([
                name for name in os.listdir(room_dir_host)
                if isdir(os.path.join(room_dir_host, name))
            ])
        except OSError:
            return []

        room_data = []
        for name in room_names:
            topic_path = posixpath.join(room_dir_virtual, name, 'topic')
            topic = ""
            if await self.exists(io, topic_path):
                 topic_content = await self.get(io, topic_path)
                 if topic_content:
                     topic = topic_content.strip()
            room_data.append({'name': name, 'topic': topic})

        return room_data

    async def exists(self, io:Context, path:str):
        """Test if path exists, considering both physical files and Python modules."""
        # 1. Check for physical file/directory existence on the sandboxed filesystem.
        file_on_host = self.box(path, io_context=io)
        if exists(file_on_host):
            return True

        # 2. Check if a corresponding Python module file exists in the sandbox.
        # This handles cases like `exists('/bin/ls')` being true if `root/bin/ls.py` exists.
        py_file_on_host = self.box(f'{path}.py', io_context=io)
        if exists(py_file_on_host) and isfile(py_file_on_host):
            return True

        # 3. Check for a "built-in" Python module that is part of the iosk source
        # but not present as a file in the sandboxed filesystem (e.g., /dev/google).

        # First, resolve the path to an absolute virtual path to be safe.
        if io and io.pwd and not path.startswith('/'):
            virtual_path = posixpath.normpath(posixpath.join(io.pwd, path))
        else:
            virtual_path = posixpath.normpath(path)

        # Convert virtual path to module path suffix, e.g., '/dev/google' -> 'dev.google'
        mod_suffix = virtual_path.lstrip('/')
        if not mod_suffix:
            return False # Path was just '/'

        # The convention is to find modules relative to the 'iosk' package.
        # Example: /dev/google -> dev.google -> iosk.dev.google
        full_mod_name = f'iosk.{mod_suffix.replace("/", ".").replace("-", "_")}'

        try:
            # Use find_spec to check for module existence without importing it.
            spec = importlib.util.find_spec(full_mod_name)
            if spec is not None:
                return True
        except (ModuleNotFoundError, ValueError):
            # An invalid module path could raise an error.
            pass

        return False

    async def create(self, io:Context, path:str):
        """Create new (empty) file."""
        file = self.box(path, io_context=io)
        if exists(file): return True # Already exists, idempotent

        with open(file, 'w') as f:
            pass
        return True

    async def copy(self, io:Context, from_path:str, to_path:str):
        """Copy file."""
        from_file = self.box(from_path, io_context=io)
        if not exists(from_file):
            await io.error(f'!! copy from path not found: {from_path}')
            return False

        # Ensure the destination directory exists for the target file
        to_file_host = self.box(to_path, io_context=io)
        to_dir_host = os.path.dirname(to_file_host)
        if not exists(to_dir_host):
            try:
                os.makedirs(to_dir_host)
            except OSError as e:
                await io.error(f"!! failed to create destination directory for copy '{to_path}': {e}")
                return False

        shutil.copy(from_file, to_file_host)
        return True

    async def move(self, io:Context, from_path:str, to_path:str):
        """Move file/directory."""
        from_file = self.box(from_path, io_context=io)
        if not exists(from_file):
            await io.error(f'!! move from path not found: {from_path}')
            return False

        # Ensure the destination directory exists for the target file
        to_file_host = self.box(to_path, io_context=io)
        to_dir_host = os.path.dirname(to_file_host)
        if not exists(to_dir_host):
            try:
                os.makedirs(to_dir_host)
            except OSError as e:
                await io.error(f"!! failed to create destination directory for move '{to_path}': {e}")
                return False

        shutil.move(from_file, to_file_host) # shutil.move handles both file and dir
        return True

    async def remove(self, io:Context, path:str):
        """Remove file."""
        file = self.box(path, io_context=io)
        if not exists(file):
            await io.error(f'!! remove path not found: {path}')
            return False

        if isdir(file): # Prevent removing a directory with os.remove
            await io.error(f'!! path is a directory, use rmdir: {path}')
            return False

        os.remove(file)
        return True

    async def create_dir(self, io:Context, path:str, parents=False):
        """Create new directory."""
        folder = self.box(path, io_context=io)
        if exists(folder):
            await io.error(f'!! path already exists: {path}')
            return False # Changed to False as it already exists, not an error but not 'created new'

        try:
            if parents: os.makedirs(folder)
            else: os.mkdir(folder)
            return True
        except OSError as e:
            await io.error(f"!! failed to create directory '{path}': {e}")
            return False

    async def remove_dir(self, io:Context, path:str):
        """Remove directory."""
        folder = self.box(path, io_context=io)
        if not exists(folder):
            await io.error(f'!! remove dir path not found: {path}')
            return False
        if not isdir(folder):
            await io.error(f'!! path is not a directory: {path}')
            return False

        try:
            os.rmdir(folder)
            return True
        except OSError as e:
            await io.error(f"!! failed to remove directory '{path}': {e}")
            return False

    async def list_dir(self, io: Context, path: str, recursive: bool = False) -> list:
        """Lists the contents of a directory in the sandbox, optionally recursively."""
        host_path = self.box(path, io_context=io)
        if not exists(host_path):
            raise FileNotFoundError(f"Path not found: {path}")
        if not isdir(host_path):
            raise NotADirectoryError(f"Path is not a directory: {path}")

        listing = []
        try:
            if recursive:
                for root, dirs, files in os.walk(host_path, topdown=True):
                    # Sort dirs and files to ensure consistent output
                    dirs.sort()
                    files.sort()
                    # Convert host root path back to virtual path for this level
                    relative_path_from_start = os.path.relpath(root, host_path)
                    if relative_path_from_start == '.':
                        virtual_root = path
                    else:
                        # Ensure we use POSIX separators for the virtual path
                        virtual_root = posixpath.join(path, *relative_path_from_start.split(os.sep))

                    # Process all files at the current level
                    for item_name in files:
                        item_host_path = os.path.join(root, item_name)
                        item_virtual_path = posixpath.join(virtual_root, item_name)
                        try:
                            size = getsize(item_host_path)
                            mtime = getmtime(item_host_path)
                        except OSError:
                            size = -1
                            mtime = -1
                        listing.append({'name': item_name, 'path': item_virtual_path, 'type': 'file', 'size': size, 'mtime': mtime})

                    # Process all subdirectories at the current level
                    for item_name in dirs:
                        item_host_path = os.path.join(root, item_name)
                        item_virtual_path = posixpath.join(virtual_root, item_name)
                        try:
                            size = getsize(item_host_path)
                            mtime = getmtime(item_host_path)
                        except OSError:
                            size = -1
                            mtime = -1
                        listing.append({'name': item_name, 'path': item_virtual_path, 'type': 'dir', 'size': size, 'mtime': mtime})
            else:
                for item_name in sorted(os.listdir(host_path)):
                    full_item_path_host = os.path.join(host_path, item_name)
                    full_item_path_virtual = posixpath.join(path, item_name)
                    item_type = 'dir' if isdir(full_item_path_host) else 'file'
                    try:
                        size = getsize(full_item_path_host)
                        mtime = getmtime(full_item_path_host)
                    except OSError:
                        size = -1
                        mtime = -1
                    listing.append({
                        'name': item_name,
                        'path': full_item_path_virtual,
                        'type': item_type,
                        'size': size,
                        'mtime': mtime
                    })
        except OSError as e:
            await io.error(f"Error reading directory {path}: {e}")
            raise
        return listing

    async def get(self, io:Context, path:str):
        """Get file contents."""
        file = self.box(path, io_context=io)
        if not exists(file):
            await io.error(f'!! path not found: {path}')
            return None # Return None on error

        if not isfile(file):
            await io.error(f'!! not a file: {path}')
            return None # Return None on error

        if is_binary(file):
            await io.error(f'!! refusing binary file: {path}')
            return None # Return None on error

        with open(file, 'r', encoding='utf-8') as file:
            return file.read()

    async def get_raw(self, io:Context, path:str):
        """Get raw file contents as bytes, and determine if it's binary."""
        file = self.box(path, io_context=io)
        if not exists(file):
            error_msg = f'path not found: {path}'
            return None, False, error_msg

        if not isfile(file):
            error_msg = f'not a file: {path}'
            return None, False, error_msg
        
        try:
            is_binary_file = is_binary(file)
            with open(file, 'rb') as f:
                content = f.read()
            return content, is_binary_file, None
        except Exception as e:
            error_msg = f'could not read file: {e}'
            return None, False, error_msg