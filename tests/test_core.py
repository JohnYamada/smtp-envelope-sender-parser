import unittest

from smtp_envelope_sender_parser import parse_mail_from, parse_rcpt_to, EnvelopeCommand
from smtp_envelope_sender_parser.core import EnvelopeParseError


class TestMailFrom(unittest.TestCase):
    def test_basic(self):
        cmd = parse_mail_from("MAIL FROM:<sender@host.test>")
        self.assertEqual(cmd.address, "sender@host.test")
        self.assertEqual(cmd.parameters, {})
        self.assertEqual(cmd.source_route, [])
        self.assertIsInstance(cmd, EnvelopeCommand)

    def test_case_insensitive_verb(self):
        cmd = parse_mail_from("mail from:<sender@host.test>")
        self.assertEqual(cmd.address, "sender@host.test")

    def test_with_parameters(self):
        cmd = parse_mail_from("MAIL FROM:<sender@host.test> SIZE=42 NOTIFY=NEVER")
        self.assertEqual(cmd.address, "sender@host.test")
        self.assertEqual(cmd.parameters, {"size": "42", "notify": "NEVER"})

    def test_parameter_keys_are_case_insensitive(self):
        cmd = parse_mail_from("MAIL FROM:<sender@host.test> Size=42")
        self.assertEqual(cmd.parameters, {"size": "42"})

    def test_null_sender(self):
        cmd = parse_mail_from("MAIL FROM:<>")
        self.assertEqual(cmd.address, "")
        self.assertEqual(cmd.source_route, [])

    def test_null_sender_with_parameters(self):
        cmd = parse_mail_from("MAIL FROM:<> SIZE=100")
        self.assertEqual(cmd.address, "")
        self.assertEqual(cmd.parameters, {"size": "100"})

    def test_extra_whitespace(self):
        cmd = parse_mail_from("MAIL FROM:   <sender@host.test>   BODY=7BIT")
        self.assertEqual(cmd.address, "sender@host.test")
        self.assertEqual(cmd.parameters, {"body": "7BIT"})

    def test_missing_argument_raises(self):
        with self.assertRaises(EnvelopeParseError):
            parse_mail_from("MAIL FROM")

    def test_missing_brackets_raises(self):
        with self.assertRaises(EnvelopeParseError):
            parse_mail_from("MAIL FROM:sender@host.test")

    def test_unterminated_bracket_raises(self):
        with self.assertRaises(EnvelopeParseError):
            parse_mail_from("MAIL FROM:<sender@host.test")

    def test_invalid_parameter_raises(self):
        with self.assertRaises(EnvelopeParseError):
            parse_mail_from("MAIL FROM:<sender@host.test> BADPARAM")


class TestRcptTo(unittest.TestCase):
    def test_basic(self):
        cmd = parse_rcpt_to("RCPT TO:<user@domain.test>")
        self.assertEqual(cmd.address, "user@domain.test")

    def test_case_insensitive_verb(self):
        cmd = parse_rcpt_to("rcpt to:<user@domain.test>")
        self.assertEqual(cmd.address, "user@domain.test")

    def test_with_orcpt_parameter(self):
        cmd = parse_rcpt_to("RCPT TO:<user@domain.test> ORCPT=rfc822;user@domain.test")
        self.assertEqual(cmd.address, "user@domain.test")
        self.assertEqual(cmd.parameters, {"orcpt": "rfc822;user@domain.test"})


class TestSourceRoute(unittest.TestCase):
    def test_single_hop(self):
        cmd = parse_rcpt_to("RCPT TO:<@relay.test:user@domain.test>")
        self.assertEqual(cmd.address, "user@domain.test")
        self.assertEqual(cmd.source_route, ["relay.test"])

    def test_multiple_hops(self):
        cmd = parse_rcpt_to("RCPT TO:<@a.test,@b.test:user@domain.test>")
        self.assertEqual(cmd.address, "user@domain.test")
        self.assertEqual(cmd.source_route, ["a.test", "b.test"])

    def test_source_route_with_parameters(self):
        cmd = parse_mail_from("MAIL FROM:<@relay.test:sender@host.test> SIZE=50")
        self.assertEqual(cmd.address, "sender@host.test")
        self.assertEqual(cmd.source_route, ["relay.test"])
        self.assertEqual(cmd.parameters, {"size": "50"})

    def test_source_route_missing_colon_raises(self):
        with self.assertRaises(EnvelopeParseError):
            parse_rcpt_to("RCPT TO:<@relay.test>")

    def test_source_route_empty_host_raises(self):
        with self.assertRaises(EnvelopeParseError):
            parse_rcpt_to("RCPT TO:<@,user@domain.test>")

    def test_source_route_missing_at_raises(self):
        with self.assertRaises(EnvelopeParseError):
            parse_rcpt_to("RCPT TO:<relay.test:user@domain.test>")


if __name__ == "__main__":
    unittest.main()
