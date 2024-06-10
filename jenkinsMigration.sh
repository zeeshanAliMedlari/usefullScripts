#!/bin/bash

# Define variables for namespaces, pod names, and contexts
SOURCE_CONTEXT="source-context"
SOURCE_NAMESPACE="jenkins"
TARGET_CONTEXT="target-context"
TARGET_NAMESPACE="ccs"
POD_NAME="jenkins-0"

# Function to switch Kubernetes context
switch_kube_context() {
    local context=$1
    echo "Switching to $context cluster context..."
    if ! kubectl config use-context "$context"; then
        echo "Failed to switch to $context cluster context."
        exit 1
    fi
}

# Function to backup Jenkins data
backup_jenkins_data() {
    local namespace=$1
    local pod=$2
    local backup_path=$3
    local config_backup_path=$4

    echo "Backing up Jenkins data from $namespace namespace..."
    if ! kubectl -n "$namespace" exec "$pod" -- tar -czvf /tmp/jenkins-backup.tar.gz "$backup_path"; then
        echo "Failed to backup Jenkins data from $backup_path."
        exit 1
    fi
    if ! kubectl -n "$namespace" exec "$pod" -- tar -czvf /tmp/jenkins-config-backup.tar.gz "$config_backup_path"; then
        echo "Failed to backup Jenkins configuration from $config_backup_path."
        exit 1
    fi
}

# Function to copy backups to local machine
copy_backups_to_local() {
    local namespace=$1
    local pod=$2

    echo "Copying backups to local machine..."
    if ! kubectl -n "$namespace" cp "$pod":/tmp/jenkins-backup.tar.gz ./jenkins-backup.tar.gz; then
        echo "Failed to copy Jenkins data backup to local machine."
        exit 1
    fi
    if ! kubectl -n "$namespace" cp "$pod":/tmp/jenkins-config-backup.tar.gz ./jenkins-config-backup.tar.gz; then
        echo "Failed to copy Jenkins configuration backup to local machine."
        exit 1
    fi
}

# Function to copy backups to the pod in the target namespace
copy_backups_to_pod() {
    local namespace=$1
    local pod=$2

    echo "Copying backups to new Jenkins pod in $namespace namespace..."
    if ! kubectl -n "$namespace" cp ./jenkins-backup.tar.gz "$pod":/tmp/jenkins-backup.tar.gz; then
        echo "Failed to copy Jenkins data backup to pod."
        exit 1
    fi
    if ! kubectl -n "$namespace" cp ./jenkins-config-backup.tar.gz "$pod":/tmp/jenkins-config-backup.tar.gz; then
        echo "Failed to copy Jenkins configuration backup to pod."
        exit 1
    fi
}

# Function to restore Jenkins data
restore_jenkins_data() {
    local namespace=$1
    local pod=$2
    local backup_path=$3
    local config_backup_path=$4

    echo "Restoring backups in $namespace namespace..."
    if ! kubectl -n "$namespace" exec "$pod" -- tar -xzvf /tmp/jenkins-backup.tar.gz -C "$backup_path"; then
        echo "Failed to restore Jenkins data backup to $backup_path."
        exit 1
    fi
    if ! kubectl -n "$namespace" exec "$pod" -- tar -xzvf /tmp/jenkins-config-backup.tar.gz -C "$config_backup_path"; then
        echo "Failed to restore Jenkins configuration backup to $config_backup_path."
        exit 1
    fi
}

# Main script execution
switch_kube_context "$SOURCE_CONTEXT"
backup_jenkins_data "$SOURCE_NAMESPACE" "$POD_NAME" "/var/jenkins_home" "/var/jenkins_config"
copy_backups_to_local "$SOURCE_NAMESPACE" "$POD_NAME"
switch_kube_context "$TARGET_CONTEXT"
copy_backups_to_pod "$TARGET_NAMESPACE" "$POD_NAME"
restore_jenkins_data "$TARGET_NAMESPACE" "$POD_NAME" "/var/jenkins_home" "/var/jenkins_config"
echo "Migration completed successfully."
