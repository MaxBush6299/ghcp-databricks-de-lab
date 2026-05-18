# GitHub Copilot + Databricks: Automated Data Engineering — Lab

> This is the **hands-on lab branch**. You'll build a production-ready Formula 1 medallion lakehouse from scratch by prompting GitHub Copilot CLI — discovering real data quality issues along the way and crafting the prompts to fix them.

---

## What you'll build

Starting from **60 raw CSV files** spanning 14 seasons of Formula 1 data, you'll use GitHub Copilot CLI to:

- Create a Unity Catalog medallion architecture (Bronze → Silver → Gold) in Databricks
- Clean and normalise messy team names — catching at least one data anomaly yourself
- Build a full snowflake dimensional model
- Fill in historical data gaps using a public API — but only after you spot the problem
- Publish a live AI/BI dashboard in the Databricks workspace

**The generated notebooks are not included here.** Copilot writes them during the lab. If you want to see the reference output, check the [`main` branch](../../tree/main).

---

## Branches

| Branch | What it contains |
|---|---|
| **`lab`** (you are here) | Starter — follow `LAB.md` to run the exercise |
| **[`main`](../../tree/main)** | Completed reference — `SOLUTION.md` + generated notebooks |

---

## Prerequisites

- Windows 10/11
- GitHub Copilot CLI installed and authenticated
- Visual Studio Code with the GitHub Copilot extension
- An Azure Databricks workspace with Unity Catalog enabled and permission to create catalogs/warehouses

See [`SETUP.md`](./SETUP.md) for the full setup walkthrough.

---

## Start here → [`LAB.md`](./LAB.md)

> Build a production-ready Formula 1 medallion lakehouse — **Bronze → Silver → Gold** with a full snowflake dimensional model and an AI/BI dashboard — entirely through natural-language conversation with GitHub Copilot CLI.

---

## What is this?

This repo demonstrates how far data engineering can be automated when an AI agent (GitHub Copilot CLI) has direct, governed access to a Databricks workspace via the Databricks MCP server.

Starting from **60 raw CSV files** spanning 14 seasons of Formula 1 data, Copilot:

- Profiles and plans the migration end-to-end
- Creates the Unity Catalog infrastructure (catalog, schemas, volumes, warehouse)
- Ingests all CSVs into Bronze Delta tables with schema merging and metadata columns
- Normalises 70+ messy team-name variants down to 18 canonical teams — catching data anomalies using live web research
- Transforms Bronze → Silver → Gold with full type casting, deduplication, and a snowflake dimensional model
- Enriches missing calendar data by fetching a public API
- Publishes a live AI/BI dashboard — all without a single click in the Databricks UI

Every action was performed by Copilot via tool calls in the terminal. No copy-paste, no SQL editor clicks, no manual notebook edits.

---

## Branches

| Branch | What it contains | Who it's for |
|---|---|---|
| **`main`** (you are here) | Completed reference — `SOLUTION.md`, generated notebooks, full scaffolding | Reviewing what the agent produced |
| **[`lab`](../../tree/lab)** | Starter — `LAB.md` guided walkthrough, no pre-generated notebooks | Running the exercise yourself |

If you want to **do** the lab, switch to the `lab` branch and follow `LAB.md`. Use `git diff main lab` at any point to see exactly what the agent produced.

---

## Prerequisites

- Windows 10/11
- [GitHub Copilot CLI](https://docs.github.com/en/copilot/using-github-copilot/using-copilot-coding-agent-to-work-on-tasks) installed and authenticated
- [Visual Studio Code](https://code.visualstudio.com/) with the GitHub Copilot extension
- An Azure Databricks workspace with:
  - Unity Catalog enabled
  - Permission to create catalogs, schemas, SQL warehouses, and volumes
  - Your workspace URL (e.g. `https://adb-XXXXXXX.azuredatabricks.net`)

See [`SETUP.md`](./SETUP.md) for the full setup walkthrough.

---

## Source data

Raw CSV files are from the open-source Formula 1 dataset maintained by **[@toUpperCase78](https://github.com/toUpperCase78/formula1-datasets/tree/master)**. See [`formula1-datasets/README.md`](./formula1-datasets/README.md) for details and license.

---

## Tooling

This repo uses the **[Databricks AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit)** — a collection of Databricks-specific skills and an MCP server that give Copilot CLI direct, governed access to your workspace.

Install it with a single command (see [`SETUP.md`](./SETUP.md)).

---

## Solution walkthrough

See [`SOLUTION.md`](./SOLUTION.md) for the full narrative of what happened during the demo session — phase by phase, with Copilot callouts and the prompts used at each stage.
