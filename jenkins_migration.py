import subprocess
import sys
import os

# Define variables for namespaces, pod names, contexts, and Azure tenant IDs
SOURCE_CONTEXT = "Argocd_Cluster"
SOURCE_NAMESPACE = "jenkins"
SOURCE_POD_NAME = "jenkins-76db9f6ccb-pjt7b"
TARGET_CONTEXT = "jenkinsMigration_cluster"
TARGET_NAMESPACE = "jenkins"
TARGET_POD_NAME = "jenkins-76db9f6ccb-pgdls"
SOURCE_TENANT_ID = "your-source-tenant-id"
TARGET_TENANT_ID = "your-target-tenant-id"
SWITCH_TENANT = os.getenv('SWITCH_TENANT', 'false').lower() == 'true'

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while executing command: {e.cmd}")
        print(f"Return code: {e.returncode}")
        print(f"Output: {e.output}")
        sys.exit(1)

def switch_azure_ad(tenant_id):
    print(f"Switching to Azure Active Directory with tenant ID {tenant_id}...")
    run_command(f"az login --tenant {tenant_id} --output none")

def switch_kube_context(context):
    print(f"Switching to {context} cluster context...")
    run_command(f"kubectl config use-context {context}")

def backup_jenkins_data(namespace, pod, backup_path, config_backup_path):
    print(f"Backing up Jenkins data from {namespace} namespace...")
    run_command(f"kubectl -n {namespace} exec {pod} -- tar -czvf /tmp/jenkins-backup.tar.gz {backup_path}")
    try:
        run_command(f"kubectl -n {namespace} exec {pod} -- tar -czvf /tmp/jenkins-config-backup.tar.gz {config_backup_path}")
    except subprocess.CalledProcessError:
        print(f"Directory {config_backup_path} does not exist. Skipping config backup.")

def copy_backups_to_local(namespace, pod):
    print("Copying backups to local machine... This might take a while.")
    run_command(f"kubectl -n {namespace} cp {pod}:/tmp/jenkins-backup.tar.gz ./jenkins-backup.tar.gz")
    try:
        run_command(f"kubectl -n {namespace} cp {pod}:/tmp/jenkins-config-backup.tar.gz ./jenkins-config-backup.tar.gz")
    except subprocess.CalledProcessError:
        print("Config backup not found on the pod. Skipping config backup copy.")

def copy_backups_to_pod(namespace, pod):
    print(f"Copying backups to new Jenkins pod in {namespace} namespace... This might take a while.")
    run_command(f"kubectl -n {namespace} cp ./jenkins-backup.tar.gz {pod}:/tmp/jenkins-backup.tar.gz")
    try:
        run_command(f"kubectl -n {namespace} cp ./jenkins-config-backup.tar.gz {pod}:/tmp/jenkins-config-backup.tar.gz")
    except subprocess.CalledProcessError:
        print("Config backup not found locally. Skipping config backup copy to pod.")

def restore_jenkins_data(namespace, pod, backup_path, config_backup_path):
    print(f"Restoring backups in {namespace} namespace... This might take a while.")
    run_command(f"kubectl -n {namespace} exec {pod} -- tar -xzvf /tmp/jenkins-backup.tar.gz -C {backup_path}")
    try:
        run_command(f"kubectl -n {namespace} exec {pod} -- tar -xzvf /tmp/jenkins-config-backup.tar.gz -C {config_backup_path}")
    except subprocess.CalledProcessError:
        print(f"Config backup not found on the pod. Skipping config restore.")

def main():
    if SWITCH_TENANT:
        switch_azure_ad(SOURCE_TENANT_ID)

    switch_kube_context(SOURCE_CONTEXT)
    backup_jenkins_data(SOURCE_NAMESPACE, SOURCE_POD_NAME, "/var/jenkins_home", "/var/jenkins_config")
    copy_backups_to_local(SOURCE_NAMESPACE, SOURCE_POD_NAME)

    if SWITCH_TENANT:
        switch_azure_ad(TARGET_TENANT_ID)

    switch_kube_context(TARGET_CONTEXT)
    copy_backups_to_pod(TARGET_NAMESPACE, TARGET_POD_NAME)
    restore_jenkins_data(TARGET_NAMESPACE, TARGET_POD_NAME, "/var/jenkins_home", "/var/jenkins_config")

    print("Migration completed successfully.")

if __name__ == "__main__":
    main()