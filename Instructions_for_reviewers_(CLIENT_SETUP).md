# CLIENT SETUP: Instructions for reviewers

Reviewer (client) setup guide (Tailscale + browser access)

## Quick start

This guide is for **reviewers** (clients). You only need:
- Tailscale installed and connected to the correct tailnet
- A browser to open the server URL

---

## 1) Ask the server admin to invite you to the server tailnet (required)

You must be added to the **same Tailscale network (tailnet)** as the server.

1. Send the server admin the email address you use (or will use) to log into Tailscale.
2. Wait for the invitation email.
3. Accept the invitation and confirm you can see the tailnet in your Tailscale account.

Important:
- If you do not accept the invitation, you will not be able to access the server URL.

---

## 2) Install Tailscale

Download Tailscale:
- [https://tailscale.com/download](https://tailscale.com/download)

Install it like any normal application.

---

## 3) Log in to the correct tailnet (do not mix accounts)

This is the step where most mistakes happen.

1. Open Tailscale
2. Click **Log in**
3. Log in using your email/account

**Important**:
- After logging in, **you have to select the Tailscale server admin's network** (i.e. its email address, **not yours**). In other words: you must join the **same tailnet** as the server admin, or you will not see the server and the URL will not open.

After login, in the Tailscale app, confirm:
- Status: **Connected**

---

## 4) Enable “Use Tailscale DNS settings”

In the Tailscale app settings:
- Enable **Use Tailscale DNS settings** (wording can vary slightly by OS)

---

## 5) Open the server URL

The server admin will send you a URL similar to:
```text
https://syst-rev-server.<tailnet-name>.ts.net


