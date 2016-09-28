# -*- coding: utf-8 -*-

import re
import sys

import lpbot.tools


class PreTrigger:
    """A parsed message from the server, which has not been matched against
    any rules."""
    component_regex = re.compile(r'([^!]*)!?([^@]*)@?(.*)')
    intent_regex = re.compile('\x01(\\S+) (.*)\x01')

    def __init__(self, own_nick, line):
        """own_nick is the bot's nick, needed to correctly parse sender.
        line is the full line from the server."""
        line = line.strip('\r')
        self.line = line

        # Break off IRCv3 message tags, if present
        self.tags = {}
        if line.startswith('@'):
            tagstring, line = line.split(' ', 1)
            for tag in tagstring[1:].split(';'):
                tag = tag.split('=', 1)
                if len(tag) > 1:
                    self.tags[tag[0]] = tag[1]
                else:
                    self.tags[tag[0]] = None

        # TODO note what this is doing and why
        if line.startswith(':'):
            self.hostmask, line = line[1:].split(' ', 1)
        else:
            self.hostmask = None

        # TODO note what this is doing and why
        if ' :' in line:
            argstr, text = line.split(' :', 1)
            self.args = argstr.split(' ')
            self.args.append(text)
        else:
            self.args = line.split(' ')
            self.text = self.args[-1]

        self.event = self.args[0]
        components = PreTrigger.component_regex.match(self.hostmask or '').groups()
        self.nick, self.user, self.host = components
        self.nick = lpbot.tools.Identifier(self.nick)

        # If we have more than one argument, the second one is the sender
        if len(self.args) > 1:
            target = lpbot.tools.Identifier(self.args[1])
        else:
            target = None

        # Unless we're messaging the bot directly, in which case that second
        # arg will be our bot's name.
        if target and target.lower() == own_nick.lower():
            target = self.nick
        self.sender = target

        # Parse CTCP into a form consistent with IRCv3 intents
        if self.event == 'PRIVMSG' or self.event == 'NOTICE':
            intent_match = PreTrigger.intent_regex.match(self.args[-1])
            if intent_match:
                self.tags['intent'], self.args[-1] = intent_match.groups()


class Trigger(str):
    """A line from the server, which has matched a callable's rules.

    Note that CTCP messages (`PRIVMSG`es and `NOTICE`es which start and end
    with `'\\x01'`) will have the `'\\x01'` bytes stripped, and the command
    (e.g. `ACTION`) placed mapped to the `'intent'` key in `Trigger.tags`.
    """

    def __new__(cls, config, message, match):
        self = str.__new__(cls, message.args[-1])
        self.sender = message.sender
        # TODO docstring for sender
        self.raw = message.line
        """The entire message, as sent from the server. This includes the CTCP
        \\x01 bytes and command, if they were included."""

        self.is_privmsg = message.sender.is_nick()
        """True if the trigger is from a user, False if it's from a channel."""

        self.hostmask = message.hostmask
        """
        Hostmask of the person who sent the message in the form
        <nick>!<user>@<host>
        """
        self.user = message.user
        """Local username of the person who sent the message"""
        self.nick = message.nick
        """The ``Identifier`` of the person who sent the message."""
        self.host = message.host
        """The hostname of the person who sent the message"""
        self.event = message.event
        """
        The IRC event (e.g. ``PRIVMSG`` or ``MODE``) which triggered the
        message."""
        self.match = match
        """
        The regular expression ``MatchObject_`` for the triggering line.
        .. _MatchObject: http://docs.python.org/library/re.html#match-objects
        """
        self.group = match.group
        """The ``group`` function of the ``match`` attribute.

        See Python ``re_`` documentation for details."""
        self.groups = match.groups
        """The ``groups`` function of the ``match`` attribute.

        See Python ``re_`` documentation for details."""
        self.args = message.args
        """
        A tuple containing each of the arguments to an event. These are the
        strings passed between the event name and the colon. For example,
        setting ``mode -m`` on the channel ``#example``, args would be
        ``('#example', '-m')``
        """
        self.tags = message.tags
        """A map of the IRCv3 message tags on the message."""

        def match_host_or_nick(pattern):
            pattern = lpbot.tools.get_hostmask_regex(pattern)
            return bool(
                pattern.match(self.nick) or
                pattern.match('@'.join((self.nick, self.host)))
            )

        self.admin = any(match_host_or_nick(item)
                         for item in config.core.get_list('admins'))
        """
        True if the nick which triggered the command is one of the bot's admins.
        """
        #self.owner = match_host_or_nick(config.core.owner) and lpbot.tools.lpbotMemory().get('owner_auth', False)
        """True if the nick which triggered the command is the bot's owner."""
        self.admin = self.admin #or self.owner

        return self
