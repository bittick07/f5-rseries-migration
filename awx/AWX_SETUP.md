# AWX Configuration Guide

This directory contains AWX configuration for the F5 iSeries to rSeries migration.

---

## AWX Setup Steps

### 1. Create Credentials

Go to **Credentials > Add** and create the following:

#### iSeries SSH Credential
| Field | Value |
|---|---|
| Name | F5 iSeries SSH |
| Credential Type | Machine |
| Username | root |
| Password | `<iseries root password>` |

#### rSeries API Credential
| Field | Value |
|---|---|
| Name | F5 rSeries API |
| Credential Type | Machine |
| Username | admin |
| Password | `<rseries admin password>` |

#### BIG-IP Tenant Credential
| Field | Value |
|---|---|
| Name | F5 BIG-IP Tenant |
| Credential Type | Machine |
| Username | admin |
| Password | `<tenant admin password>` |

---

### 2. Create the Project

Go to **Projects > Add**:

| Field | Value |
|---|---|
| Name | F5 rSeries Migration |
| Organization | Default |
| Source Control Type | Git |
| Source Control URL | `https://your-gitlab-instance/f5-rseries-migration.git` |
| Source Control Branch | main |
| Source Control Credential | Your GitLab credential |
| Update Revision on Launch | Checked |

---

### 3. Create the Inventory

Go to **Inventories > Add**:

| Field | Value |
|---|---|
| Name | F5 Migration Inventory |
| Organization | Default |

Then add the following **Variables** on the inventory:

```yaml
iseries_host: "192.168.1.10"
rseries_host: "192.168.1.20"
tenant_mgmt_ip: "192.168.1.30"
tenant_mgmt_prefix: "24"
tenant_mgmt_gateway: "192.168.1.1"
tenant_hostname: "bigip-rseries01.example.com"
tenant_name: "bigip-tenant1"
tenant_image: "BIGIP-17.1.0-0.0.16.ALL-F5OS"
tenant_vcpus: 4
tenant_memory: 14848
tenant_vlans:
  - 100
  - 200
  - 300
modules:
  ltm: nominal
  gtm: nominal
```

---

### 4. Create Job Templates

Create a Job Template for each playbook stage:

#### Template 1: Deploy Tenant
| Field | Value |
|---|---|
| Name | F5 - 01 Deploy Tenant |
| Job Type | Run |
| Inventory | F5 Migration Inventory |
| Project | F5 rSeries Migration |
| Playbook | ansible/playbooks/01_deploy_tenant.yml |
| Credentials | F5 rSeries API |
| Extra Variables | See below |

#### Template 2: Provision Modules
| Field | Value |
|---|---|
| Name | F5 - 02 Provision Modules |
| Playbook | ansible/playbooks/02_provision_modules.yml |
| Credentials | F5 BIG-IP Tenant |

#### Template 3: Pull SCF
| Field | Value |
|---|---|
| Name | F5 - 03 Pull SCF |
| Playbook | ansible/playbooks/03_pull_scf.yml |
| Credentials | F5 iSeries SSH |

#### Template 4: Edit SCF
| Field | Value |
|---|---|
| Name | F5 - 04 Edit SCF |
| Playbook | ansible/playbooks/04_edit_scf.yml |
| Credentials | (none needed - runs locally) |

#### Template 5: Apply SCF
| Field | Value |
|---|---|
| Name | F5 - 05 Apply SCF |
| Playbook | ansible/playbooks/05_apply_scf.yml |
| Credentials | F5 iSeries SSH, F5 BIG-IP Tenant |

#### Template 6: Verify
| Field | Value |
|---|---|
| Name | F5 - 06 Verify Migration |
| Playbook | ansible/playbooks/06_verify.yml |
| Credentials | F5 BIG-IP Tenant |

---

### 5. Create the Workflow Template

Go to **Templates > Add > Add Workflow Template**:

| Field | Value |
|---|---|
| Name | F5 iSeries to rSeries Migration |
| Organization | Default |
| Inventory | F5 Migration Inventory |

Then in the **Workflow Visualizer**, chain the job templates in order:

```
01 Deploy Tenant
      ↓ (on success)
02 Provision Modules
      ↓ (on success)
03 Pull SCF
      ↓ (on success)
04 Edit SCF
      ↓ (on success)
05 Apply SCF
      ↓ (on success)
06 Verify Migration
```

Set **05 Apply SCF** to require **approval** before running (go to the node settings and enable **Prompt on Launch** or use an **Approval Node** before it in the workflow) so a human can review the verify output before the SCF is actually merged.

---

### 6. AWX Extra Variables

Set these as **Extra Variables** on the Workflow Template or in the AWX inventory. These override vars/migration_vars.yml:

```yaml
iseries_host: "192.168.1.10"
rseries_host: "192.168.1.20"
tenant_mgmt_ip: "192.168.1.30"
tenant_mgmt_gateway: "192.168.1.1"
tenant_hostname: "bigip-rseries01.example.com"
```

---

### 7. Environment Variables for Passwords

AWX passes credentials as environment variables. In each Job Template, under **Extra Variables** or using **Custom Credential Types**, map:

| AWX Credential Field | Environment Variable |
|---|---|
| iSeries Password | `ISERIES_PASSWORD` |
| rSeries Password | `RSERIES_PASSWORD` |
| Tenant Password | `TENANT_PASSWORD` |

To do this cleanly, create a **Custom Credential Type** in AWX:

**Input Configuration:**
```yaml
fields:
  - id: iseries_password
    type: string
    label: iSeries Password
    secret: true
  - id: rseries_password
    type: string
    label: rSeries Password
    secret: true
  - id: tenant_password
    type: string
    label: Tenant Password
    secret: true
```

**Injector Configuration:**
```yaml
env:
  ISERIES_PASSWORD: "{{ iseries_password }}"
  RSERIES_PASSWORD: "{{ rseries_password }}"
  TENANT_PASSWORD: "{{ tenant_password }}"
```

---

### 8. Notifications (Optional)

Under each Job Template, add **Notifications** for on-success and on-failure to send alerts to Slack, email, or Teams so the team knows when each stage completes or fails.

---

## Workflow Diagram

```
┌─────────────────────────────────────────────────────┐
│           AWX Workflow: F5 Migration                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  [01 Deploy Tenant] ──► [02 Provision Modules]      │
│                                ↓                     │
│                       [03 Pull SCF]                  │
│                                ↓                     │
│                       [04 Edit SCF]                  │
│                                ↓                     │
│                    ⚠ [APPROVAL NODE] ⚠               │
│                                ↓                     │
│                       [05 Apply SCF]                 │
│                                ↓                     │
│                    [06 Verify Migration]              │
│                                                      │
└─────────────────────────────────────────────────────┘
```
