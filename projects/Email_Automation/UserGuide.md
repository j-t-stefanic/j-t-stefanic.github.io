# Optimum Email Automation — User Guide

This guide describes `Optimum_Email_Automation.py` as supplied. The script connects to an Optimum mailbox over IMAP, scans one mailbox, chooses actions from a JSON rules file, and optionally moves messages. Start with `analyze` to inspect the proposed actions. `apply` makes mailbox changes.

## Before you start

- Python **3.10 or newer**. The script uses only Python's standard library; there is no `pip install` step.
- An Optimum email account with IMAP access and its valid sign-in credentials. The script defaults to `mail.optimum.net` on port `993` using SSL. If your account requires a special app password, use the credential your email provider supplies for IMAP.
- A copy of `Optimum_Email_Automation.py` in your working directory. The commands below assume that filename. Replace it if you renamed the script.
- A local place to store `email_rules.json` and the generated CSV. The CSV contains senders and subjects, so keep it private.

Use `python` on Windows or `python3` on macOS/Linux in the examples below. On some Windows installations, `py` may be the appropriate command.

Check that Python and the script run:

```shell
python --version
python Optimum_Email_Automation.py --help
```

## 1. Create your rules file

```shell
python Optimum_Email_Automation.py init-rules
```

This creates `email_rules.json` in the current directory. The sample contains illustrative addresses that you **must replace** with your own matching criteria. The command refuses to overwrite an existing rules file. It does not connect to the mailbox and does not need `--username`.

Edit the file in a text editor. Here is a small example:

```json
{
  "rules": [
    {
      "name": "Keep tax documents",
      "match": {"subject": {"contains": "tax document"}},
      "action": "keep"
    },
    {
      "name": "Move store receipts",
      "match": {"sender_email": {"equals": "receipts@example.com"}},
      "action": "move",
      "folder": "Receipts"
    },
    {
      "name": "Send daily newsletter to Trash",
      "match": {
        "sender_email": {"ends_with": "@newsletter.example"},
        "subject": {"contains": "daily update"}
      },
      "action": "delete"
    }
  ]
}
```

Rules are evaluated **from top to bottom**. The first matching rule wins. Place a specific `keep` rule above a broader `move` or `delete` rule when you need that exception. Every condition within one rule must match. The recognized fields are `sender` (the full displayed From header), `sender_email` (the parsed email address), and `subject`. Matching is case-insensitive.

| Operator | Example | Meaning |
| --- | --- | --- |
| `equals` | `{"sender_email": {"equals": "person@example.com"}}` | The entire field equals the value. |
| `contains` | `{"subject": {"contains": "receipt"}}` | The field contains the text. |
| `ends_with` | `{"sender_email": {"ends_with": "@example.com"}}` | The field ends with the text. |
| `regex` | `{"subject": {"regex": "invoice [0-9]+"}}` | A Python regular expression matches somewhere in the field. |

Each rule's `action` is `move`, `delete`, or `keep`. A `move` rule also needs a nonempty `folder`. `delete` moves a message to the configured Trash folder; it is **not** a permanent deletion in this script. `keep` leaves it in the selected mailbox. A message with no matching rule receives the action `none` and stays in place.

Avoid empty `match` objects: they do not match anything. Use valid JSON with double quotes and no trailing commas. A malformed rule may fail during analysis rather than at file load time, so inspect the preview carefully.

## 2. Provide your username and password

The simplest option is to pass the email address as a global option. The script prompts for a password without displaying what you type:

```shell
python Optimum_Email_Automation.py --username you@optimum.net analyze
```

Alternatively set `OPTIMUM_EMAIL` for the username. You may also set `OPTIMUM_EMAIL_PASSWORD` for the password, but a password environment variable can be exposed to other local processes or retained in shell history if entered directly. The interactive prompt is a sensible default. Do not put a password into the rules file or commit credentials to GitHub.

**PowerShell (current session):**

```powershell
$env:OPTIMUM_EMAIL = 'you@optimum.net'
python .\Optimum_Email_Automation.py analyze
```

**macOS/Linux (current shell):**

```shell
export OPTIMUM_EMAIL='you@optimum.net'
python3 Optimum_Email_Automation.py analyze
```

If necessary, `--host` and `--port` override `mail.optimum.net` and `993`; verify changes with your provider before using them. `--mailbox` defaults to `INBOX`. These global options go **before** the command name.

## 3. Analyze the mailbox without changing it

```shell
python Optimum_Email_Automation.py --username you@optimum.net analyze --rules email_rules.json --output preview.csv
```

The script opens the chosen mailbox read-only, searches all messages in it, fetches their From, Subject, and Date headers, chooses the first matching rule, and writes the proposed actions to `preview.csv`. It does not fetch message bodies or attachments. If `--output` is omitted, it creates a timestamped file such as `optimum_email_plan_20260924_143000.csv` in the current directory. An existing file at the chosen `--output` path is overwritten.

