import subprocess
import sys

def run_command(command):
    """Run a system command and return the output."""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(e.stderr)
        sys.exit(1)

def git_status():
    """Check the status of the git repository."""
    print("Checking git status...")
    status = run_command("git status --porcelain")
    if status:
        print("There are changes to commit.")
    else:
        print("No changes detected.")
    return status

def git_add():
    """Add all changes to the staging area."""
    print("Adding changes to staging area...")
    run_command("git add .")

def git_commit(commit_message):
    """Commit the changes with a given message."""
    print(f"Committing changes with message: '{commit_message}'")
    run_command(f"git commit -m '{commit_message}'")

def git_push():
    """Push the committed changes to the remote repository."""
    print("Pushing changes to the remote repository...")
    run_command("git push origin main")

if __name__ == "__main__":
    # Check for changes
    if not git_status():
        print("No changes to commit. Exiting.")
        sys.exit(0)

    # Get commit message
    commit_message = input("Enter the commit message: ")

    # Add, commit, and push changes
    git_add()
    git_commit(commit_message)
    git_push()

    print("Prepare and deploy steps completed successfully.")

