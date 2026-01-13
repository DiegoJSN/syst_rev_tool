# CLIENT SETUP: Instructions for reviewers

Reviewer (client) setup guide (Tailscale + browser access)

## Quick start

This guide is for **reviewers** (clients). You only need:
- **Tailscale** installed and connected
- A **browser** to open the server URL

---

## 1) Ask the server admin to invite you

1. **Send the server admin the email address** you use (or will use) to log into Tailscale.
   - If you use an **institutional email** and the admin’s tailnet is tied to a different identity provider (for example, a personal email or a different institutional email), you may get an **Error 403** when trying to join. If that happens, send the admin a **personal email** (Gmail, Outlook, etc.) instead.
2. **Wait for the invitation** email from Tailscale.
3. **Accept the invitation** and **log into Tailscale** using that same email account.

![Invitation email and sign-in page](assets_client_setup_new/client_setup_new_page_1.png)

---

## 2) Complete the form

1. Complete the form and click **“Next: Add your first device”**.
2. You’ll be redirected to a new page: click **“Skip this introduction.”**

![Tailscale onboarding form and “Skip this introduction”](assets_client_setup_new/client_setup_new_page_2.png)

---

## 3) Accept device invite (again)

1. Go back to the invitation email and click **“Accept device invite”** again.
2. You’ll be redirected to a page where you must click **“Accept invite.”**
3. After clicking **“Accept invite”**, you’ll be redirected to a new page. **Refresh** that page and confirm you can see the **server name** along with the **server admin email**.

![Accept invite and verify you can see the server](assets_client_setup_new/client_setup_new_page_3.png)

---

## 4) Install Tailscale

1. Download Tailscale:  
   https://tailscale.com/download
2. Install it like any normal application.

![Download instructions](assets_client_setup_new/client_setup_new_page_4.png)

---

## 5) Log in and connect your device

1. Click the **Tailscale icon** in your **system tray/taskbar** (Windows) or **menu bar** (macOS). You’ll be taken to the sign-in page. **Log in** with your email address.
2. Connect your device by clicking **“Connect.”** You should see a confirmation message indicating the connection was successful (**do not close this page yet**).

![Sign in and connect](assets_client_setup_new/client_setup_new_page_4.png)

---

## 6) Check everything is working

1. After a few seconds, you’ll be redirected to another page. You should now see two devices:
   - the **server device** (with the server admin email)
   - **your device** (with your email)
2. You can also click the **Tailscale icon** again to confirm it shows **“Connected.”**

![Verify both devices and “Connected” status](assets_client_setup_new/client_setup_new_page_5.png)

---

## 7) Enable “Use Tailscale DNS settings”

1. In the Tailscale app **Preferences**, make sure that **Use Tailscale DNS settings** is enabled (wording can vary slightly by OS).

![DNS settings](assets_client_setup_new/client_setup_new_page_5.png)

---

## 8) Open the server URL

1. The server admin will send you a URL similar to:

```text
https://<tailnet-name>.<tailnet-id>.ts.net
```

![Example URL format](assets_client_setup_new/client_setup_new_page_6.png)
