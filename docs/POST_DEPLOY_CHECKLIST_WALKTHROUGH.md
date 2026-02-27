# Post-Deploy Checklist Walkthrough

A step-by-step guide to verify your YesCount deployment works end-to-end. Use this after deploying or restarting the app.

---

## What to do tomorrow (resume here)

Do these in order:

1. **Run manual Weekly Ingestion** (Step 2 below) — Yes, run it first. Fresh data plus the new curation filters (no news, closures, guides) will improve event quality.
2. **Wait for ingestion to finish** (5–15 min). Then restart the Streamlit app so it picks up the new events.
3. **Hard refresh the app** (Ctrl+Shift+R) to load the latest deployed code.
4. **Verify new features** — Swipe: mosaic 3/row, colorful boxes, LLM titles. Results: no errors. Calendar: full month, clickable dates.
5. **Continue checklist** — Steps 3–6 below (durability, full flow, invite link, logs).

---

## Step 1: Check readiness/liveness output

**What this means:** Make sure the app starts correctly and can talk to the database.

**What to do:**

1. Open your app URL in a browser (e.g. `https://your-app-name.streamlit.app`).
2. Wait for the page to fully load.
3. Look at what you see:
   - **Good:** The YesCount landing page loads with the hero image, "Lead A Plan For Your Crew", and "Join Your Crew's Plan" cards.
   - **Bad:** A red error box saying "Startup validation failed" or "Readiness check failed".
4. If you see a yellow warning like "Search embeddings are degraded" or "Automatic startup ingestion is degraded"—that's okay. Core features still work.

**Pass:** App loads without a red error box.

---

## Step 2: Run manual Weekly Ingestion in GitHub Actions

**What this means:** Populate the database with fresh events so users have something to vote on.

**What to do:**

1. Go to your GitHub repo (e.g. `https://github.com/YourUsername/yescount`).
2. Click the **Actions** tab at the top.
3. In the left sidebar, click **Weekly Ingestion**.
4. On the right, click the **Run workflow** button.
5. Leave the branch as `main` and click the green **Run workflow** button again.
6. Wait for the run to complete (usually 5–15 minutes).
7. Check the status:
   - **Green checkmark** = success.
   - **Red X** = failure; click the run to see the logs and error message.

**Pass:** The workflow run completes with a green checkmark.

---

## Step 3: Durability test — create session, add vote, restart app

**What this means:** Confirm your data is stored in Postgres and survives app restarts.

**What to do:**

1. **Create a session**
   - On the app landing page, use "Lead A Plan For Your Crew".
   - Enter a plan name (e.g. "Test Plan") and your name.
   - Click **Create plan**.
2. **Add a vote**
   - You should land on the Swipe view.
   - Check "Interested" on at least one event.
   - Click **Save votes and continue**.
3. **Restart the app**
   - In Streamlit Cloud: go to your app dashboard → **Settings** → **Restart app** (or redeploy).
   - Wait for the app to come back up.
4. **Confirm persistence**
   - Join the same session again (use the session link or "Join Your Crew's Plan" with the session ID).
   - Go to Swipe or Results.
   - Your vote should still be there.

**Pass:** Your vote is still there after the restart.

---

## Step 4: End-to-end flow — create → join → vote → availability → recommendations

**What this means:** Run through the full user journey to ensure nothing is broken.

**What to do:**

1. **Create** — Create a new plan (or reuse one). Note the session link or ID.
2. **Join** — Open the session link in a new tab or incognito window (or use another device). Enter your name and join.
3. **Vote** — Mark "Interested" on several events. Click **Save votes and continue**.
4. **Availability** — On the calendar, select "Available" for some dates. Click **Submit availability**.
5. **Recommendations** — Click **See results**. You should see recommendations and "Best dates to gather your crew".

**Pass:** You can complete the full flow without errors.

---

## Step 5: Verify session links and invite text in a real browser

**What this means:** Ensure sharing and invites work correctly.

**What to do:**

1. On the Results page, find the **Invite text** text area.
2. Copy the invite text.
3. Paste it into a messaging app or email (or just a new browser tab).
4. Click the session link in the invite.
5. Confirm it opens the correct session in the browser.

**Pass:** The link works and the invite text looks correct.

---

## Step 6: Inspect logs for errors

**What this means:** Catch any hidden issues.

**What to do:**

1. In Streamlit Cloud, open your app dashboard.
2. Go to **Manage app** → **Logs** (or similar).
3. Scroll through the recent logs.
4. Look for lines containing `Error`, `Exception`, or `Traceback`.
5. If you see errors, note the message and when it occurred.

**Pass:** No critical errors in the logs.

---

## Quick summary

| Step | Action | Pass condition |
|------|--------|----------------|
| 1 | Open app URL | App loads without red error |
| 2 | Run Weekly Ingestion in GitHub Actions | Workflow run succeeds |
| 3 | Create session, vote, restart app | Vote still there after restart |
| 4 | Full flow: create → join → vote → availability → results | All steps complete |
| 5 | Copy invite text and test session link | Link opens correct session |
| 6 | Check Streamlit logs | No critical errors |

If all six steps pass, your deployment is verified and ready for normal use.
