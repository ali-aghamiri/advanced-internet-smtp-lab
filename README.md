# Advanced Internet: SMTP Socket Lab

This is a **new reconstruction** of an unfinished SMTP exercise found in my Advanced Internet course folder. The archived `SMTP.py` was a blank teaching template, so this repository does not present that template as a completed submission.

The client demonstrates a raw TCP SMTP exchange: greeting, multiline `EHLO` reply, sender and recipient commands, `DATA`, dot-stuffing, and `QUIT`. It rejects header line breaks and surfaces SMTP error replies. The tests use a local fake server and send **no real email**.

```bash
python -m unittest -v
```

Requires Python 3.10 or newer; no third-party packages. The exercise handles plain ASCII messages only. It omits authentication, TLS, MIME, internationalized addresses, and production delivery safeguards. The course handout, teaching template, lecture recordings, and student submissions are excluded.
