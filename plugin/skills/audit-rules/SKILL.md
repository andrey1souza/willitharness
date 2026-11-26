---
name: audit-rules
description: Scan a repository for the rules an agent loads and report which a behaviour test could measure. Use when the user asks to audit, scan or test the rules of a repository.
---
Run `willitharness audit DIR` on the repository of the user.
DIR is the repository folder. Use `.` for the current folder.
If the command is not found, stop and tell the user that willitharness is not installed.
Show the whole report to the user.
Never edit the repository of the user. The report proposes changes. It applies none.
Apply a proposed change only when the user asks for that change.
Paid tests are a separate step. They are not built yet.
Say that the scan predicts and does not measure.
