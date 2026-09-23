---
layout: default
title: Optimum Email Organizer | John Stefanic
---

[← Back to Portfolio](../)

# 📧 Optimum Email Organizer

**Python · IMAP · Automation · JSON · CSV · Email Processing**

## Project Overview

The Optimum Email Organizer is a Python command-line workflow for analyzing and organizing an Optimum mailbox through secure IMAP. It separates analysis from mailbox changes so a user can review a proposed action plan before anything is moved or deleted.

## The Problem

Large mailboxes can become difficult to organize manually. A useful automation needs flexible matching rules, repeatable actions, useful audit output, and safeguards that reduce the chance of unintended mailbox changes.

## Solution Workflow

Optimum Mailbox → Read Message Headers → Apply Configurable Rules → Generate CSV Preview → User Confirmation → Move / Delete / Keep

## Safety-First Design

The program is read-only by default. Mailbox changes require the apply command and explicit confirmation. Passwords are obtained from an environment variable or secure prompt rather than stored by the program.

## Rule Engine

Rules are loaded from JSON and can match message sender, sender email address, or subject. Matching supports:

- Exact values
- Contains
- Ends with
- Regular expressions

Rules can assign one of three actions: **move**, **delete**, or **keep**. Move rules require a destination folder.

## Analysis & Reporting

The analyzer reads message headers using IMAP UIDs and builds an action plan containing:

- UID
- Date
- Sender
- Sender email
- Subject
- Matching rule
- Planned action
- Destination folder

The plan can be written to CSV before any mailbox changes occur, creating a reviewable audit trail.

## Applying Changes

After confirmation, the workflow can create destination folders, copy matching messages, mark originals for deletion, route delete actions to Trash, expunge completed changes, and report counts for move, delete, keep, unmatched messages, and errors.

Individual message failures are captured so one malformed or problematic message does not stop the entire run.

## Skills Demonstrated

Python · IMAP · Email Processing · JSON Configuration · CSV Reporting · Regular Expressions · Error Handling · Command-Line Interfaces · Workflow Automation · Credential Safety

## Why This Project Matters

This project demonstrates practical automation against a real external service while emphasizing controlled changes, configurable business rules, error handling, and reviewable output. It shows how Python can automate a repetitive operational task without making mailbox modifications silently.

[← Back to Portfolio](../)
