# Setting Up NFS on Synology for Kubernetes

This guide configures a Synology NAS (DSM 7.2) as an NFS backend for Kubernetes PersistentVolumeClaims. The `nfs-subdir-external-provisioner` on the cluster will dynamically create subdirectories on the NFS share for each PVC.

## Prerequisites

- Admin access to Synology DSM (web interface)
- Synology NAS at `192.168.0.102` on the same subnet as your Kubernetes cluster nodes

## Steps

### 1. Enable NFS Service

1. Open **Control Panel** > **File Services**
2. Click the **NFS** tab
3. Check **Enable NFS service**
4. Set **Maximum NFS protocol** to **NFSv4.1**
5. Click **Apply**

**Verification:** The NFS service status should show **"Running"** at the top of the NFS tab.

### 2. Create a Shared Folder for Kubernetes

1. Open **Control Panel** > **Shared Folder**
2. Click **Create** > **Create Shared Folder**
3. Fill in the details:

| Field | Value |
|-------|-------|
| **Name** | `k8s` |
| **Description** | (optional) Kubernetes persistent storage |
| **Location** | Volume 1 |

The path will be `/volume1/k8s`.

4. On the next screen (Advanced Settings):
   - ~~**Do NOT** enable data checksum (unnecessary overhead for Kubernetes workloads)~~
     - **Enable** data checksum: minor overhead, but prevents silent corruption from propagating into backups undetected
   - Leave encryption disabled
5. Complete the wizard

**Verification:** The shared folder `k8s` appears in the Shared Folder list. The path `/volume1/k8s` exists on the NAS.

### 3. Set NFS Permissions

1. In **Control Panel** > **Shared Folder**, select the `k8s` folder
2. Click **Edit**
3. Go to the **NFS Permissions** tab
4. Click **Create**
5. Fill in the NFS rule:

| Field | Value |
|-------|-------|
| **Hostname or IP** | `192.168.0.0/24` |
| **Privilege** | Read/Write |
| **Squash** | Map all users to admin |
| **Security** | sys |
| **Enable asynchronous** | Yes |
| **Allow connections from non-privileged ports** | Yes |
| **Allow users to access mounted subfolders** | Yes |

6. Click **OK**, then **OK** again to close the edit dialog

**Verification:** The NFS rule appears in the NFS Permissions list, showing the subnet `192.168.0.0/24` with Read/Write privilege.

> **Warning:** The squash setting **"Map all users to admin"** is required. Without it, Kubernetes pods will get "Permission denied" errors because they run as UIDs that don't exist on the Synology. This setting gives all NFS clients from the specified subnet admin-equivalent access to this specific shared folder only.

### 4. Verify NFS Export is Visible

From your local machine (or any machine on the same subnet), run:

```bash
showmount -e 192.168.0.102
```

You should see `/volume1/k8s` in the export list:

```
Export list for 192.168.0.102:
/volume1/k8s  192.168.0.0/24
/volume1/Plex (existing export)
```

If `showmount` is not available, you can verify from DSM: go to **Control Panel** > **File Services** > **NFS** tab and check that the service is running.

### 5. Add to Hyper Backup

The NFS share must be backed up to protect Kubernetes data (sketchpad files, OAuth state).

1. Open the **Hyper Backup** application
2. Edit your existing backup task (or create a new one if you don't have one)
3. In the **Folder** selection step, add `/volume1/k8s` to the backup
4. Save the backup task

**Verification:** The `k8s` folder appears in the backup task's folder selection. Run a manual backup to confirm it completes successfully.

## Installing the NFS Provisioner on Kubernetes

After the NFS share is configured, install the `nfs-subdir-external-provisioner` on the cluster. This creates a StorageClass called `nfs-client` that automatically provisions PVs backed by subdirectories on the NFS share.

```bash
# Add the Helm repo
helm repo add nfs-subdir-external-provisioner \
  https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm repo update

# Install the provisioner
helm install nfs-subdir-external-provisioner \
  nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --namespace sketchpad \
  --set nfs.server=192.168.0.102 \
  --set nfs.path=/volume1/k8s \
  --set storageClass.name=nfs-client \
  --set storageClass.defaultClass=false \
  --set storageClass.reclaimPolicy=Retain \
  --set storageClass.archiveOnDelete=false \
  --set storageClass.accessModes=ReadWriteOnce
```

**Verification:**

```bash
# Check the provisioner pod is running
kubectl get pods -n sketchpad -l app=nfs-subdir-external-provisioner

# Check the StorageClass was created
kubectl get storageclass nfs-client
```

## Troubleshooting

### "Permission denied" when pods write to NFS

Check the NFS permission squash setting. It must be **"Map all users to admin"**, not "No mapping" or "Map root to admin."

### PVC stays in Pending state

1. Check the provisioner pod is running: `kubectl get pods -n sketchpad`
2. Check provisioner logs: `kubectl logs -n sketchpad -l app=nfs-subdir-external-provisioner`
3. Verify the NFS share is reachable: `showmount -e 192.168.0.102`

### "mount.nfs: access denied"

The NFS permission rule doesn't include the cluster node IPs. Verify the hostname/IP field is `192.168.0.0/24` (or matches your cluster subnet).
