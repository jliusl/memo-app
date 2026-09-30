# Memo App

The web memo application built under `src/`, and the System Under Test for this repository's Playwright harness.

## Language

**Memo**:
A single note owned by exactly one User, made of an optional title and a Markdown body.
_Avoid_: Note, card, todo, item

**User**:
An account that signs in with an email and a password, and owns Memos.
_Avoid_: Account, member, author, profile

**Owner**:
The single User a Memo belongs to. Ownership never transfers, and a Memo never has more than one owner.
_Avoid_: Author, creator, parent

**Pin** (置顶):
A marker on a Memo that raises it above every unpinned Memo in a listing. Only the owner can pin or unpin a Memo, and any number of a User's Memos can be pinned at once.
_Avoid_: Favorite, star, bookmark, flag, sticky

**Delete**:
Permanent removal of a Memo by its owner. A deleted Memo is gone and cannot be recovered from within the application.
_Avoid_: Remove, drop, destroy

**System Under Test** (SUT):
The Memo App itself, as opposed to the test harness that drives it. This repository exists to test the SUT.
_Avoid_: App, application, product, target, subject

## Explicitly not concepts in this context

- **Archive (归档)** and **Trash (回收站)**: deletion is permanent, so no intermediate state exists.
- **Tag (标签)**: Memos are not categorised.
- **Draft (草稿)**: a Memo is never partial or unsaved; it exists only once saved.
