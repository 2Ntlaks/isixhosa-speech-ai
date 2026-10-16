# Problems

Every error, failure or surprise worth remembering: the raw material for the "what went wrong" part of the write-up.
Append-only. Keep the exact error text.

Format:

    ## P-0001 · YYYY-MM-DD · <short title>
    - Stage / run: <stage N, R-00xx>
    - Symptom: <what we saw; exact error message in a code block>
    - Cause: <why it happened, in plain language>
    - Fix: <what changed; commit or file>
    - Cost: <time lost, $ lost>
    - Lesson: <one sentence the founder could say in an interview>

## P-0001 · 2026-10-16 · Download job showed no progress for 15 minutes
- Stage / run: data download, job fetch-nchlt-1 (no run ID)
- Symptom: node.log stayed on `--- 16:37:55 nchlt.speech.corpus.xho.zip` with no percentage; founder asked "how far now?" and we could only guess.
- Cause: curl ran silent (`-sS`) and nothing else reported bytes received; we also cannot log in to the node (see P-0002).
- Fix: cloud/node/fetch_bootstrap.sh now logs the size downloaded so far every 60 s.
- Cost: none in $; some uncertainty.
- Lesson: any long cloud job must report its own progress, because you can't always look inside the machine.

## P-0002 · 2026-10-16 · SSM Session Manager cannot reach our nodes
- Stage / run: data download (both jobs)
- Symptom: console log on boot:
  ```
  SSM Agent unable to acquire credentials: ... AccessDeniedException: Systems Manager's instance management role is not configured for account: <acct>
  ```
- Cause: the node role (mgaguli-render-node) only allows S3 access to the bucket; the account has no SSM default host management role, and the role lacks AmazonSSMManagedInstanceCore.
- Fix: not yet. Harmless for downloads; needed before stage 2 so agents can look inside GPU nodes without opening SSH.
- Cost: none.
- Lesson: decide how you'll get inside a cloud machine before you need to.
