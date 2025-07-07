import json
import secrets
import fire

from app.auth import (
    get_api_key,
    insert_api_keys,
    insert_api_keys_integrations,
    deactivate_api_keys,
    get_current_integrations,
)


def generate_api_key(prefix="sk", length=48):
    token = secrets.token_urlsafe(length)[:length]
    return f"{prefix}-{token}"


class KeyManager:

    def create(
        self,
        file: str = None,
        user: str = None,
        integrations: str = None
    ):
        """
        Create one or more API keys.

        Accepts:
        - A single user via --user
        - OR a file of sciper,email pairs (via --file)

        Args:
            file: Path to a file with sciper,email pairs (one per line).
            user: Comma-separated sciper and email of a single user (used only if file is not provided).
            integrations: Comma-separated integrations (optional, prompts if missing).
        """

        # Read users
        users = []
        if file:
            try:
                with open(file, "r") as f:
                    lines = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"Error: File not found: {file}")
                return

            for line in lines:
                if "," in line:
                    sciper, email = [x.strip() for x in line.split(sep=",", maxsplit=1)]
                    users.append({'sciper': sciper, 'email': email})
                else:
                    print(f"Invalid line skipped: '{line}'")
        else:
            if user:
                sciper, email = [x.strip() for x in user.split(",", maxsplit=1)]

                if not sciper or not email:
                    print(f"Invalid sciper {sciper} or email {email}. No changes made in the database.")
            else:
                sciper = input("Enter user sciper: ").strip()
                if not sciper:
                    print("No sciper read. No changes made in the database.")
                    return

                email = input("Enter user email: ").strip()
                if not email:
                    print("No email read. No changes made in the database.")
                    return

            users.append({'sciper': sciper, 'email': email})

        if not users:
            print("No users read. No changes made in the database.")
            return

        # Read integrations
        current_integrations = get_current_integrations()

        if not integrations:
            print(f"Current integrations: {current_integrations}")
            integrations = input("Enter comma-separated integration names (or * for all): ").strip()

        if not integrations:
            print("No integrations read. No changes made in the database.")
            return

        integrations = [integration.strip() for integration in integrations.split(",")]

        if '*' in integrations:
            integrations = ['*']

        # Create keys
        api_keys_records = []
        for user in users:
            api_key = get_api_key(user['sciper'], user['email'])

            if not api_key:
                api_key = generate_api_key()

            api_keys_records.append({
                'api_key': api_key,
                'sciper': user['sciper'],
                'email': user['email'],
            })

        # Insert them in the database
        insert_api_keys(api_keys_records)

        api_keys_integrations_records = []
        for api_keys_record in api_keys_records:
            for integration in integrations:
                api_keys_integrations_records.append({
                    'api_key': api_keys_record['api_key'],
                    'integration': integration,
                })

        insert_api_keys_integrations(api_keys_integrations_records)

        print("Successfully created or retrieved the following API keys:")
        print(json.dumps(api_keys_records, indent=2))
        print("and granted them access to the following integrations:")
        print(integrations)

    def deactivate(
        self,
        sciper_file: str = None,
        email_file: str = None,
        api_key: str = None,
        sciper: str = None,
        email: str = None
    ):
        """
        Deactivates keys by value, sciper or email.

        Accepts:
        - A comma-separated list of api_keys (via --api-key)
        - OR a comma-separated list of scipers (via --sciper)
        - OR a comma-separated list of emails (via --email)
        - OR a file of sciper numbers (via --sciper_file)
        - OR a file of emails (via --email_file)

        Args:
            sciper_file: Path to a file of sciper numbers (optional).
            email_file: Path to a file of emails (optional).
            sciper: Comma-separated list of scipers (optional).
            email: Comma-separated list of emails (optional).
            api_key: Comma-separated list of api_keys (optional).
        """

        targets = {
            "api_keys": [],
            "scipers": [],
            "emails": []
        }

        # Parse files
        if sciper_file:
            try:
                with open(sciper_file, "r") as f:
                    targets["scipers"].extend(
                        [line.strip() for line in f if line.strip()]
                    )
            except FileNotFoundError:
                print(f"Error: Sciper file not found: {sciper_file}")
                return

        if email_file:
            try:
                with open(email_file, "r") as f:
                    targets["emails"].extend(
                        [line.strip() for line in f if line.strip()]
                    )
            except FileNotFoundError:
                print(f"Error: Email file not found: {email_file}")
                return

        # Parse comma-separated arguments
        if sciper:
            targets["scipers"].extend([s.strip() for s in sciper.split(",") if s.strip()])

        if email:
            targets["emails"].extend([e.strip() for e in email.split(",") if e.strip()])

        if api_key:
            targets["api_keys"].extend([k.strip() for k in api_key.split(",") if k.strip()])

        if not any(targets.values()):
            print("No valid input provided. Nothing was deactivated in the database.")
            return

        # Call backend logic
        deactivate_api_keys({
            'api_key': targets["api_keys"],
            'sciper': targets["scipers"],
            'email': targets["emails"],
        })

        print("Successfully deactivated API keys (whenever present in database)")


if __name__ == "__main__":
    fire.Fire(KeyManager)