The CSV columns are `uid`, `date`, `sender`, `sender_email`, `subject`, `rule`, `action`, and `destination`. UIDs identify messages **within the selected mailbox**, not across folders. Check especially the `delete` and `move` rows, the destination names, unexpected matches, and the printed counts for `move`, `delete`, `keep`, and `none`. A `none` count simply means messages did not match any rule.

To scan a different mailbox:

```shell
python Optimum_Email_Automation.py --username you@optimum.net --mailbox Archive analyze --output archive_preview.csv
```

This command analyzes **one selected mailbox**. It does not recursively scan every folder.

## 4. Apply the rules only after reviewing the preview

Once the rules and preview look right, run:

```shell
python Optimum_Email_Automation.py --username you@optimum.net apply --rules email_rules.json
```

The script scans the mailbox **again and creates a fresh plan**. It displays planned counts, then requires you to type `APPLY` exactly. Any other answer makes no changes. It does **not** load or execute `preview.csv`; messages arriving or changing between `analyze` and `apply` may affect the fresh plan. Review the displayed counts before confirming.

For a `move` action, the script attempts to create the destination folder, copies the message there, marks the original for deletion, and expunges marked originals at the end. For a `delete` action, it uses the same process with `Trash` as the default destination. If your account uses a different Trash folder name, specify it:

```shell
python Optimum_Email_Automation.py --username you@optimum.net apply --trash Deleted
```

Check the **exact server folder name** in your email client; the script does not discover it automatically. Folder creation is attempted on each move, and a server response of `NO` is treated as though the folder may already exist. If a copy then fails, the script prints an error for that UID.

`--yes` skips the typed `APPLY` confirmation. Use it only in a controlled process after you understand the rules and potential mailbox changes:

```shell
python Optimum_Email_Automation.py --username you@optimum.net apply --yes
```

The completion counts show `move`, `delete`, `keep`, `none`, and `errors`. They count operations that returned successfully in the script. **The script does not verify the destination folder after each copy or check the server's expunge response**, so check the mailbox in your email client before treating those counts as a final audit. A failure after copying but before removing the original can leave a duplicate. The script continues past per-message errors and returns exit status `1` when such errors occur; it returns `0` when none were recorded.

## Command reference

```text
python Optimum_Email_Automation.py [global options] init-rules [--rules FILE]
python Optimum_Email_Automation.py [global options] analyze [--rules FILE] [--output CSV]
python Optimum_Email_Automation.py [global options] apply [--rules FILE] [--trash FOLDER] [--yes]
```

| Option | Default | Purpose |
| --- | --- | --- |
| `--username` | `OPTIMUM_EMAIL` environment variable | IMAP username; required for `analyze` and `apply`. |
| `--host` | `mail.optimum.net` | IMAP server. |
| `--port` | `993` | IMAP SSL port. |
| `--mailbox` | `INBOX` | One source mailbox to scan. |
| `--rules` | `email_rules.json` | Rule file to create or read, depending on command. |
| `--output` | Timestamped CSV | Output file for `analyze` only. |
| `--trash` | `Trash` | Destination for `delete` actions in `apply`. |
| `--yes` | Off | Skip the confirmation prompt in `apply`. |

Use `python Optimum_Email_Automation.py apply --help` (or another command name) for built-in command help.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `Provide --username or set OPTIMUM_EMAIL` | Add `--username` **before** `analyze` or `apply`, or set the environment variable. |
| Sign-in fails | Check the complete email address, password, IMAP access, and whether the account needs an app-specific credential. A successful connection requires access to the configured host and port. |
| `Refusing to overwrite existing file` | Edit the existing rules file or use `init-rules --rules another_name.json`. |
| JSON or rule error | Check JSON syntax, `"rules"` as an array, action spelling, move destination, field names, and operators. |
| Too many messages match | Narrow the condition; use `sender_email` for addresses, add a `subject` condition, and put specific exceptions first. Re-run `analyze`. |
| Move/delete errors or zero successful moves | Verify the destination/Trash folder names and IMAP folder permissions. Inspect each printed UID error and confirm actual mailbox state in your email client. Do not assume a `NO` response to folder creation means the folder exists. |
| Preview differs from apply | `apply` scans the mailbox anew. Re-run `analyze` immediately before applying and review the planned counts. |

## Practical limits

This script processes all messages in one selected mailbox on each run; it has no built-in date filter, incremental checkpoint, scheduler, undo command, or CSV import. The preview is a planning aid, not a locked transaction. Keep a backup of important mail, start with a narrow rule and a small mailbox if possible, and verify moves in the destination and Trash folders after an apply run.
