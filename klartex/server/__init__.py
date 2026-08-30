"""HTTP compile surface — a stateless wrapper around `klartex.render()`.

Importing this package requires the `serve` extra
(`pip install 'klartex[serve]'`). The CLI's `klartex serve` command is the
only thing in klartex that imports it, and it does so lazily; the app
itself lives in `klartex.server.app`.

This is an internal compile layer: the routes carry no prefix, no schema is
published, and it expects a caller in front of it that owns authentication,
rate limiting and policy. The default bind address is therefore 127.0.0.1 —
the container image is what opens it to 0.0.0.0 on its own network.
"""
