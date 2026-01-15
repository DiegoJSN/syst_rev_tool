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

<img src="/images/1.jpg" width="500" alt="1"> <img src="/images/2.jpg" width="450" alt="2">

---

## 2) Complete the form

1. Complete the form and click **“Next: Add your first device”**.
2. You’ll be redirected to a new page: click **“Skip this introduction.”**

<img src="/images/3.jpg" width="850" alt="1"> 
<img src="/images/4.jpg" width="850" alt="1"> 

---

## 3) Accept device invite (again)

1. Go back to the invitation email and click **“Accept device invite”** again.
2. You’ll be redirected to a page where you must click **“Accept invite.”**

<img src="/images/1.jpg" width="500" alt="1"> <img src="/images/6.jpg" width="500" alt="2">

4. After clicking **“Accept invite”**, you’ll be redirected to a new page. **Refresh** that page and confirm you can see the **server name** along with the **server admin email**.

<img src="/images/7.jpg" width="850" alt="1"> 

---

## 4) Install Tailscale

1. Download Tailscale:  
   https://tailscale.com/download
2. Install it like any normal application.

---

## 5) Log in and connect your device

1. Click the **Tailscale icon** in your **system tray/taskbar** (Windows) or **menu bar** (macOS). You’ll be taken to the sign-in page. **Log in** with your email address.

<img src="/images/8.jpg" width="850" alt="1"> 

3. Connect your device by clicking **“Connect.”** You should see a confirmation message indicating the connection was successful (**do not close this page yet**).

<img src="/images/9.jpg" width="500" alt="1"> <img src="/images/10.jpg" width="500" alt="1"> 

   - If you get this **error** after clicking **Connect**:
      ```text
      **Authorization failed**: device with nodekey:47uhjg34uyg34g78243284t2gf4ggg787g2g7 already exists; please log out explicitly and try logging in again
   - Open the terminal of your computer (in **Windows: PowerShell**; **macOS/Linux: Terminal**) and type these commands:
      ```bash
      tailscale logout
      tailscale down
      ```
   - After running those commands, go back to **step** 1 of this section (**5) Log in and connect your device**) and try it again.

---

## 6) Check everything is working

1. After a few seconds, you’ll be redirected to another page. You should now see two devices:
   - the **server device** (with the server admin email)
   - **your device** (with your email)
2. You can also click the **Tailscale icon** again to confirm it shows **“Connected.”**

<img src="/images/11.jpg" width="850" alt="1"> 

---

## 7) Enable “Use Tailscale DNS settings”

1. In the Tailscale app **Preferences**, make sure that **Use Tailscale DNS settings** is enabled (wording can vary slightly by OS).

<img src="/images/12.jpg" width="850" alt="1"> 

---

## 8) Open the server URL

1. The server admin will send you a URL similar to:

```text
https://<tailnet-name>.<tailnet-id>.ts.net
```


# FALTA AÑADIR AQUI LOS PASOS PARA ACEPTAR LA INVITACION A UN SEGUNDO DEVICE (POR SI CAMBIAS EL SERVER DE LUGAR) #
