"""Placeholder boundary for a future reviewed TikTok publishing workflow."""


def upload_video(*_: object, **__: object) -> None:
    """Reject upload attempts because publishing is outside the MVP scope."""
    raise NotImplementedError(
        "TikTok upload is intentionally not implemented. "
        "A future version must add explicit authentication, review, and consent."
    )

