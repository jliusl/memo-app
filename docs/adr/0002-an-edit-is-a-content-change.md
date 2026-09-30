# An edit is a content change

A Memo has one timestamp the list sorts by, `updated_at`, and the rule is that it records when the Memo was last **written**: when its title or its body changed. Nothing else moves it.

The tempting alternative is SQLAlchemy's `onupdate=utcnow`, which stamps the column on any UPDATE of the row and costs one line. It is rejected because it silently makes every action an edit. Pinning is the case that makes this visible: a pinned Memo leads the list whether or not its timestamp moved, so the difference only appears on the way back. Pin a Memo and unpin it, and under `onupdate` it reappears at the top of the list — it was not touched, nobody wrote a word, but it has jumped above Memos that were genuinely edited more recently. The user's account of what happened ("I pinned and unpinned it") and the list's account ("this was the last thing I wrote") disagree, and the list is wrong.

So pinning is treated as *organising* a Memo, not writing to it. A PATCH that changes neither the title nor the body is not an edit either, even when it arrives with both fields populated — the values are compared before assignment, so re-sending the same text does not reshuffle anything. `updated_at` therefore has no `onupdate`; the router sets it explicitly, and only when a comparison says the content really changed.

This is a contract, not an implementation detail: `updated_at` is returned by the API and is the ordering key for the whole unpinned list. Changing its meaning later would silently reorder every user's Memos, which is why it is written down rather than left as a property of one `mapped_column` call.

Considered and rejected: `onupdate=utcnow` (one line, but conflates organising with writing); a separate `edited_at` column alongside an `updated_at` that tracks any change (two timestamps with no reader for the second); and sorting the unpinned list by `created_at` instead (which discards the "what was I just working on" ordering that is the point of the list).
