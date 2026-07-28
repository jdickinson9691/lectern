# Lectern Contracts

This directory contains two kinds of contract:

1. Machine-readable integration contracts, such as the Fantasy Grounds snapshot
   schema and sanitized example at this directory's root.
2. Human-readable agent work contracts organized by lifecycle.

## Agent contract lifecycle

- [`templates/`](templates/) contains the required reusable template.
- [`active/`](active/) contains authorized work that is not yet accepted.
- [`completed/`](completed/) contains closed contracts with verification results.

An active contract grants only the authority written inside it. Assignment does
not automatically authorize live testing, external writes, installed-extension
changes, building, committing, merging, pushing, or releasing.

The durable domain definitions are in [`../agents/`](../agents/).
