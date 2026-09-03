#! /usr/local/python-venvs/open-tmux/bin/python3

import subprocess
import yaml
import json
import inquirer
import os
import re
import getpass
import signal
import sys

# Define function

def natural_sort_key(value):
    parts = re.split(r'(\d+)', value)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def handle_sigint(signum, frame):
    print('\nInterrupted by user. Exiting.')
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

def open_tmux_session(filepath, session_name):
    
    # Check if tmux session already exists
    session_check = subprocess.run(f"tmux has-session -t {session_name}", shell=True, capture_output=True)
    session_exists = session_check.returncode == 0
    
    if session_exists:
        session_choice = [inquirer.List("session_action", message=f"A tmux session '{session_name}' already exists. What would you like to do?", choices=["Attach to existing","Create new session", "Cancel"])]
        try:
            action = inquirer.prompt(session_choice)
        except (KeyboardInterrupt, EOFError):
            print('\nInterrupted by user. Exiting.')
            quit(1)
        if not action or not action.get('session_action'):
            print('Cancelled by user. Exiting.')
            quit(1)
        
        chosen_action = action['session_action']
        if chosen_action == "Attach to existing":
            os.system(f"tmux attach-session -t {session_name}")
            return
        elif chosen_action == "Cancel":
            print('Cancelled by user. Exiting.')
            quit(1)
        # else: Create new session, continue to creation below
    
    # Load the inventory file
    with open(filepath, 'r') as file:
        inventory = yaml.safe_load(file)

    # Create a new tmux session
    os.system(f"tmux new-session -d -s {session_name}")

    # Iterate over each node in the inventory and create a new window for each
    for node in sorted(inventory.keys(), key=natural_sort_key):
        details = inventory[node]
        hostname = details['hostname']
        username = details['username']
        password = details['password']
        os.system(f"tmux new-window -t {session_name} -n {node} 'sshpass -p {password} ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {username}@{hostname}'")

    # Attach to the tmux session
    os.system(f"tmux attach-session -t {session_name}")


# Navigate to root directory before running command so the labPath var is complete
command = "clab inspect --all -w -f json"
labs = subprocess.run(command, shell=True, capture_output=True, text=True)

# Parse the JSON
try:
    labs = json.loads(labs.stdout)
except json.decoder.JSONDecodeError:
    print("Error decoding containerlab output, are any containers running?")
    quit(1)

current_user = getpass.getuser()
user_labs = {
    lab_name: entries
    for lab_name, entries in labs.items()
    if entries and entries[0].get("owner") == current_user
}

if not user_labs:
    if not labs:
        print("No running labs found. Start a lab and try again.")
    else:
        print(f"No running labs found for current user '{current_user}'.")
    quit(1)

# Only one lab, no need for a list of options
if len(user_labs) == 1:
    print("One running lab detected")
    first_key = list(user_labs.keys())[0]
    first_entry = user_labs[first_key][0]
    onelabquestion = [inquirer.Confirm("continue", message=f"Open lab '{first_key}' owned by {first_entry['owner']}?", default=True)]
    try:
        answers = inquirer.prompt(onelabquestion)
    except (KeyboardInterrupt, EOFError):
        print('\nInterrupted by user. Exiting.')
        quit(1)
    if not answers or not answers.get('continue'):
        print('Cancelled by user. Exiting.')
        quit(1)
    # Strip the ending file as we need to find the actual lab files
    directory_path = os.path.dirname(first_entry['absLabPath'])
    # Follow the CLAB-generated artifacts to get the inventory file
    inventory_path = directory_path+f"/clab-{first_key}/nornir-simple-inventory.yml"
    open_tmux_session(inventory_path, first_key)
elif len(user_labs) > 1:
    print("Multiple running labs detected")
    lablist = []
    lab_map = {}
    for lab_name, lab_entries in user_labs.items():
        first_entry = lab_entries[0]
        label = f"Owner: {first_entry['owner']} | Lab: {lab_name} | {len(lab_entries)} nodes"
        lablist.append(label)
        lab_map[label] = lab_name
    
    questions = [inquirer.List("Lab Selection", message="Which lab do you wish to open?", choices=lablist)]
    try:
        answers = inquirer.prompt(questions)
    except (KeyboardInterrupt, EOFError):
        print('\nInterrupted by user. Exiting.')
        quit(1)
    if not answers or not answers.get('Lab Selection'):
        print('Cancelled by user. Exiting.')
        quit(1)
    selected_label = answers["Lab Selection"]
    selected_lab = lab_map[selected_label]
    selected_entry = user_labs[selected_lab][0]
    
    # Strip the ending file as we need to find the actual lab files
    directory_path = os.path.dirname(selected_entry['absLabPath'])
    # Follow the CLAB-generated artifacts to get the inventory file
    inventory_path = directory_path + f"/clab-{selected_lab}/nornir-simple-inventory.yml"
    open_tmux_session(inventory_path, selected_lab)
