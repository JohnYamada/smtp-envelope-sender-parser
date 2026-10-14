"""Core parsing logic for SMTP MAIL FROM and RCPT TO commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


class EnvelopeParseError(ValueError):
    """Raised when a command does not conform to RFC 5321 syntax."""


@dataclass
class EnvelopeCommand:
    """Represents a parsed MAIL FROM or RCPT TO command.

    Attributes:
        address: The extracted mailbox or null sender ("" for "<>").
        parameters: ESMTP key=value parameters following the address,
            with keys lowercased. Empty dict if none were present.
        source_route: The list of intermediate hosts in a source route
            path (e.g. ["a", "b"] for "<@a,@b:addr>"). Empty for
            non-source-routed addresses.
    """
    address: str
    parameters: Dict[str, str] = field(default_factory=dict)
    source_route: List[str] = field(default_factory=list)


def _split_command(text: str, verbs: List[str]) -> str:
    """Validate and strip the command verb prefix, case-insensitively."""
    stripped = text.strip()
    lowered = stripped.lower()
    # Case-insensitive verb matching per RFC 5321 Section 2.4.
    # The verb may be followed by a colon and/or whitespace.
    if lowered in verbs:
        raise EnvelopeParseError(f"Command is missing its argument: {text!r}")
    for verb in verbs:
        prefix = verb + ":"
        if lowered.startswith(prefix):
            return stripped[len(prefix):].strip()
    for verb in verbs:
        prefix = verb + " "
        if lowered.startswith(prefix):
            return stripped[len(prefix):].strip()
    raise EnvelopeParseError(f"Unrecognized command verb in: {text!r}")


def _split_path_and_params(payload: str) -> str:
    """Split the payload into the path and the trailing parameter string.

    Returns only the path portion. Raises if parameters appear before
    the closing bracket, which violates the strict ordering required by
    the extended MAIL/RCPT grammar.
    """
    if not payload.startswith("<"):
        raise EnvelopeParseError(
            f"Path must be enclosed in angle brackets: {payload!r}"
        )
    # The path is enclosed in <...>. Parameters come strictly after.
    close_index = payload.find(">")
    if close_index == -1:
        raise EnvelopeParseError(f"Unterminated angle bracket in path: {payload!r}")
    path_part = payload[: close_index + 1]
    remainder = payload[close_index + 1 :].strip()
    if remainder:
        # RFC 5321 Section 4.1.2: parameters appear after the path, separated
        # by space. Any non-space before the closing bracket is part of the path.
        # If there is unexpected trailing text, the caller validates it as params.
        _parse_parameters(remainder)
    return path_part


def _parse_path(path_part: str) -> EnvelopeCommand:
    """Parse the <...> path, extracting the address and any source route.

    RFC 5321 Section 4.1.2 defines the reverse-path and forward-path. A
    path may begin with a source route: a comma-separated list of hosts
    prefixed with "@", terminated by a colon, before the final mailbox.
    Source routes are deprecated but must still be parsed.
    """
    if not (path_part.startswith("<") and path_part.endswith(">")):
        raise EnvelopeParseError(f"Invalid path format: {path_part!r}")
    inner = path_part[1:-1]

    # The null sender path "<>" yields an empty address.
    if inner == "":
        return EnvelopeCommand(address="")

    # Source route detection: the path is a sequence of "@host" entries
    # separated by commas, followed by a colon, then the final address.
    if inner.startswith("@"):
        colon_idx = inner.find(":")
        if colon_idx == -1:
            raise EnvelopeParseError(
                f"Source route present but missing terminating colon: {path_part!r}"
            )
        route_part = inner[:colon_idx]
        address = inner[colon_idx + 1 :]
        # Split on commas. Empty host entries (e.g. "a,,b") are invalid.
        raw_hosts = route_part.split(",")
        route = []
        for host in raw_hosts:
            h = host.strip()
            if not h.startswith("@"):
                raise EnvelopeParseError(
                    f"Source route host missing leading '@': {host!r}"
                )
            host_name = h[1:].strip()
            if not host_name:
                raise EnvelopeParseError(
                    f"Source route contains an empty host: {path_part!r}"
                )
            route.append(host_name)
        return EnvelopeCommand(address=address, source_route=route)

    # A colon in a non-source-routed path is invalid per RFC 5321.
    if ":" in inner:
        raise EnvelopeParseError(f"Invalid path format: {path_part!r}")

    return EnvelopeCommand(address=inner)


def _parse_parameters(text: str) -> Dict[str, str]:
    """Parse ESMTP MAIL/RCPT parameters.

    Parameters follow the path, separated by whitespace. Each is a
    keyword=value pair. The keyword is case-insensitive; we store it
    lowercased. The value is optional in the general grammar, but
    common extensions (SIZE, NOTIFY, ORCPT) require it. We accept a
    missing value to stay true to the base syntax and yield the empty
    string for it.
    """
    params: Dict[str, str] = {}
    tokens = text.split()
    for token in tokens:
        if "=" not in token:
            raise EnvelopeParseError(
                f"Invalid parameter (missing '='): {token!r}"
            )
        key, sep, value = token.partition("=")
        if not key:
            raise EnvelopeParseError(f"Parameter has empty keyword: {token!r}")
        params[key.lower()] = value
    return params


def _parse_command(text: str, verbs: List[str]) -> EnvelopeCommand:
    """Full pipeline: verb strip, path/param split, path parse, param parse."""
    payload = _split_command(text, verbs)
    path_part = _split_path_and_params(payload)
    cmd = _parse_path(path_part)

    # Extract the remainder after the path to populate parameters.
    close_index = payload.find(">")
    remainder = payload[close_index + 1 :].strip()
    if remainder:
        cmd.parameters = _parse_parameters(remainder)
    return cmd


def parse_mail_from(text: str) -> EnvelopeCommand:
    """Parse a MAIL FROM command string per RFC 5321."""
    return _parse_command(text, ["mail from"])


def parse_rcpt_to(text: str) -> EnvelopeCommand:
    """Parse a RCPT TO command string per RFC 5321."""
    return _parse_command(text, ["rcpt to"])
