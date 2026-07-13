# v0.1.103.10.88 — execute and prove the effective 10.75 remove-then-upload transaction

This is a diagnostic-only candidate.

The legacy arm now:

1. uploads a unique disposable file;
2. requires two stable listings with exactly one canonical source;
3. captures the exact source title and identity;
4. invokes the same exact remove operation used by 10.75;
5. requires two stable listings proving the source family is absent;
6. reuploads changed bytes through the unchanged 10.75 fresh-upload implementation;
7. requires a committed upload with new `file_...` and `libfile_...` identities; and
8. classifies the backend-assigned filename.

A pre-existing visible card is never accepted as second-upload success.
