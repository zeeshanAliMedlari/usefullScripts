# Define variables for namespaces, pod names, and contexts
$SOURCE_CONTEXT = "source-context"
$SOURCE_NAMESPACE = "jenkins"
$TARGET_CONTEXT = "target-context"
$TARGET_NAMESPACE = "ccs"
$POD_NAME = "jenkins-0"

function Switch-KubeContext {
    param (
        [string]$context
    )
    Write-Output "Switching to $context cluster context..."
    & kubectl config use-context $context
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to switch to $context cluster context."
        exit 1
    }
}

function Backup-JenkinsData {
    param (
        [string]$namespace,
        [string]$pod,
        [string]$backupPath,
        [string]$configBackupPath
    )
    Write-Output "Backing up Jenkins data from $namespace namespace..."
    & kubectl -n $namespace exec $pod -- tar -czvf /tmp/jenkins-backup.tar.gz $backupPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to backup Jenkins data from $backupPath."
        exit 1
    }
    & kubectl -n $namespace exec $pod -- tar -czvf /tmp/jenkins-config-backup.tar.gz $configBackupPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to backup Jenkins configuration from $configBackupPath."
        exit 1
    }
}

function Copy-BackupsToLocal {
    param (
        [string]$namespace,
        [string]$pod
    )
    Write-Output "Copying backups to local machine..."
    & kubectl -n $namespace cp $pod:/tmp/jenkins-backup.tar.gz ./jenkins-backup.tar.gz
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to copy Jenkins data backup to local machine."
        exit 1
    }
    & kubectl -n $namespace cp $pod:/tmp/jenkins-config-backup.tar.gz ./jenkins-config-backup.tar.gz
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to copy Jenkins configuration backup to local machine."
        exit 1
    }
}

function Copy-BackupsToPod {
    param (
        [string]$namespace,
        [string]$pod
    )
    Write-Output "Copying backups to new Jenkins pod in $namespace namespace..."
    & kubectl -n $namespace cp ./jenkins-backup.tar.gz $pod:/tmp/jenkins-backup.tar.gz
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to copy Jenkins data backup to pod."
        exit 1
    }
    & kubectl -n $namespace cp ./jenkins-config-backup.tar.gz $pod:/tmp/jenkins-config-backup.tar.gz
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to copy Jenkins configuration backup to pod."
        exit 1
    }
}

function Restore-JenkinsData {
    param (
        [string]$namespace,
        [string]$pod,
        [string]$backupPath,
        [string]$configBackupPath
    )
    Write-Output "Restoring backups in $namespace namespace..."
    & kubectl -n $namespace exec $pod -- tar -xzvf /tmp/jenkins-backup.tar.gz -C $backupPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to restore Jenkins data backup to $backupPath."
        exit 1
    }
    & kubectl -n $namespace exec $pod -- tar -xzvf /tmp/jenkins-config-backup.tar.gz -C $configBackupPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to restore Jenkins configuration backup to $configBackupPath."
        exit 1
    }
}

# Switch to Source cluster context
Switch-KubeContext -context $SOURCE_CONTEXT

# Backup old Jenkins data in Source cluster
Backup-JenkinsData -namespace $SOURCE_NAMESPACE -pod $POD_NAME -backupPath "/var/jenkins_home" -configBackupPath "/var/jenkins_config"

# Copy backups to local machine
Copy-BackupsToLocal -namespace $SOURCE_NAMESPACE -pod $POD_NAME

# Switch to Target cluster context
Switch-KubeContext -context $TARGET_CONTEXT

# Copy backups to new Jenkins pod in Target cluster
Copy-BackupsToPod -namespace $TARGET_NAMESPACE -pod $POD_NAME

# Restore backups in new Jenkins pod in Target cluster
Restore-JenkinsData -namespace $TARGET_NAMESPACE -pod $POD_NAME -backupPath "/var/jenkins_home" -configBackupPath "/var/jenkins_config"

Write-Output "Migration completed successfully."
