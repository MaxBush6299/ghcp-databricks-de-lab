# GitHub Copilot + Databricks: Automated Data Engineering — Lab

> This is the **hands-on lab branch**. You'll build a production-ready Formula 1 medallion lakehouse from scratch by prompting GitHub Copilot — discovering real data quality issues along the way and crafting the prompts to fix them.

---

## What you'll build

Starting from the latest **Formula 1 CSV dataset** (50+ files spanning 14+ seasons — it grows as new races are run), you'll use GitHub Copilot to:

- Create a Unity Catalog medallion architecture (Bronze → Silver → Gold) in Databricks
- Clean and normalise messy team names — catching at least one data anomaly yourself
- Build a full snowflake dimensional model
- Fill in historical data gaps using a public API — but only after you spot the problem
- Publish a live AI/BI dashboard in the Databricks workspace

**The generated notebooks are not included here.** Copilot writes them during the lab. To see the reference output, check the [`main` branch](https://github.com/MaxBush6299/ghcp-databricks-de-lab/tree/main).

---

## Branches

| Branch | What it contains |
|---|---|
| **`lab`** (you are here) | Starter — follow `LAB.md` to run the exercise |
| **[`main`](https://github.com/MaxBush6299/ghcp-databricks-de-lab/tree/main)** | Completed reference — `SOLUTION.md` + generated notebooks |

---

## Prerequisites

- Windows 10/11
- **GitHub Copilot** subscription (Individual, Business, or Enterprise) with VS Code agent mode
- Visual Studio Code with the GitHub Copilot and GitHub Copilot Chat extensions
- Git installed (for cloning the dataset)
- An Azure Databricks workspace with Unity Catalog enabled and permission to create catalogs/warehouses

See [`SETUP.md`](./SETUP.md) for the full setup walkthrough.

---

## Source data

The Formula 1 CSVs come from the open-source dataset maintained by **[@toUpperCase78](https://github.com/toUpperCase78/formula1-datasets/tree/master)**, which is updated frequently with new race results. You'll **clone the latest copy yourself** during the lab rather than using a bundled snapshot — see [`SETUP.md`](./SETUP.md) and [`LAB.md`](./LAB.md). Please credit the original author if you reuse the data.

---

## Tooling

This lab uses the **[Databricks AI Dev Kit](https://github.com/databricks-solutions/ai-dev-kit)** — a collection of Databricks-specific skills and an MCP server that give GitHub Copilot direct, governed access to your workspace. Install it with a single command (see [`SETUP.md`](./SETUP.md)).

---

## Start here → [`LAB.md`](./LAB.md)
