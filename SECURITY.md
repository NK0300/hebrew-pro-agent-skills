# Security

<div dir="rtl" lang="he">

אין כאן שירות רץ ואין סודות. אם מצאתם מפתח, סיסמה, או הוראה שגורמת לסוכן לטפל בסודות ברשלנות, פתחו דיווח פרטי ב-GitHub Security Advisories של המאגר. אל תפתחו issue ציבורי עם הסוד עצמו.

</div>

This repository publishes instructions and installer scripts. It does not run a service and it does not ship credentials.

## Reporting

Use [GitHub Security Advisories](https://github.com/NK0300/hebrew-pro-agent-skills/security/advisories/new) for this repository. Include the file, the version (`1.0.0` or a commit), and what an agent following the text would do. Do not paste live secrets into a public issue.

## What "secret" means here

Placeholders such as `postgres://app:password@localhost:5432/app` in examples are fake. A real token, private key, or production URL does not belong in a skill, a test, or a commit.

## Installer

`install.sh` writes a timestamped backup before it replaces a file. Backups live under `.hebrew-skills/backups/` (project) or `~/.hebrew-pro-agent-skills/backups/` (global). Those directories can contain the previous contents of your `CLAUDE.md`. The installer drops a `.gitignore` of `*` into the project state directory so a backup is not committed by accident. Treat the backup folder as private and delete it when you no longer need the restore point.

The installer merges a marked block into instruction files. It does not delete the rest of the file. Review the script before piping it from the network. Cloning the repository and running `./install.sh` is the safer path.

## Scope

The skills tell an agent how to build Hebrew products with ordinary application security (authorization, parameterized queries, CSP, no secrets in logs). They are not a penetration-testing guide.
