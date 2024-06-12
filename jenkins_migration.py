import subprocess
import sys
import os

# Define variables for namespaces, pod names, contexts, and Azure tenant IDs
SOURCE_CONTEXT = "Argocd_Cluster"
SOURCE_NAMESPACE = "jenkins"
TARGET_CONTEXT = "jenkinsMigration_cluster"
TARGET_NAMESPACE = "jenkins"
POD_NAME = "jenkins-0"
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

def backup_jenkins_data(namespace, pod, backup_path):
    print(f"Backing up Jenkins data from {namespace} namespace...")
    run_command(f"kubectl -n {namespace} exec {pod} -- tar -czvf /tmp/jenkins-backup.tar.gz {backup_path}")

def copy_backups_to_local(namespace, pod):
    print("Copying backups to local machine... This might take a while.")
    run_command(f"kubectl -n {namespace} cp {pod}:/tmp/jenkins-backup.tar.gz ./jenkins-backup.tar.gz")

def copy_backups_to_pod(namespace, pod):
    print(f"Copying backups to new Jenkins pod in {namespace} namespace... This might take a while.")
    run_command(f"kubectl -n {namespace} cp ./jenkins-backup.tar.gz {pod}:/tmp/jenkins-backup.tar.gz")

def restore_jenkins_data(namespace, pod, backup_path):
    print(f"Restoring backups in {namespace} namespace... This might take a while.")
    run_command(f"kubectl -n {namespace} exec {pod} -- tar -xzvf /tmp/jenkins-backup.tar.gz --strip-components=1 -C {backup_path}")

def main():
    if SWITCH_TENANT:
        switch_azure_ad(SOURCE_TENANT_ID)

    switch_kube_context(SOURCE_CONTEXT)
    backup_jenkins_data(SOURCE_NAMESPACE, POD_NAME, "/var/jenkins_home")
    copy_backups_to_local(SOURCE_NAMESPACE, POD_NAME)

    if SWITCH_TENANT:
        switch_azure_ad(TARGET_TENANT_ID)

    switch_kube_context(TARGET_CONTEXT)
    copy_backups_to_pod(TARGET_NAMESPACE, POD_NAME)
    restore_jenkins_data(TARGET_NAMESPACE, POD_NAME, "/var/jenkins_home")

    print("Migration completed successfully.")

if __name__ == "__main__":
    main()