import sys
import getpass
from proxmoxer import ProxmoxAPI
import urllib3

# Disable SSL warnings for this script
urllib3.disable_warnings()

def main():
    print("--- Proxmox Connection Verifier ---")
    host = input("Proxmox Host (e.g., 192.168.1.10 or https://192.168.1.10): ").strip()
    
    # Simulate the cleanup logic we added to the integration
    clean_host = host.replace("https://", "").replace("http://", "").rstrip("/")
    print(f"DEBUG: Connecting to cleaned host: '{clean_host}'")
    
    user = input("Username (e.g., root): ").strip()
    realm = input("Realm (e.g., pam, pve): ").strip()
    full_user = f"{user}@{realm}"
    
    password = getpass.getpass("Password: ")
    
    print("\nAttempting connection...")
    
    try:
        proxmox = ProxmoxAPI(
            clean_host,
            user=full_user,
            password=password,
            verify_ssl=False,
            port=8006
        )
        
        # Test 1: Get Version
        version = proxmox.version.get()
        print(f"\n✅ SUCCESS! Connected to Proxmox VE version: {version['version']}")
        
        # Test 2: Get Nodes
        print("\nFetching Nodes...")
        nodes = proxmox.nodes.get()
        for node in nodes:
            print(f"- Node: {node['node']} (Status: {node['status']})")
            
            # Test 3: Get VMs for this node
            print(f"  Fetching VMs for {node['node']}...")
            vms = proxmox.nodes(node['node']).qemu.get()
            for vm in vms:
                print(f"  -- VM: {vm['name']} (ID: {vm['vmid']}, Status: {vm['status']})")
                
            # Test 4: Get LXCs for this node
            print(f"  Fetching LXCs for {node['node']}...")
            lxcs = proxmox.nodes(node['node']).lxc.get()
            for lxc in lxcs:
                 print(f"  -- LXC: {lxc['name']} (ID: {lxc['vmid']}, Status: {lxc['status']})")
                 
    except Exception as e:
        print(f"\n❌ FAILED to connect!")
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check if the IP is correct and reachable (ping it).")
        print("2. Check credentials.")
        print("3. Ensure user has permissions.")

if __name__ == "__main__":
    main()
