# Seed Assets

This folder holds scaffold-era seed assets for the new Django web application.

## Included

- `csv/supply_usage_sample.csv`
- `csv/maintenance_schedule_sample.csv`
- `csv/legacy_catalog/` copied from the archived starter backend

## Seed Command

Run the demo seeder from `server/`:

```bash
python manage.py bootstrap_demo_data --reset
```

This seeds the prompt-2 demo dataset:

- 7 regions and 7 supply hubs
- 38 stores with realistic coordinates
- logistics managers for Regions A-G
- Region C repair staff assignments
- store managers/admins, account users, and guest-order fixtures
- inventory balances, local suppliers, transfers, machines, maintenance records, imports, schedules, notifications, audit logs, and sync events

`python manage.py seed_codepop` remains available as an alias for the same command.
