"""SMTP Envelope Sender Parser.

Parses RFC 5321 MAIL FROM and RCPT TO command arguments.
"""
from .core import EnvelopeCommand, parse_mail_from, parse_rcpt_to

__all__ = ["EnvelopeCommand", "parse_mail_from", "parse_rcpt_to"]
