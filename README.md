# smtp-envelope-sender-parser

Parses RFC 5321 MAIL FROM and RCPT TO command arguments, extracting the address, optional ESMTP parameters, and stripping deprecated source-routes.

```python
from smtp_envelope_sender_parser import parse_mail_from, parse_rcpt_to, EnvelopeCommand

result = parse_mail_from("MAIL FROM:<sender@host.test> SIZE=42 NOTIFY=NEVER")
# result.address -> "sender@host.test"
# result.parameters -> {"size": "42", "notify": "NEVER"}
# result.source_route -> []

result = parse_rcpt_to("RCPT TO:<@route1,@route2:final@host.test>")
# result.address -> "final@host.test"
# result.source_route -> ["route1", "route2"]
```

## Why this exists

A real SMTP server must reply to MAIL FROM and RCPT TO by parsing the line exactly as the spec demands: angle brackets, whitespace before parameters, keyword=value pairs separated by single spaces, and the officially deprecated but still reachable source-route syntax (`<@a,@b:final@host>`). This library is a single-purpose, zero-dependency parser for those rules.

The trade-off: we do not validate that the local-part is a sensible mailbox, nor that the domain has DNS records. RFC 5321 lets an SMTP server accept any syntactically correct path; deeper validation is a policy decision and out of scope here.

## Edge cases

RFC 5321 allows the address angle brackets to be empty, as in `MAIL FROM:<>`. This is the null sender address used for delivery status notifications. The parser accepts this and returns an empty string for `address`.
