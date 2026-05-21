# F5 iSeries to rSeries Migration

Ansible automation for migrating F5 BIG-IP configuration from iSeries to rSeries tenants. Designed to run via **AWX** or the GitLab CI/CD pipeline.

---

## What This Does

1. Deploys a BIG-IP tenant on the rSeries via the F5OS API
2. Provisions LTM and GTM modules on the tenant
3. Pulls the SCF config file from the source iSeries
4. Edits the SCF automatically (strips hardware-specific objects, fixes line endings, updates mgmt IP/gateway)
5. Transfers the master key from iSeries to rSeries tenant
6. Verifies the SCF before applying
7. Merges the SCF onto the rSeries tenant
8. Validates virtual servers and pools post-migration

---

## Requirements

- AWX or Ansible >= 2.12
- Python 3.8+
- F5 Ansible collection: `f5networks.f5_modules`
- SSH access to both iSeries and rSeries
- rSeries BIG-IP tenant image already uploaded to F5OS

---

## Quick Start

### 1. Install Dependencies

```bash
ansible-galaxy collection install f5networks.f5_modules
pip install f5-sdk requests pyyaml
```

### 2. Configure Variables

Edit `vars/migration_vars.yml` with your environment details.

### 3. Store Secrets

**Never hardcode passwords.** Use AWX Credentials or GitLab CI/CD Variables:

| Variable | Description |
|---|---|
| `ISERIES_PASSWORD` | iSeries root password |
| `RSERIES_PASSWORD` | rSeries F5OS admin password |
| `TENANT_PASSWORD` | BIG-IP tenant admin password |

### 4. Run via AWX

Import this repo into AWX as a Project, then create Job Templates for each playbook. See `awx/` directory for AWX configuration exports.

### 5. Run via GitLab CI

Push to `main` branch to trigger the full pipeline, or run individual stages manually.

### 6. Run Manually

```bash
# Full migration
ansible-playbook ansible/playbooks/site.yml -i ansible/inventory/hosts.yml

# Individual stages
ansible-playbook ansible/playbooks/01_deploy_tenant.yml
ansible-playbook ansible/playbooks/02_provision_modules.yml
ansible-playbook ansible/playbooks/03_pull_scf.yml
ansible-playbook ansible/playbooks/04_edit_scf.yml
ansible-playbook ansible/playbooks/05_apply_scf.yml
ansible-playbook ansible/playbooks/06_verify.yml
```

---

## SCF Objects Removed Automatically

| Object | Reason |
|---|---|
| `sys management-ip` | Replaced with rSeries tenant values |
| `sys management-route` | Replaced with rSeries tenant values |
| `cm device` | Hardware specific, rSeries generates its own |
| `cm cert / cm key (dtca, dtos, dtdi)` | Old HA device trust, rSeries generates its own |
| `cm bundle` | Old HA device trust |
| `cm device-group` | Must be rebuilt manually after migration |
| `cm trust-domain` | Must be rebuilt manually after migration |
| `net trunk` | Handled at F5OS layer |
| `net stp` | Handled at F5OS layer |
| `net fdb` | Hardware specific |
| `net vlan` | Inherited from F5OS layer |
| `net interface` | Hardware specific (iSeries port names) |
| `turboflex` | iSeries only, not supported on rSeries |
| `apm epsec` | APM not provisioned on rSeries |
| `data-publisher` | APM/analytics remnant |

---

## Directory Structure

```
f5-rseries-migration/
├── ansible/
│   ├── inventory/         # Hosts and connection details
│   ├── group_vars/        # Group level variables
│   ├── playbooks/         # Individual migration playbooks
│   └── roles/             # Reusable role components
├── awx/                   # AWX job templates and workflow exports
├── scripts/               # Python SCF editing and validation scripts
├── templates/             # Jinja2 templates
├── vars/                  # Migration variables
└── .gitlab-ci.yml         # GitLab CI/CD pipeline
```
