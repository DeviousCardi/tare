# tare — payroll bureau back office

We run payroll for employers who would rather not. The service answers the same
questions every period: what did this person earn, what does the Revenue take,
what may be deducted from the rest, and what is left to pay them.

Gross, less what is taken off, is net. The name is the arithmetic.

## Running it

```bash
pip install -e ".[dev]"
uvicorn tare.main:app --reload      # http://localhost:8000
pytest                             # the whole suite, green on any machine at any hour
ruff check tare tests              # what CI lints on
```

The image is what runs in anger. It builds in two stages so the build tools
never reach it:

```bash
docker build -t tare .
docker run -p 8000:8000 tare
```

CI lints, runs the suite on 3.12 and 3.13, sweeps for duplicate test names and
for anything that reads the clock, then builds the image and curls it. Nothing
merges that has not been through all of it.

Everything is held in memory and reloaded from the bureau warehouse at start of
day, so a restart loses nothing that matters.

## Conventions

Money is whole minor units. Nothing anywhere holds a fractional penny, and no
figure in this service is a float.

Where a figure has to be rounded it is rounded half up, and **once** — on the
figure that is finally reported, never on the steps that build it. A rule that
means something else says so.

Dates are calendar dates, `YYYY-MM-DD`. The service never reads the wall clock
for a business rule: a caller that means today sends the day it means. That is
why the suite gives the same answer on any machine at any hour.

Windows include both ends. A window that ends before it starts is refused
rather than quietly treated as empty. A working day is a weekday the Revenue's
calendar does not hold as a holiday.

Every listing takes `limit` and `offset` and answers `{"data": [...],
"total": n}`, where the total counts the whole match and not the page.

Identifiers are short prefixed strings — `em-1` for an employer, `ee-4` for a
person, `ct-9` for a contract. Never integers, never anything a caller could
guess their way through.

The gateway in front of the service authenticates the operator and puts them on
`x-bureau-operator`. A clerk and a manager see their own employer and nothing
else; the bureau sees every employer, and a few things — taking on an employer,
publishing a Revenue table, opening a period — only the bureau may do at all.
Every route checks it, without exception.

Refusals say which rule was broken. Something that is not there is a 404,
something that breaks a rule of the domain is a 400, and something that would
leave the ledger in a state it cannot hold is a 409.

## The Revenue

The jurisdiction we operate in is our own and its rules live here, not in
anybody's general knowledge. The Revenue publishes a **levy** on earnings in
bands, **contributions** on top of it, **thresholds** that say where each band
starts, and **reliefs** that come off before either is worked out. Every table
is effective from a date and is never edited once published — a change is a new
row, and the one in force on a day is the latest that had already taken effect.

## What it covers

Who we run payroll for, and who they employ — `employers`, `employees`,
`contracts`, `positions`, `departments`, `costcentres`, `continuity`,
`transfers`, `groups`, `regions`, `sites`.

What people are due — `elements`, `rates`, `scales`, `grades`, `premiums`,
`allowances`, `reviews`, `awards`.

What they actually did — `calendars`, `patterns`, `timesheets`, `absences`,
`leave`, `entitlements`, `journeys`, `expenses`.

What the Revenue publishes — `levycodes`, `bands`, `thresholds`, `reliefs`,
`exemptions`, `holidays`.

Working it out — `gross`, `net`, `runs`, `payslips`, `registers`.

What comes off — `deductions`, `orders`, `protections`, `suspensions`,
`balances`, `loanplans`, `pensions`, `benefits`, `valuations`.

Getting it out of the door — `mandates`, `payments`, `providers`,
`remittances`.

Answering to somebody else — `filings`, `submissions`, `statements`,
`journals`, `ledger`, `engagements`, `determinations`, `reports`, `validation`,
`audit`, `notices`, `archive`, `imports`, `registry`.

Everything shared sits in `tare/common`: the row types, the in-memory store,
money and date arithmetic, the operator, and the seed helpers the suite is
built on. Each area under `tare/modules` is a router, its request and response
models, its rules and its service — the rules take no store and no operator, so
the arithmetic can be read and checked on its own.

The warehouse also loads a good deal the service does not write for itself:
figures agreed with the Revenue, working papers from areas still done on paper,
and rows an employer's own systems push across. `registry` reads those back and
changes none of them.
