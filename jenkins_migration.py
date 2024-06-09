import subprocess
import sys

SOURCE_CONTEXT = "Argocd_Cluster"
SOURCE_NAMESPACE = "jenkins"
TARGET_CONTEXT = "target-context"
TARGET_NAMESPACE = "ccs"
POD_NAME = "jenkins-0"

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while executing command: {e.cmd}")
        print(f"Return code: {e.returncode}")
        print(f"Output: {e.output}")
        sys.exit(1)

def switch_kube_context(context):
    print(f"Switching to {context} cluster context...")
    run_command(f"kubectl config use-context {context}")

def backup_jenkins_data(namespace, pod, backup_path, config_backup_path):
    print(f"Backing up Jenkins data from {namespace} namespace...")
    run_command(f"kubectl -n {namespace} exec {pod} -- tar -czvf /tmp/jenkins-backup.tar.gz {backup_path}")
    run_command(f"kubectl -n {namespace} exec {pod} -- tar -czvf /tmp/jenkins-config-backup.tar.gz {config_backup_path}")

def copy_backups_to_local(namespace, pod):
    print("Copying backups to local machine...")
    run_command(f"kubectl -n {namespace} cp {pod}:/tmp/jenkins-backup.tar.gz ./jenkins-backup.tar.gz")
    run_command(f"kubectl -n {namespace} cp {pod}:/tmp/jenkins-config-backup.tar.gz ./jenkins-config-backup.tar.gz")

def copy_backups_to_pod(namespace, pod):
    print(f"Copying backups to new Jenkins pod in {namespace} namespace...")
    run_command(f"kubectl -n {namespace} cp ./jenkins-backup.tar.gz {pod}:/tmp/jenkins-backup.tar.gz")
    run_command(f"kubectl -n {namespace} cp ./jenkins-config-backup.tar.gz {pod}:/tmp/jenkins-config-backup.tar.gz")

def restore_jenkins_data(namespace, pod, backup_path, config_backup_path):
    print(f"Restoring backups in {namespace} namespace...")
    run_command(f"kubectl -n {namespace} exec {pod} -- tar -xzvf /tmp/jenkins-backup.tar.gz -C {backup_path}")
    run_command(f"kubectl -n {namespace} exec {pod} -- tar -xzvf /tmp/jenkins-config-backup.tar.gz -C {config_backup_path}")

def main():
    switch_kube_context(SOURCE_CONTEXT)
    backup_jenkins_data(SOURCE_NAMESPACE, POD_NAME, "/var/jenkins_home", "/var/jenkins_config")
    copy_backups_to_local(SOURCE_NAMESPACE, POD_NAME)
    switch_kube_context(TARGET_CONTEXT)
    copy_backups_to_pod(TARGET_NAMESPACE, POD_NAME)
    restore_jenkins_data(TARGET_NAMESPACE, POD_NAME, "/var/jenkins_home", "/var/jenkins_config")
    print("Migration completed successfully.")

if __name__ == "__main__":
    main()
