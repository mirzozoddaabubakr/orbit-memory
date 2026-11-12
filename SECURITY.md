# Security

Report suspected exposure privately to the maintainer using GitHub private vulnerability reporting when available. Include the commit, file, line and credential type. Omit the credential value.

## Public repository audit, 12 November 2026

A Gitleaks scan of all locally available refs and reflogs (two commits) found zero credential alerts. A directory scan including archives reported eight candidates: the ignored publishable key in orbit-auth.json and seven matches in the Python environment's cryptography, PyJWT and win32 dependencies. An additional byte scan looked for email addresses, home paths, Supabase key prefixes and SQLite headers in working files, bundled zip contents and each historical tree. Generated plugin configurations, compiled Python and dependency bundles contain local paths or upstream contact information. These files are ignored.

Personal email is present in both author and committer fields of bea872e and 5b01ca7. Inspect locally with git show --no-patch --format=fuller COMMIT. No historical database or pairing-key file was identified. Known-pattern scanning cannot prove every arbitrary string is harmless.

## If a credential reaches GitHub

Revoke the exposed credential with its provider, issue a replacement, update the local configuration and review usage logs. For a leaked Orbit pairing key, revoke the affected credential in the local account store and pair the client again. A Supabase publishable key is intended for clients; a secret or service-role key requires immediate rotation.

History cleanup is a separate action. Make a backup, coordinate with collaborators and use git-filter-repo in a fresh mirror. Use --mailmap to replace both author and committer email, --invert-paths --path FILE for an accidentally committed file, or --replace-text for embedded values. Inspect all rewritten branches and tags before force-pushing. Have collaborators re-clone and contact GitHub Support about cached sensitive content. Existing clones may retain earlier commits. No rewrite was performed during this audit.

## Local data

Keep account configuration, databases and their SQLite sidecars, pairing credentials, generated integrations and Python environments out of version control. Backups and exports need the same care as the original conversations.
