import socketserver
import threading
import unittest

from smtp_lab import SMTPError, send_plain_message


class FakeSMTP(socketserver.StreamRequestHandler):
    def handle(self):
        self.wfile.write(b"220 local test server\r\n")
        self.wfile.flush()
        commands = []
        message = []
        while True:
            line = self.rfile.readline()
            if not line:
                break
            line = line.rstrip(b"\r\n")
            commands.append(line)
            if line == b"EHLO localhost":
                self.wfile.write(b"250-localhost\r\n250 HELP\r\n")
            elif line.startswith(b"MAIL FROM:<"):
                self.wfile.write(b"250 sender accepted\r\n")
            elif line.startswith(b"RCPT TO:<"):
                if self.server.reject_recipient:
                    self.wfile.write(b"550 recipient rejected\r\n")
                    self.wfile.flush()
                    break
                self.wfile.write(b"250 recipient accepted\r\n")
            elif line == b"DATA":
                self.wfile.write(b"354 send data\r\n")
                self.wfile.flush()
                while True:
                    data = self.rfile.readline()
                    if data == b".\r\n":
                        break
                    message.append(data)
                self.wfile.write(b"250 queued locally\r\n")
            elif line == b"QUIT":
                self.wfile.write(b"221 goodbye\r\n")
                self.wfile.flush()
                break
            self.wfile.flush()
        self.server.received.append((commands, message))


class SMTPTests(unittest.TestCase):
    def setUp(self):
        self.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), FakeSMTP)
        self.server.daemon_threads = True
        self.server.received = []
        self.server.reject_recipient = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def send(self, **kwargs):
        return send_plain_message(
            "127.0.0.1",
            self.server.server_address[1],
            "alice@example.test",
            "bob@example.test",
            "Course lab",
            "first\n.dot-leading\nlast",
            **kwargs,
        )

    def test_complete_conversation_and_dot_stuffing(self):
        transcript = self.send()
        commands, message = self.server.received[0]
        self.assertEqual(commands[-1], b"QUIT")
        self.assertIn(b"..dot-leading\r\n", message)
        self.assertEqual(message[0], b"From: alice@example.test\r\n")
        self.assertTrue(transcript[-1].startswith("221"))
        self.assertEqual(len(transcript), 8)  # Includes two EHLO reply lines.

    def test_rejected_recipient_is_reported(self):
        self.server.reject_recipient = True
        with self.assertRaisesRegex(SMTPError, "550"):
            self.send()

    def test_header_injection_is_rejected_before_connect(self):
        with self.assertRaises(ValueError):
            send_plain_message("127.0.0.1", 1, "alice@example.test", "bob@example.test", "Hi\r\nBcc: x", "body")


if __name__ == "__main__":
    unittest.main()
