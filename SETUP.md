# Setup Guide

Follow these steps once before running the lab. Estimated time: **10–15 minutes**.

---

## 1. Install GitHub Copilot CLI

If you don't already have it:

1. Install the [GitHub Copilot extension for VS Code](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot)
2. Sign in with your GitHub account (must have a Copilot licence)
3. Open a terminal in VS Code — you should be able to run `gh copilot` or use the Copilot Chat panel

> The lab uses GitHub Copilot CLI (the terminal-based agentic mode), not just Copilot Chat. Make sure you can open a Copilot CLI session from the VS Code terminal.

---

## 2. Install the Databricks AI Dev Kit

The AI Dev Kit installs the Databricks MCP server and Copilot skill packs that give Copilot direct access to your workspace.

Open a **PowerShell** terminal and run:

```powershell
irm https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/install.ps1 | iex
```

This will:
- Clone the `databricks-solutions/ai-dev-kit` repo locally
- Create a Python virtual environment and install the Databricks SDK and MCP server
- Register the MCP server in VS Code's MCP configuration (`.vscode/mcp.json`)
- Install the skill packs needed for Databricks data engineering

> **Source:** [github.com/databricks-solutions/ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit)
> The installer always pulls the latest release.

---

## 3. Authenticate to your Databricks workspace

```powershell
databricks auth login --host https://<your-workspace-url>.azuredatabricks.net
```

This opens a browser tab for OAuth login. Complete the sign-in, then return to the terminal — you should see a success message.

Your credentials are saved to `~/.databrickscfg` under the `DEFAULT` profile. The MCP server picks these up automatically.

---

## 4. Restart VS Code

Close and reopen VS Code so the MCP server configuration takes effect.

---

## 5. Verify the MCP connection

In VS Code:

1. Open the Command Palette (`Ctrl+Shift+P`) → search for **"MCP: List Servers"**
2. You should see `databricks` listed with a **green** status indicator

If the server shows red or missing, check:
- `~/.databrickscfg` exists and has a `[DEFAULT]` section with your workspace URL and a valid token/OAuth credential
- The AI Dev Kit installed successfully (re-run the installer with `-Force` if unsure)
- VS Code was fully restarted after install

---

## 6. Verify the skill profile

Open a terminal in this repo's root folder and run:

```powershell
cat .ai-dev-kit\.skills-profile
```

You should see:
```
data-engineer
ai-ml-engineer
```

These profiles tell Copilot to load the Databricks data engineering and AI/ML skill packs automatically when you open this folder.

---

## Cost and cleanup

The lab uses:
- A **2X-Small SQL warehouse** with 15-minute auto-stop (very low cost)
- **Serverless Python compute** (billed per second, on-demand)

Both are provisioned by Copilot during the lab. The lab ends with a **teardown prompt** that drops the catalog and stops the warehouse. Make sure to run it.

Rough estimate: a full run of the lab (including teardown) costs well under $5 in DBUs on a standard Azure Databricks workspace.

---

## Troubleshooting

**Catalog creation fails**
The agent will try to create the `formula1` catalog via the Databricks SDK. On workspaces that use Default Storage (no external metastore), this call fails. The agent will automatically pivot to creating the catalog via SQL DDL instead. This is expected — let it continue.

**Re-running the lab after a previous run**
The `formula1` catalog will already exist. Either:
- Run the teardown prompt from your previous session first, or
- Tell Copilot: *"Drop and recreate the formula1 catalog before starting."*

**MCP server not green after restart**
- Confirm `databricks auth login` completed successfully
- Try re-running the AI Dev Kit installer: `.\install.ps1 -Force`
- Check that `.vscode/mcp.json` was created in the repo root by the installer

**"formula1-datasets folder not found" error**
Make sure you cloned this repo (including the `formula1-datasets/` subdirectory) and opened the repo root as your VS Code workspace folder.
