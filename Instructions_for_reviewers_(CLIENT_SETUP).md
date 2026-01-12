# CLIENT SETUP: Instructions for reviewers

Reviewer (client) setup guide (Tailscale + browser access)

## Quick start

This guide is for **reviewers** (clients). You only need:
- **Tailscale** installed and connected to the correct tailnet
- A **browser** to open the server URL

---

## 1) Ask the server admin to invite you to the server tailnet (required)

You must be added to the **same Tailscale network (tailnet)** as the server.

1. **Send the server admin the email address** you use (or will use) to log into Tailscale.
    - If you use an **institutional email** and the admin’s tailnet is tied to a different identity provider (for example, a personal email or a different institutional email), you may get an **Error 403** when trying to join. If that happens, send the admin a **personal email** (Gmail, Outlook, etc.) instead.
2. **Wait for the invitation** email from Tailscale.
3. **Accept the invitation** and log into Tailscale using that same email account.

<img src="https://github.com/user-attachments/assets/6f514078-301c-4b5f-a943-bfd7afcf3df4" width="500" alt="1_3_1">
<img src="https://github.com/user-attachments/assets/b57fe401-4e6b-4e10-a242-db004a0cfff9" width="390" alt="1_3_2">

   
4. **Join the tailnet** and wait for the server admin's approval.
    - If you see **Error 403**, it usually means your email domain/identity provider is not allowed in that tailnet. Contact the server admin and ask them to send the invitation to your **personal email** instead.
<img src="https://github.com/user-attachments/assets/ea1cc9ad-b50d-44a9-a307-8c1a9cd0e789" width="350" alt="1_4">
<img src="https://github.com/user-attachments/assets/27c0bf46-f0cf-46f5-9637-c281212efd48" width="520" alt="1_5">

---

## 2) Install Tailscale


1. Download Tailscale:
    - [https://tailscale.com/download](https://tailscale.com/download)

3. Install it like any normal application.

---

## 3) Log in to the correct tailnet

This is the step where most mistakes happen.

1. Open Tailscale
2. Click **Sign in to your network**
<img src="https://github.com/user-attachments/assets/13ff2282-c8e0-43d6-a73a-d43687b54d12" width="380" alt="3_2">

3. Log in using your email/account
   
4. **Important**:
     - After logging in, **you have to select the Tailscale server admin's network** (i.e. its email address, **not yours**). In other words: you must join the **same tailnet** as the server admin, or you will not see the server and the URL will not open.

<img src="https://github.com/user-attachments/assets/91ffda18-780d-4454-83e6-b1d728a5fdb2" width="450" alt="3_4">


5. After login, click on the Tailscale app (the icon is in the taskbar), and confirm:
    - Tailscale: **Connected**

---

## 4) Enable “Use Tailscale DNS settings”

1. In the Tailscale app settings:
   - Make sure that **Use Tailscale DNS settings** is enabled (wording can vary slightly by OS).

<img src="https://github.com/user-attachments/assets/1f1a7651-597c-49ac-8254-534d2ce53a19" width="650" alt="4_1">

---

## 5) Open the server URL

1. The server admin will send you a URL similar to:
```text
https://<tailnet-name>.<tailnet-id>.ts.net
```

