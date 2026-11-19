# Security policy

Report vulnerabilities privately with GitHub private vulnerability reporting: open the
Security tab of this repository and choose "Report a vulnerability". Do not open a public
issue or pull request for a vulnerability.

Only the latest commit on `main` receives fixes; nothing here is released yet.

## If something goes wrong
The owner, andrey1souza, acts. The project has no releases yet. Report as shown above.
Within one hour:
- Leaked secret: revoke it, then rotate it. Remove it from history only after you revoke it. Check the gitleaks and secret scanning alerts.
- Bad dependency or Dependabot alert: pin or update the package. Run `make check`.
- Compromised workflow or action: disable Actions. Pin the previous commit SHA.
- Wrong result on the site: correct the fixtures or results. Rebuild the site. The site never claims more than the data file allows.
