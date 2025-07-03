import os
import requests
import pydo
import argparse

# Function to load API token
def get_api_token(env_var, token_file):
    # Try to get the token from an environment variable
    token = os.getenv(env_var)
    if token:
        return token
    
    # Try to read the token from a file
    token_file = os.path.expanduser(token_file)
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            return f.read().strip()
    
    raise ValueError(f"DigitalOcean API token not found. Set {env_var} or store it in {token_file}")


def list_droplets_by_tag(client: pydo.Client, tag_name: str, per_page: int = 50) -> list[dict]:
    page = 1
    all_droplets = []

    while True:
        response = client.droplets.list(per_page=per_page, page=page, tag_name=tag_name)
        droplets = response.get("droplets", [])
        if not droplets:
            break

        all_droplets.extend(droplets)

        if len(droplets) < per_page:
            break
        page += 1

    return all_droplets


if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="List all droplets with a given tag")
    parser.add_argument("--tag", default="ephemeral")
    parser.add_argument("--environment_variable_for_token", default="DIGITALOCEAN_API_TOKEN", required=False)
    parser.add_argument("--filename_for_token", default=".digital_ocean_token", required=False)

    args = parser.parse_args()
    # Load API token
    token = get_api_token(args.environment_variable_for_token, args.filename_for_token)

    # Initialize the DigitalOcean API client
    client = pydo.Client(token=token)

    droplets = list_droplets_by_tag(client, args.tag)

    for droplet in droplets:
        name = droplet["name"]
        droplet_id = droplet["id"]
        ipv4s = [net["ip_address"] for net in droplet["networks"]["v4"]]
        tags = droplet["tags"]

        print(f"{name} (ID: {droplet_id}) - IPv4: {', '.join(ipv4s)}, Tags: {', '.join(tags)}")

