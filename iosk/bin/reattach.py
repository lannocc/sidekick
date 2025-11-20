#!/usr/bin/env python
# bin/reattach.py

import asyncio
import posixpath
from sk.iosk.chat import Engagement

async def iocall(io, argv):
    """Reattach a user to a different device.

    Usage: reattach <device> [user]
           reattach --help

    <device>: The name of the device (e.g., 'dummy', 'google', 'openai/gpt-4).
              Corresponds to a path under /dev/.
    [user]: The username to reattach. If omitted, defaults to the current user.
    --help: Displays this help message.

    Special behavior for console devices ('/dev/console'):
    If a user is reattached to a console device that is already occupied,
    the two users will swap devices. The original console user will be
    attached to the device the other user was previously on.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not argv or len(argv) > 2:
        await io.error("!! reattach: requires 1 or 2 arguments: <device> [user]")
        return False

    device_name_input = argv[0]
    target_user_name = argv[1] if len(argv) > 1 else io.user

    # --- Initial Validation ---
    if target_user_name not in io.os.users.contexts:
        await io.error(f"!! reattach: user '{target_user_name}' is not logged in.")
        return False
    target_io = io.os.users.contexts[target_user_name]

    new_device_virtual_path = posixpath.join('/dev', device_name_input)
    if not await io.os.exists(io, new_device_virtual_path):
        await io.error(f"!! reattach: device '{device_name_input}' not found in /dev/.")
        return False

    # --- Job Creation: Normal reattach or a device swap ---
    jobs = []
    console_devices == ('/dev/console') #, '/dev/terminal')
    is_console_target = new_device_virtual_path in console_devices

    if is_console_target:
        current_console_io = None
        for user_io_obj in io.os.users.contexts.values():
            if user_io_obj.dev in console_devices:
                current_console_io = user_io_obj
                break

        # If we are targeting a console and another user is on it, it's a swap.
        if current_console_io and current_console_io.user != target_io.user:
            await io.print(f":: Console is occupied. Swapping devices for '{target_io.user}' and '{current_console_io.user}'.")

            source_user_device = target_io.dev
            console_user_device = current_console_io.dev

            jobs.append((target_io, console_user_device))
            jobs.append((current_console_io, source_user_device))
        else:
            # Normal reattach (e.g., no console user, or reattaching self to console).
            jobs.append((target_io, new_device_virtual_path))
    else:
        # Not targeting a console device, so it's a normal reattach.
        jobs.append((target_io, new_device_virtual_path))

    # --- Job Execution Loop ---
    overall_success = True
    for user_io_to_change, new_path in jobs:

        if user_io_to_change.dev == new_path:
            await io.print(f":: User '{user_io_to_change.user}' is already on '{new_path}'. No change needed.")
            continue

        await io.print(f":: Reattaching user '{user_io_to_change.user}' from '{user_io_to_change.dev}' to '{new_path}'...")

        old_device = user_io_to_change.dev
        was_bot = user_io_to_change.bot
        chat_instance = io.os.chat
        current_engagement = chat_instance.engagements.get(user_io_to_change.user) if chat_instance else None

        # Tear down old engagement if user was a bot
        if was_bot and current_engagement:
            current_engagement.enabled = False
            await io.print(f":: Old AI engagement for '{user_io_to_change.user}' disabled.")
            if chat_instance and user_io_to_change.user in chat_instance.engagements:
                del chat_instance.engagements[user_io_to_change.user]

        # Update user's device and flags
        user_io_to_change.dev = new_path
        user_io_to_change.su = new_path in console_devices
        user_io_to_change.bot = not user_io_to_change.su

        # Set up a new engagement if the new device is an AI bot
        if user_io_to_change.bot and chat_instance:
            new_engagement = Engagement(user_io_to_change.user)
            chat_instance.engagements[user_io_to_change.user] = new_engagement
            await new_engagement.ioset(user_io_to_change)

            device_name_for_mod = new_path.replace('/dev/', '', 1)
            mod_name_for_pymod = device_name_for_mod.replace('/', '.').replace('-', '_')

            potential_host_py_path = io.os.box(f"{new_path}.py", io_context=io)
            new_device_mod = io.os.pymod(f'dev.{mod_name_for_pymod}', potential_host_py_path)

            if not new_device_mod:
                await io.error(f"!! reattach: failed to load device module for '{device_name_for_mod}'.")
                await io.os.system.print(f":: {io.user} FAILED to reattach user '{user_io_to_change.user}' (module load failed)")
                user_io_to_change.dev = old_device # Revert
                if was_bot and current_engagement: chat_instance.engagements[user_io_to_change.user] = current_engagement
                overall_success = False
                continue

            trip_func = getattr(new_device_mod, 'trip', None)
            online_func = getattr(new_device_mod, 'online', None)

            if not trip_func:
                await io.error(f"!! reattach: device module '{device_name_for_mod}' is missing a 'trip' function.")
                await io.os.system.print(f":: {io.user} FAILED to reattach user '{user_io_to_change.user}' (no trip function)")
                user_io_to_change.dev = old_device # Revert
                if was_bot and current_engagement: chat_instance.engagements[user_io_to_change.user] = current_engagement
                overall_success = False
                continue

            if online_func:
                try:
                    if asyncio.iscoroutinefunction(online_func):
                        await online_func(user_io_to_change)
                    else:
                        online_func(user_io_to_change)
                except Exception as e:
                    await io.error(f"!! reattach: error calling online() for device '{device_name_for_mod}': {e}")
                    await io.os.system.print(f":: {io.user} FAILED to reattach user '{user_io_to_change.user}' (online() error)")
                    user_io_to_change.dev = old_device # Revert
                    if was_bot and current_engagement: chat_instance.engagements[user_io_to_change.user] = current_engagement
                    overall_success = False
                    continue

            new_engagement.trip = trip_func
            asyncio.create_task(new_engagement.engage())
            await io.print(f":: New AI engagement for '{user_io_to_change.user}' started with '{new_path}'.")

        elif not user_io_to_change.bot and chat_instance and user_io_to_change.user in chat_instance.engagements:
            chat_instance.engagements[user_io_to_change.user].enabled = False
            del chat_instance.engagements[user_io_to_change.user]
            await io.print(f":: AI engagement for '{user_io_to_change.user}' removed as they are now a console user.")

        if chat_instance and user_io_to_change.user != io.user:
            await chat_instance.send(io.user, f":: Administrator reattached '{user_io_to_change.user}' to '{new_path}'", sys=True)

        await io.print(f":: Successfully reattached '{user_io_to_change.user}' to '{new_path}'.")
        await io.os.system.print(f":: {io.user} reattached user '{user_io_to_change.user}' from '{old_device}' to '{new_path}'")

    # --- Final Reporting ---
    if len(jobs) > 1:
        if overall_success:
            await io.print(":: Swap complete.")
        else:
            await io.error("!! Device swap failed. System may be in an inconsistent state.")

    return overall_success

