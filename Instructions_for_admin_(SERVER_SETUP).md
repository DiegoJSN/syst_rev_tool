# SERVER SETUP: Instructions for the server admin

Server setup guide (PostgreSQL + Tailscale + Python app)

## Quick start

This guide is for the **server machine** that will host:
- The **PostgreSQL database** (on port 5432)
- The **Python web app** (runs on port 5000 locally)
- **Tailscale Serve**, so reviewers can access the app in their browser over Tailscale

## Before you start (important)
- Use a machine that can stay **powered on** and **connected to the internet**.
- Disable sleep/hibernation on the server (otherwise the app becomes unreachable).
  - Windows: Settings → System → Power & battery → Screen and sleep → set to **Never**.
- Have **admin rights** on the server.

---

## 1) Install PostgreSQL and create the database

1. Download and install PostgreSQL
    - [https://www.postgresql.org/download/](https://www.postgresql.org/download/)
    
2. During installation, note these settings:
    - Port: **5432**
    - Set a strong password for the ``postgres`` superuser (you will need this later)
    - Install pgAdmin 4 (usually selected by default)

---

## 2) Create the database user + database

After the installation, create:
- A dedicated database user (for example: `review_user`)
- A database owned by that user (for example: `systrev_db`)

Two different options for doing this:

### Option A: Using the terminal (`psql`)
1. Open a terminal and connect as the `postgres` superuser:
```bash
psql -h localhost -p 5432 -U postgres -d postgres
```

2. It will ask for a pasword: enter the password you set during installation.

3. Create the user (edit username/password):

```sql
CREATE USER review_user WITH PASSWORD 'your_strong_password_here';
```

4. Create the database and set the owner:

```sql
CREATE DATABASE systrev_db OWNER review_user;
```

5. Exit psql
```sql
\q
```

### Option B: Using pgAdmin (GUI)
1. Open **pgAdmin 4** and connect to your local server
2. Open **Query Tool** in pgAdmin and run (edit values):
```sql
CREATE USER review_user WITH PASSWORD 'your_strong_password_here';
CREATE DATABASE systrev_db OWNER review_user;
```


---

## 3) Allow PostgreSQL connections from your Tailscale network
By default, PostgreSQL often listens only on localhost. To allow connections coming from Tailscale:

1. Open and edit ```postgresql.conf```
    - Find your ```postgresql.conf``` file (Windows  usually have it under the PostgreSQL “data” directory, something like ```C:\Program Files\PostgreSQL\<version>\data\```).
    - Set ```listen_addresses``` to include your Tailscale interface. The simplest option is:
    ```conf
    listen_addresses = '*'
    ```
    - With this, PostgreSQL listens for connections; the actual restriction is carried out in ```pg_hba.conf``` and the firewall.

2. Open and edit ```pg_hba.conf```
    - In ```pg_hba.conf```, add a rule to allow only Tailscale IPs (CGNAT range) to reach your DB (you can add this line at the end of the file):
    ```conf
    host    systrev_db   review_user   100.64.0.0/10   scram-sha-256
    ```
    - This enables any device on the Tailnet (Tailscale 100.x IP addresses) to connect to the database and user.

3. Restart PostgreSQL
Restart the PostgreSQL service so changes apply.
    - Windows:
        - Win + R
        - Type ``services.msc`` and press Enter
        - Search for a service type:
            - ``postgresql-x64-16`` (or 15, 14…)
        - Right click -> **Restart**

---

## 4) Install Tailscale

1. Download Tailscale:
    - [https://tailscale.com/download](https://tailscale.com/download)

3. Install it like any normal application.

4. Log in to the correct tailnet
    - Open Tailscale
    - Click **Log in**
    - Make sure you log into the **tailnet you will share with reviewers**
    
---

## 5) Enable MagicDNS
MagicDNS lets you use a stable hostname (recommended), for example:
    - ``syst-rev-server``
1. In the Tailscale admin console:
    - Go to **DNS**
    - Enable **MagicDNS**
    - In **HTTPS Certificates**, tap **Enable HTTPS** and accept the consent.
    
2. In the Tailscale app settings:
   - Make sure that **Use Tailscale DNS settings** is enabled (wording can vary slightly by OS).

## 6) Rename the server device
In the Tailscale admin console
- Go to **Machines** 
- Rename the server to something simple like: ``syst-rev-server``
    - This will be used as the hostname inside your tailnet (with MagicDNS).
    
## 7) Open PostgreSQL port 5432 in the firewall (Tailscale only)
You want PostgreSQL reachable only over Tailscale, not from the public internet.
- Windows (GUI method):
    1. Win + R 
    2. Type ``wf.msc`` and press Enter
    3. On the right side: Inbound Rules -> **New Rule...**
    4. Rule Type: **Port**
    5. Protocol: **TCP**
    6. Specific local ports: **5432**
    7. Action: **Allow the connection**
    8. Profile: usually **Private** (and Domain if applicable). Do not select Public
    9. Name it: ``PostgreSQL 5432 (Tailscale)``
    Now restrict the rule to Tailscale IPs:
    1. Find the rule you created → right click → Properties
    2. Go to **Scope**
    3. Remote IP address → “These IP addresses” → Add:
        - ``100.64.0.0/10``

---

## 8) Install Python
1. Download PythonL
    - [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Windows notes:
    - During install, check: **Add Python to PATH**

---

## 9) Download the GitHub project and install dependencies
1. Download this project: download ZIP from GitHub and extract it.

2. Install dependencies (choose one option)

### Option A (recommended): Run the automatic setup script (Windows)
1. In the extracted project folder, double-click ``server_setup.bat``
2. Wait until the script finishes. If everything goes well, you should see a success message saying:
    ```bash
    Setup is complete. Check and configure the .env file, then run the run.bat file.
    ```

### Option B: Install manually using a terminal (Windows/macOS/Linux)

1. Open a terminal 
    - Windows: PowerShell
    - macOS: Terminal
    - Linux: Terminal

2. Go to the project folder. Then:
    ```bash
    # Windows:
    cd C:\path\to\project
    # macOS/Linux:
    cd /path/to/project
    ```
3. Create a virtual environment (venv):
    ```bash
    python -m venv venv
    ```
4. Activate venv
    ```bash
    # Windows:
    venv\Scripts\activate
    # maxOS/Linux:
    source venv/bin/activate
    ```
5. Install requirements:
    ```bash
    pip install -r requirements.txt
    ```

---

## 10) Configure the ``.env`` file
1. Copy the file ``.env_example`` and rename it to ``.env``
2. Edit ``.env`` and set your DATABASE_URL:
    - Required format:
    ```text
    DATABASE_URL="postgresql://{user_name}:{password}@{magicdns_hostname OR tailscale_ip}:5432/{db_name}"
    ```
    - Example 1 (with ecommended with MagicDNS hostname):
    ```text
    DATABASE_URL="postgresql://review_user:your_strong_password_here@syst-rev-server:5432/systrev_db"
    ```
    
    - Example 2 (using a Tailscale IP):
    ```text
    DATABASE_URL="postgresql://review_user:your_strong_password_here@100.104.194.28:5432/systrev_db"
    ```

---

## 11) Run the app on the server and expose the web app to reviewers with Tailscale Serve

Two options:

### Option A (recommended): Run the automatic run server script (Windows)
1. In the extracted project folder, double-click ``run_server.bat``
2. Wait until the script finishes. If everything goes well, you should see a message saying 
    ```bash
    Serve started and running in the background.
    ```
    - **Do not close this terminal window**. If you close it, the server will stop and the app will become unreachable.



### Option B: using a terminal (Windows/macOS/Linux)
1. Open the terminal and go to the project folder.
2. Activate venv
3. With the venv activated, type:
    ```bash
    python app.py
    ```
4. Confirm it works locally on the server:
    ```text
    http://127.0.0.1:5000
    ```

5. Enable Serve for your tailnet (one-time)
    - If Serve is disabled, Tailscale will tell you and give you a URL to enable it in the admin console.
6. Start Serve
    - Open the terminal, and type:
    ```bash
    tailscale serve --bg 5000
    ```
    This publishes your local app (running on 127.0.0.1:5000) as an HTTPS URL inside your tailnet.
    
    
    

---

## 12) Run the app on the server and expose the web app to reviewers with Tailscale Serve

3. Share the URL with reviewers:
    - ``tailscale serve`` will show a URL similar to:
    ```text
    https://syst-rev-server.<your-tailnet-name>.ts.net
    ```
    That is the URL reviewers should open.



---

## 13) Share the server machine with reviewers (Device Sharing):
In the Tailscale Admin Console:
1. Go to the **Machines** tab.
2. Find your server machine, click the **three dots (… )** menu, then select **Share**.
3. Open the **Share via email** tab.
4. Enter the reviewer’s email address and click **Share**.

---
