# Lab Part 2: From Medallion to Product — Ship an Azure Static Web App with GitHub Copilot + Databricks

> **Part 2 of 2.** Part 1 ([`LAB.md`](./LAB.md)) built the `formula1.{bronze,silver,gold}` medallion and a single AI/BI dashboard. Part 2 turns that warehouse into a *product* — a branded Azure Static Web App that embeds four AI/BI dashboards and a Genie chat panel, deployed with `azd` and CI/CD.
>
> **You are on the `lab` branch.** The completed reference (full narrative + every Copilot Callout) lives in [`DEMO_SWA_TELEMETRY.md`](https://github.com/MaxBush6299/dbx-swa/blob/main/DEMO_SWA_TELEMETRY.md) on the `main` branch of the companion repo.

---

## What you'll build

A live **F1 Race Telemetry Command Center** — a branded, F1-themed React + TypeScript Static Web App, sitting on top of the `formula1.gold.*` warehouse you built in Part 1.

By the end of this lab you'll have:

- **Four published Databricks AI/BI dashboards** (Overview, Race Pace, Constructors, Drivers), each authored, validated, and screenshot-verified by Copilot.
- A **Vite + React 18 + TypeScript** front end with Tailwind CSS in the F1 palette (`#E10600` paddock red, chequer white, carbon black).
- **F1-themed components**: `PitWall.tsx` (top nav), `RaceControl.tsx` (left rail), `Telemetry.tsx` (iframe wrapper), `AskGenie.tsx` (chat panel).
- A **SWA Managed Function** (`POST /api/genie-chat`) that proxies questions to your Part 1 Genie space — keeping the Databricks PAT entirely server-side.
- **Infra-as-code** in Bicep, deployable with one `azd up`.
- A **GitHub Actions** workflow that builds and deploys on every push, with PR preview environments.

Two real gotchas surface during the lab — a silent "No data" dashboard publish, and an iframe that 403s for anonymous visitors. You'll write the prompts to fix them yourself. That's the point.

**Estimated effort:** most of the lab is watching Copilot work and clicking through Catalog Explorer / browser screenshots. If you customize the layout, add more dashboards, or wire in Entra ID auth, expect a longer session.

---

## Prerequisites checklist

Before you start, confirm:

- [ ] **Part 1 complete.** `formula1.gold.*` exists, the Genie space ("Formula 1 Championship Explorer" or similar) is published, and your SQL warehouse is running. If you tore it all down at the end of Part 1, run Part 1 again first.
- [ ] **GitHub Copilot CLI** installed and authenticated. Agent mode + plan mode available.
- [ ] **Visual Studio Code** open in an **empty repo folder** for this lab (Part 2 scaffolds a fresh project — do *not* run it inside your Part 1 working tree).
- [ ] **AI Dev Kit installed** with the **Databricks MCP** server showing green — see Part 1's `SETUP.md`.
- [ ] **Microsoft Playwright MCP (Edge)** installed and green. Copilot will use it to verify dashboards and the live SWA visually.
- [ ] **Node.js 20** on your PATH (`node --version` → `v20.x`).
- [ ] **Azure Developer CLI (`azd`)** installed (`azd version`).
- [ ] **Azure subscription** with permission to create a Resource Group and an Azure Static Web App (Standard SKU).
- [ ] **GitHub account** that can create a new public or private repository (the SWA workflow needs a GitHub repo to deploy from).
- [ ] **Databricks PAT** (or Service Principal token) for your Part 1 workspace, with permission to call the Genie Conversation API.
- [ ] **`databricks auth login`** still active from Part 1.

---

## Verify your MCP connections

Before running any prompts, confirm both MCP servers are connected:

1. Open the Command Palette in VS Code: `Ctrl+Shift+P`
2. Search **"MCP: List Servers"**
3. Confirm **both** `databricks` and `microsoft-playwright` (Edge) show **green**.

If either is red, fix it before continuing — Copilot needs the Databricks MCP to author dashboards and Playwright to screenshot them.

---

## Capture your Part 1 outputs

Prompt 1 needs three values from Part 1. Grab them now and paste them into a scratch note — you'll inline them into the prompt below.

| Value | Where to find it |
|---|---|
| `WORKSPACE_URL` | Your Databricks workspace base URL, e.g. `https://adb-XXXXXXX.azuredatabricks.net` |
| `SQL_WAREHOUSE_ID` | **Databricks → SQL Warehouses** → click `formula1-warehouse` → copy the ID from the URL or the connection details panel |
| `GENIE_SPACE_ID` | **Databricks → Genie** → open the space you published in Part 1 → copy the ID from the URL (`/genie/rooms/{id}`) |

> **Tip:** Generate a fresh Databricks PAT now too (**User Settings → Developer → Access tokens**). You'll paste it into `azd` later as `DBX_SERVICE_PRINCIPAL_TOKEN`. Give it 90 days for the lab and rotate or revoke it when you're done.

---

## Prompt 1 — Plan and build the app

Open **Copilot CLI** in your empty repo folder. Switch to **agent mode**. Paste the prompt below, **replacing the four `<...>` placeholders** with the values you captured above.

The prompt is intentionally long. It's the same `[[PLAN]]` block from the companion `DEMO_SWA_TELEMETRY.md` (rewritten to start with `/plan` so you can paste it straight into Copilot Chat in agent mode), plus four **engineering ground rules** at the top — general rules that catch common silent failure modes when authoring AI/BI dashboards and shipping a SWA.

```
/plan build an Azure Static Web App that serves as a branded "F1 Race Telemetry
Command Center" shell embedding Databricks AI/BI dashboards and a Genie
conversational panel over the formula1.gold.* medallion warehouse from Part 1.

A few engineering ground rules for whatever you build:

1. Databricks AI/BI dashboard JSON uses `queryLines: []` (one SQL fragment per array
   element), not a `query: string` property. Collapsing SQL into a single string produces
   silent parse errors at render time. Use queryLines everywhere.

2. Prefer bar + text widgets. Counter widgets in lvdash.json need an extra `fields[]`
   mapping that is easy to get wrong — pick one validated shape and reuse it across all
   four dashboards.

3. Always run `get_table_stats_and_schema` before authoring a dashboard on an unfamiliar
   schema. Don't assume column names — for example, the constructors table on this
   warehouse is `formula1.gold.dim_teams` (column `team_short_name`), not `dim_constructors`.

4. `VITE_*` env vars are inlined into the JS bundle and are visible to every visitor.
   Treat them as public. Dashboard embed URLs (which contain IDs, not data) belong here.
   PATs, client secrets, and anything else that grants Databricks access must live in
   SWA app settings only — never `VITE_*`.

STACK
- React 18 + TypeScript + Vite
- Azure Static Web Apps (SWA) with a SWA Managed Function (Node 20)
- GitHub Actions CI/CD (azure/static-web-apps-deploy@v1)
- Tailwind CSS — F1-styled dark theme (red #E10600 / paddock black / chequer white)

LAYOUT
- Top nav (PitWall): app title
- Left rail (RaceControl): routes for Overview, Race Pace, Constructors,
  Drivers, "Ask Genie"
- Main area: route-driven content
- Each analytical route embeds a Databricks AI/BI dashboard via iframe
  using a published embed URL read from a VITE_* env var

DASHBOARDS
Using the Databricks MCP, author 4 published AI/BI dashboards against the
formula1.gold.* star schema (dim_teams, dim_drivers, dim_race_rounds,
fact_race_results, vw_constructor_wins, vw_driver_wins, vw_alltime_driver_wins):
  - F1 TCC – Overview    (constructor wins by season + driver wins by season +
                          all-time driver wins bar charts)
  - F1 TCC – Race Pace   (avg fastest lap seconds by season)
  - F1 TCC – Constructors (all-time wins by team via dim_teams join)
  - F1 TCC – Drivers     (all-time driver wins + driver-of-the-day wins)
Validate every query with execute_sql before authoring. After publishing each
dashboard with embed_credentials=true, record the embed URLs.

GENIE INTEGRATION
Build a custom in-app F1-themed chat panel (AskGenie.tsx) with starter-question
chips, user/Genie message bubbles, conversation continuity, and a "New" button.
Back it with a SWA Managed Function POST /api/genie-chat that:
  1. Receives { question, conversationId? } from the browser
  2. Calls the Databricks Genie Conversation API server-side using
     DBX_SERVICE_PRINCIPAL_TOKEN (start-conversation or continue)
  3. Polls until status === "COMPLETED"
  4. Returns { answer, conversationId, messageId }
The token MUST NEVER reach the browser.

ENVIRONMENT VARIABLES
Build-time (VITE_* — inlined into bundle, non-secret):
  VITE_DBX_WORKSPACE_URL              — workspace base URL
  VITE_DBX_GENIE_SPACE_ID             — Genie space ID
  VITE_DBX_DASHBOARD_OVERVIEW_URL     — published embed URL
  VITE_DBX_DASHBOARD_RACEPACE_URL     — published embed URL
  VITE_DBX_DASHBOARD_CONSTRUCTORS_URL — published embed URL
  VITE_DBX_DASHBOARD_DRIVERS_URL      — published embed URL

Runtime secrets (SWA app settings — never reach browser):
  DBX_WORKSPACE_URL              — workspace URL for server-side calls
  DBX_SERVICE_PRINCIPAL_TOKEN    — Databricks PAT
  DBX_GENIE_SPACE_ID             — Genie space ID for server-side calls

CSP: add frame-src *.azuredatabricks.net *.cloud.databricks.com in
staticwebapp.config.json. All routes open (allowedRoles: anonymous) for demo.

DEVELOPER EXPERIENCE
- azd-compatible infra/ folder (Bicep) provisioning the SWA + app settings
- README: prerequisites, env vars, local dev (swa start), deployment,
  how to swap dashboard/Genie IDs
- .env.example with all placeholder vars
- One Vitest test for the genie-chat function

COMPONENTS (name after F1 concepts)
  PitWall.tsx     — top nav bar
  RaceControl.tsx — left-rail route links
  Telemetry.tsx   — iframe wrapper (accepts any dashboard embed URL)
  AskGenie.tsx    — in-app Genie chat panel

CONTEXT (from Part 1)
  Workspace URL:    <PASTE WORKSPACE_URL HERE>
  SQL warehouse ID: <PASTE SQL_WAREHOUSE_ID HERE>
  Genie space ID:   <PASTE GENIE_SPACE_ID HERE>
  Catalog/schema:   formula1.gold
```

> **Why the ground rules?** They're general front-end + AI/BI authoring rules that prevent the most common silent failures (wrong JSON shape, wrong column name, leaked secret). None of them give away the two teaching moments — those still require you to look at the output and push back.

### What to do when the plan appears

Copilot will return a phased plan covering dashboards, scaffold, components, Genie panel, SWA API, CSP, Bicep, and CI/CD. **Review it, then approve it as written.** Reply:

```
proceed!
```

> ⚠️ **Don't** ask Copilot to "test the Genie embed first" or "add a screenshot step to dashboard publishing" yet. Those interventions are exactly the two teaching moments — let them surface naturally.

### What Copilot will do

| Phase | What happens |
|---|---|
| 1. Author 4 dashboards | Inspects gold schema, validates SQL via `execute_sql`, publishes 4 lvdash dashboards with `embed_credentials=true`, records URLs |
| 2. Scaffold the SWA | Vite + React + TypeScript + Tailwind config emitted in a parallel batch, `npm install`, `npm run build` |
| 3. UI components | `PitWall.tsx`, `RaceControl.tsx`, `Telemetry.tsx` + `lib/databricks.ts` env registry |
| 4. Genie chat panel | `AskGenie.tsx` — F1-themed thread, starter chips, conversation state |
| 5. SWA Managed API | `/api/genie-chat` Azure Functions v3 trigger, start/continue + polling |

This is a good time to open **Databricks → Dashboards** in your browser and watch the four "F1 TCC – …" dashboards appear as Copilot publishes them.

### 🔍 UI Checkpoint — After Phase 1 (Dashboards published)

Open **Databricks → Dashboards** in the left nav. You should see all four:

- **F1 TCC – Overview**
- **F1 TCC – Race Pace**
- **F1 TCC – Constructors**
- **F1 TCC – Drivers**

Open **F1 TCC – Overview**. The page renders, the chart frames are drawn — but look closely at the widget contents.

---

## 🔎 Teaching Moment 1 — The "No data" dashboards

Copilot's terminal output for Phase 1 will read something like:

> *"Published 4 dashboards: F1 TCC – Overview ✅, F1 TCC – Race Pace ✅, F1 TCC – Constructors ✅, F1 TCC – Drivers ✅."*

All four `manage_dashboard` calls returned `success: true`. But click into **F1 TCC – Overview** in the Databricks UI. What do the chart widgets actually say?

**Look at the rendered chart bodies, not just the dashboard frame.**

<details>
<summary>💡 Hint (click to reveal)</summary>

Several widgets — especially the counters — show **"No data"** or render blank. The API call succeeded, but the dashboard is empty. A successful publish is not the same as a working dashboard.

</details>

### Your turn: craft the prompt

The agent thinks it's done. What would you ask Copilot to do?

A good prompt should:
- **(a)** Tell Copilot to **see** the dashboards, not just publish them — i.e., use Playwright to navigate to each published URL and take a screenshot
- **(b)** Diff what's on screen against expectation ("counters showing 'No data'")
- **(c)** Rebuild the broken widgets — and consider swapping fragile counter widgets for the proven bar + text pattern, in parallel across all four dashboards

Try writing your own prompt before looking at the reference.

<details>
<summary>📋 Reference prompt (click to reveal)</summary>

```
Several widgets across the four published dashboards render as "No data" even though
the manage_dashboard calls all succeeded. Please:

1. Use Playwright (Edge) to navigate to each of the four published dashboard URLs and
   take a full-page screenshot.
2. Diff the screenshots against expectation — list every widget that shows "No data",
   an error, or a blank chart.
3. Inspect the lvdash.json for each broken widget. If counter widgets are the culprit,
   replace them with the bar/text widget pattern that the other working widgets use.
4. Re-run execute_sql against every dashboard query to confirm the SQL itself returns
   rows — if a query returns 0 rows, fix the column references (remember dim_teams,
   not dim_constructors).
5. Re-publish all four dashboards in parallel using manage_dashboard.
6. Re-screenshot with Playwright to confirm every widget now renders data.
```

</details>

### What Copilot will do

Copilot will drive Playwright over each dashboard, identify the broken widgets, rebuild them using the bar + text pattern (avoiding the fragile counter shape), and re-publish all four in parallel. The second round of screenshots should show every widget populated with data.

### 🔍 UI Checkpoint — After the fix

Refresh each of the four dashboards in the Databricks UI. Every widget should now show data. Pay particular attention to the team names in **F1 TCC – Constructors** — they should be clean (`Red Bull Racing`, `Mercedes`, `McLaren`), confirming that the Teaching Moment 1 fix from Part 1 is flowing all the way through.

> **Why this matters:** A green API response is not a green dashboard. Build a screenshot step into any "publish a dashboard" workflow — the agent → action → screenshot → agent loop is the single biggest reliability win for AI/BI authoring.

---

## Back to the build — Phases 2 through 5

Tell Copilot to continue with the SWA scaffold, components, Genie panel, and API:

```
continue
```

Copilot will emit the Vite + React + TypeScript scaffold (Phase 2), the F1-themed components (Phase 3), the `AskGenie.tsx` panel (Phase 4), and the `/api/genie-chat` Azure Function (Phase 5) in parallel file-creation batches. `npm install` and `npm run build` should complete clean on the first try.

### 🔍 UI Checkpoint — Local `swa start`

Ask Copilot to run the SWA emulator locally:

```
Start the SWA emulator (swa start) so I can click through the app locally before deploying.
```

When the emulator is up, open **http://localhost:4280** and:

1. Click **Overview**, **Race Pace**, **Constructors**, **Drivers** in the left rail. Each route should render its dashboard iframe inside the `Telemetry` wrapper.
2. Click **Ask Genie**. Type a question like *"who won the constructors championship in 2021?"* and press send. You should get a Genie answer back through the local `/api/genie-chat` function (with your PAT being read from a local `.env`).
3. Click **New** in the chat panel. Send a follow-up question. The conversation should continue with context.

Leave the emulator running for the next teaching moment, or stop it — your choice.

---

## 🔎 Teaching Moment 2 — The Genie iframe 403

If you followed the prompt strictly, Copilot built an in-app chat panel backed by a server-side proxy — and the local emulator confirmed it works. **But should we have just used the built-in Databricks Genie iframe (`/embed/genie/{id}`) instead?** It's one line of code.

Let's find out.

Ask Copilot:

```
Just to compare, add a second route called "Genie (iframe)" that simply embeds
https://<your-workspace>/embed/genie/<GENIE_SPACE_ID> in a plain iframe. No
proxy, no API call, no auth wiring. Then open it in Playwright (Edge) as an
anonymous visitor and screenshot what loads.
```

When Playwright finishes, **open the screenshot Copilot took**.

<details>
<summary>💡 Hint (click to reveal)</summary>

The iframe doesn't render the Genie chat. It shows a Databricks **login page** — or a **403 Forbidden** — because the `/embed/genie/{id}` URL authenticates via the browser's Databricks session cookie. An anonymous SWA visitor has no such cookie.

</details>

### Your turn: craft the prompt

You've now seen *why* the in-app chat + server-side proxy pattern is necessary. What would you ask Copilot to do next?

A good prompt should:
- **(a)** Confirm the iframe pattern is not viable for anonymous visitors
- **(b)** Remove the throwaway "Genie (iframe)" route so it can't ship by accident
- **(c)** Add a comment in `staticwebapp.config.json` or the `RaceControl` route table explaining *why* there is no Genie iframe route — so the next maintainer doesn't "simplify" it back

Try writing your own prompt before looking at the reference.

<details>
<summary>📋 Reference prompt (click to reveal)</summary>

```
Confirmed — the /embed/genie/{id} iframe requires a Databricks browser session and is
not viable for anonymous SWA visitors. Please:

1. Remove the "Genie (iframe)" route, link, and component you just added.
2. Add a short comment in RaceControl.tsx (or wherever the route table lives) explaining
   that the Genie iframe path is not anonymous-visitor-safe, and that AskGenie.tsx +
   /api/genie-chat is the supported pattern.
3. Re-run npm run build to confirm the cleanup compiles.
```

</details>

### What Copilot will do

Copilot will delete the throwaway route and component, leave a load-bearing comment in the route table, and rebuild to confirm a clean tree.

> **Why this matters:** The Genie iframe is the *obvious* solution and the *wrong* solution for a public app. The in-app proxy keeps the Databricks session entirely server-side — the function holds the PAT, calls the Genie Conversation API, and streams the answer back as plain JSON. No browser session, no leaked token, no login prompt.

---

## Prompt 2 — Deploy to Azure

Time to ship. Run this prompt:

```
Now deploy to Azure. Specifically:

1. Make sure staticwebapp.config.json has the CSP frame-src header allowing
   *.azuredatabricks.net and *.cloud.databricks.com, and that allowedRoles is
   "anonymous" for all routes.
2. Confirm infra/main.bicep provisions the SWA Standard SKU and wires
   DBX_WORKSPACE_URL, DBX_SERVICE_PRINCIPAL_TOKEN, and DBX_GENIE_SPACE_ID as
   app settings (NOT as VITE_* — these are server-side secrets).
3. Confirm azure.yaml is wired for `azd up` end-to-end.
4. Confirm the GitHub Actions workflow at .github/workflows/azure-static-web-apps.yml
   injects the VITE_* values from repo secrets at build time and deploys via
   azure/static-web-apps-deploy@v1, with PR preview environments enabled.
5. Walk me through `azd up` step by step — initializing, prompting for the PAT
   and Genie space ID, provisioning the SWA, and capturing the public URL.
```

Follow the prompts in your terminal. `azd` will ask for an Azure subscription and a location, then provision the SWA, then deploy the build output. When it finishes you'll get a public `*.azurestaticapps.net` URL.

Push the repo to GitHub (Copilot can do this for you with `gh repo create`). Add your `VITE_*` values and the SWA deployment token as repo secrets — Copilot will tell you exactly which secret names the workflow expects. Trigger the workflow with a push to `main`.

### 🔍 UI Checkpoint — Live SWA on the public URL

Ask Copilot to verify the deployed site end-to-end:

```
Open the live SWA URL in Playwright (Edge). Click through every route — Overview,
Race Pace, Constructors, Drivers, Ask Genie — and take a screenshot of each. For
Ask Genie, send a real question and screenshot the answer.
```

You should see:

- All four dashboard iframes loading and rendering data (the CSP allow-list is working).
- The Ask Genie panel sending a question, calling `/api/genie-chat` on the SWA, and rendering the Genie response — with conversation continuity if you ask a follow-up.
- No console errors, no CORS errors, no 403s.

Open the GitHub Actions tab on your repo. You should see one successful workflow run. Open a throwaway pull request — within a couple of minutes you'll get a comment with a unique **preview URL** for that branch. Close the PR and the cleanup job tears the preview down.

> **Why this matters:** Build-time `VITE_*` vs runtime app settings is the boundary between "every visitor sees your PAT" and "your PAT never leaves the function host." Bicep enforces that boundary as code — there's no way to accidentally leak the SP token through the front-end bundle if you follow the pattern.

---

## Teardown

When you're done, clean up Azure to avoid unnecessary spend.

Run this prompt:

```
Please run `azd down --purge` to remove the Static Web App, the resource group,
and any associated resources. Then revoke the Databricks PAT we used for
DBX_SERVICE_PRINCIPAL_TOKEN.
```

If you also want to tear down the Part 1 Databricks artifacts, follow the teardown section of [`LAB.md`](./LAB.md) — drop the `formula1` catalog and stop the warehouse.

---

## Stuck or curious?

For the full narrative — every Copilot Callout, every lesson learned, every JSON shape that broke and how Copilot self-corrected — read [`DEMO_SWA_TELEMETRY.md`](https://github.com/MaxBush6299/dbx-swa/blob/main/DEMO_SWA_TELEMETRY.md) on `main`.

For an end-to-end reference of what the generated SWA repo looks like, browse the `main` branch of the [`dbx-swa`](https://github.com/MaxBush6299/dbx-swa) companion repo. Every file in there was emitted by the agent under operator supervision during the session this lab is based on.
