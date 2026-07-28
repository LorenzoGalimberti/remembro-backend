# Remembro Backend

Backend Django + DRF per Remembro. Vedi la specifica funzionale e il piano operativo nel repo/documenti di progetto per il contesto completo.

## Stack

- Django + Django REST Framework
- PostgreSQL (via Docker Compose)
- Celery + Redis (task asincroni, non ancora configurati — Fase 4+)
- Ambiente di sviluppo: WSL2 (Ubuntu) su Windows

## Come riprendere il progetto (ogni volta)

### 1. Apri il terminale Ubuntu (WSL)

Cerca "Ubuntu" nel menu Start di Windows, oppure da PowerShell:
```bash
wsl -d Ubuntu
```

### 2. Vai nella cartella del progetto

```bash
cd /mnt/c/Users/loren/Desktop/transfer/HERA/remembro/remembro-backend
```

### 3. Avvia Docker Desktop (se non è già in esecuzione)

Aprilo dal menu Start di Windows e aspetta che dica "Engine running" in basso a sinistra.

### 4. Avvia Postgres e Redis

```bash
docker compose up -d
```

Verifica che siano su:
```bash
docker compose ps
```

### 5. Attiva il virtual environment Python

```bash
source venv/bin/activate
```

Il prompt deve mostrare `(venv)` all'inizio della riga. Se manca il venv o dà errori, va ricreato da zero (vedi sezione Troubleshooting).

### 6. Avvia il server Django

```bash
python manage.py runserver
```

Apri il browser su:
- **App/API**: http://127.0.0.1:8000/
- **Admin**: http://127.0.0.1:8000/admin/ (login: `lorenzo`, la password che hai scelto con `createsuperuser`)

### Per fermare tutto a fine sessione

```bash
# Ctrl+C per fermare il server Django
docker compose down   # ferma Postgres e Redis (opzionale, puoi anche lasciarli su)
```

---

## Struttura del progetto

```
remembro-backend/
├── manage.py
├── requirements.txt          # dipendenze Python
├── docker-compose.yml        # Postgres + Redis per dev locale
├── .env                       # variabili d'ambiente (NON committato — vedi sotto)
├── remembro_backend/          # configurazione progetto Django (settings, urls)
├── categories/                 # app: categorie/deck dell'utente
│   └── fixtures/seed_data.json # dati di esempio per test manuali
├── notions/                    # app: nozioni grezze catturate dall'utente
├── cards/                      # app: card di ripasso generate dalle nozioni
└── reviews/                    # app: log delle sessioni di ripasso (ReviewLog)
```

## Variabili d'ambiente (`.env`)

Il file `.env` **non è su Git** (è nel `.gitignore`, giustamente — contiene la SECRET_KEY). Se lo perdi o lavori su un'altra macchina, ricrealo così:

```bash
cat > .env << 'EOF'
DEBUG=True
SECRET_KEY=<genera una nuova chiave, vedi sotto>
DATABASE_URL=postgres://remembro:remembro_dev_password@localhost:5432/remembro
REDIS_URL=redis://localhost:6379/0
LLM_API_KEY=
EXPO_ACCESS_TOKEN=
EOF
```

Per generare una nuova `SECRET_KEY`:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Caricare i dati di esempio (fixture)

Dopo un `migrate` su un database pulito, per avere subito una categoria, una notion e una card di test:

```bash
python manage.py loaddata categories/fixtures/seed_data.json
```

## Comandi utili

```bash
# Creare un nuovo superuser (accesso admin)
python manage.py createsuperuser

# Vedere lo stato delle migrazioni
python manage.py showmigrations

# Generare migrazioni dopo aver modificato un modello
python manage.py makemigrations
python manage.py migrate

# Aprire una shell Python con i modelli già importabili
python manage.py shell

# Controllare che il progetto non abbia errori di configurazione
python manage.py check

# Ispezionare il database Postgres direttamente
docker compose exec postgres psql -U remembro -d remembro
# dentro psql: \dt per elencare le tabelle, \q per uscire
```

---

## Stato di avanzamento (piano operativo)

- ✅ **Fase 0** — Setup progetto (repo, Django+DRF, Docker Compose, Expo, CI)
- ✅ **Fase 1** — Data model (app `categories`/`notions`/`cards`/`reviews`, modelli, migrazioni, admin, fixture)
- ⬜ **Fase 2** — Autenticazione (JWT, endpoint registrazione/login/refresh)
- ⬜ **Fase 3** — API core (CRUD)
- ⬜ **Fase 4+** — vedi `remembro_piano_operativo_mvp.md`

## Troubleshooting

**`docker: command not found`**
Docker Desktop non è avviato, o l'integrazione WSL non è attiva. Apri Docker Desktop → Settings → Resources → WSL Integration → verifica che "Ubuntu" sia attivo.

**`permission denied ... docker.sock`**
Il tuo utente non è nel gruppo `docker`:
```bash
sudo usermod -aG docker $USER
```
poi da PowerShell: `wsl --shutdown`, e riapri il terminale Ubuntu.

**Il venv non si attiva / `venv/bin/activate: No such file or directory`**
Il venv potrebbe essere stato creato con Python di Windows invece che di Linux (cartella `Scripts/` invece di `bin/`). Ricrealo dentro WSL:
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**`ModuleNotFoundError: No module named 'categories'` (o notions/cards/reviews)**
Le app non esistono ancora su disco ma sono già in `INSTALLED_APPS`. Commenta temporaneamente le 4 righe in `INSTALLED_APPS`, lancia `python manage.py startapp <nome>`, poi rimettile.

**Postgres non raggiungibile / connection refused**
```bash
docker compose ps       # verifica che i container siano "Up"
docker compose up -d    # riavvia se serve
```