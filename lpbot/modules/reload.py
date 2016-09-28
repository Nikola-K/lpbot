# -*- coding: utf-8 -*-

# Copyright 2008, Sean B. Palmer, inamidst.com
# Copyright 2014, Nikola Kovacevic, <nikolak@outlook.com>
# Licensed under the Eiffel Forum License 2.

import sys
import os.path
import time
import imp
import subprocess

from lpbot.tools import owner_only
import lpbot.module
from lpbot import logger

log = logger.get_logger()


@lpbot.module.nickname_commands("reload")
@lpbot.module.priority("low")
@lpbot.module.thread(False)
@owner_only
def f_reload(bot, trigger):
    """Reloads a module, for use by admins only."""
    if not trigger.admin:
        return

    name = trigger.group(2)
    if name == bot.config.owner:
        return bot.reply('What?')

    if not name or name == '*':
        bot.callables = None
        bot.commands = None
        bot.setup()
        return bot.reply('Reloading all done!')

    if name not in sys.modules:
        return bot.reply('%s: not loaded, try the `load` command' % name)

    old_module = sys.modules[name]

    old_callables = {}
    for obj_name, obj in vars(old_module).items():
        if bot.is_callable(obj) or bot.is_shutdown(obj):
            old_callables[obj_name] = obj

    bot.unregister(old_callables)
    # Also remove all references to willie callables from top level of the
    # module, so that they will not get loaded again if reloading the
    # module does not override them.
    for obj_name in list(old_callables.keys()):
        delattr(old_module, obj_name)

    # Also delete the setup function
    if hasattr(old_module, "setup"):
        delattr(old_module, "setup")

    # Thanks to moot for prodding me on this
    path = old_module.__file__
    if path.endswith('.pyc') or path.endswith('.pyo'):
        path = path[:-1]
    if not os.path.isfile(path):
        return bot.reply('Found %s, but not the source file' % name)

    module = imp.load_source(name, path)
    sys.modules[name] = module
    if hasattr(module, 'setup'):
        module.setup(bot)

    mtime = os.path.getmtime(module.__file__)
    modified = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mtime))

    bot.register(vars(module))
    bot.bind_commands()

    bot.reply('%r (version: %s)' % (module, modified))


@lpbot.module.nickname_commands('update')
@owner_only
def f_update(bot, trigger):
    """Pulls the latest versions of all modules from Git"""
    if not trigger.admin:
        return

    proc = subprocess.Popen('/usr/bin/git pull',
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=True)
    resp = proc.communicate()[0].decode('utf-8')
    log.info("Update response: \n{}".format(resp))

    resp_lines = resp.splitlines()

    update_info = " ".join(resp_lines[:2])
    bot.say(update_info)

    files_update = resp_lines[2:-1]
    if len(files_update)<=3:
        for file_status in files_update:
            bot.say(file_status.strip())

    update_summary = resp_lines[-1:][0].strip()
    bot.say(update_summary)

    f_reload(bot, trigger)


@lpbot.module.nickname_commands("load")
@lpbot.module.priority("low")
@lpbot.module.thread(False)
@owner_only
def f_load(bot, trigger):
    """Loads a module, for use by admins only."""
    if not trigger.admin:
        return

    module_name = trigger.group(2)
    path = ''
    if module_name == bot.config.owner:
        return bot.reply('What?')

    if module_name in sys.modules:
        return bot.reply('Module already loaded, use reload')

    mods = bot.config.enumerate_modules()
    for name in mods:
        if name == trigger.group(2):
            path = mods[name]
    if not os.path.isfile(path):
        return bot.reply('Module %s not found' % module_name)

    module = imp.load_source(module_name, path)
    mtime = os.path.getmtime(module.__file__)
    modified = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mtime))
    if hasattr(module, 'setup'):
        module.setup(bot)
    bot.register(vars(module))
    bot.bind_commands()

    bot.reply('%r (version: %s)' % (module, modified))


# Catch PM based messages
@lpbot.module.commands("reload")
@lpbot.module.priority("low")
@lpbot.module.thread(False)
@owner_only
def pm_f_reload(bot, trigger):
    """Wrapper for allowing delivery of .reload command via PM"""
    if trigger.is_privmsg:
        f_reload(bot, trigger)


@lpbot.module.commands('update')
@owner_only
def pm_f_update(bot, trigger):
    """Wrapper for allowing delivery of .update command via PM"""
    if trigger.is_privmsg:
        f_update(bot, trigger)


@lpbot.module.commands("load")
@lpbot.module.priority("low")
@lpbot.module.thread(False)
@owner_only
def pm_f_load(bot, trigger):
    """Wrapper for allowing delivery of .load command via PM"""
    if trigger.is_privmsg:
        f_load(bot, trigger)
