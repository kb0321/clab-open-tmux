import subprocess
import yaml
import json
import inquirer
import os

# Define function
def open_tmux_session(filepath, session_name):
    
    # Load the inventory file
    with open(filepath, 'r') as file:
        inventory = yaml.safe_load(file)

    # Create a new tmux session
    os.system(f"tmux new-session -d -s {session_name}")

    # Iterate over each node in the inventory and create a new window for each
    for node, details in inventory.items():
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



# Only one lab, no need for a list of options
if len(labs)==1:
    print("One running lab detected")
    first_key = list(labs.keys())[0]
    first_entry = labs[first_key][0]
    onelabquestion = [inquirer.Confirm("continue", message=f"Should I continue to open for lab \"{first_key}\" (Owner: {first_entry['owner']}, {len(labs[first_key])} containers, File: {first_entry['absLabPath']})?", default=True)]
    answers = inquirer.prompt(onelabquestion)
    # Exit if no is pressed
    if not answers['continue']:
        quit()
    # Strip the ending file as we need to find the actual lab files
    directory_path = os.path.dirname(first_entry['absLabPath'])
    # Follow the CLAB-generated artifacts to get the inventory file
    inventory_path = directory_path+f"/clab-{first_key}/nornir-simple-inventory.yml"
    open_tmux_session(inventory_path, first_key)
elif len(labs) > 1:
    print("Multiple running labs detected")
    lablist = []
    for lab_name, lab_entries in labs.items():
        first_entry = lab_entries[0]
        lablist.append(f"{lab_name} (Owner: {first_entry['owner']}, {len(lab_entries)} containers, File: {first_entry['absLabPath']})")
    
    questions = [inquirer.List("Lab Selection", message="Which lab do you wish to open?", choices=lablist)]
    answers = inquirer.prompt(questions)
    
    # Extract the selected lab name
    selected_lab = answers['Lab Selection'].split(' ')[0]
    selected_entry = labs[selected_lab][0]
    
    # Strip the ending file as we need to find the actual lab files
    directory_path = os.path.dirname(selected_entry['absLabPath'])
    # Follow the CLAB-generated artifacts to get the inventory file
    inventory_path = directory_path + f"/clab-{selected_lab}/nornir-simple-inventory.yml"
    open_tmux_session(inventory_path, selected_lab)
