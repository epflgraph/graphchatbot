"""
This module contains the tool to retrieve the organizational chart from EPFL
"""
from datetime import datetime

import json

import ldap

from app.config import config


def get_ldap_attribute(entry, attribute, index=0):
    binary_str_list = entry.get(attribute, [b''])

    if index < len(binary_str_list):
        binary_str = binary_str_list[index]
    else:
        binary_str = b''

    return binary_str.decode('utf-8')


def fetch_from_ldap():
    # Initialize LDAP connection
    host = config.get('ldap', {}).get('host')
    port = config.get('ldap', {}).get('port')
    ldap_connection = ldap.initialize(f'ldap://{host}:{port}')

    # Define base dn
    base_dn = 'o=epfl, c=ch'

    # Set timeout of 5 seconds both for establishing the connection and for the request
    ldap_connection.set_option(ldap.OPT_NETWORK_TIMEOUT, 3)
    ldap_connection.set_option(ldap.OPT_TIMEOUT, 3)

    # Search filter: Presidency plus VPs plus AVPs
    personnel_filter = '(organizationalStatus=Personnel)'
    pres_filter = '(ou=PRES)'
    vpa_filter = '(| (ou=VPA-VP-GE) (ou=AVP-E-GE) (ou=AVP-R-GE) (ou=AVP-CP-GE) (ou=AVP-DLE-GE) (ou=VPA*) )'
    vpf_filter = '(| (ou=VPF-VP-GE) (ou=VPF*) )'
    vph_filter = '(| (ou=VPH-VP-GE) (ou=VPH*) )'
    vpi_filter = '(| (ou=VPI-VP-GE) (ou=VPI*) )'
    vpo_filter = '(| (ou=DVPO-GE) (ou=VPO*) (ou=DVPO*) )'
    vps_filter = '(| (ou=VPS-VP-GE) (ou=VPS*) )'

    search_filter = f'(& {personnel_filter} (| {pres_filter} {vpa_filter} {vpf_filter} {vph_filter} {vpi_filter} {vpo_filter} {vps_filter} ))'
    attributes = ['displayName', 'ou', 'title', 'mail', 'uniqueIdentifier']

    # Fetch data
    results = ldap_connection.search_s(base_dn, ldap.SCOPE_SUBTREE, search_filter, attributes)

    # Parse the results
    orgchart = []
    for dn, entry in results:
        person = {
            'name': get_ldap_attribute(entry, attribute='displayName'),
            'unit_en': get_ldap_attribute(entry, attribute='ou;lang-en'),
            'unit_fr': get_ldap_attribute(entry, attribute='ou', index=1),
            'unit_id': get_ldap_attribute(entry, attribute='ou'),
            'title_en': get_ldap_attribute(entry, attribute='title;lang-en'),
            'title_fr': get_ldap_attribute(entry, attribute='title'),
            'email': get_ldap_attribute(entry, attribute='mail'),
        }

        orgchart.append(person)

    # Close the LDAP connection
    ldap_connection.unbind_s()

    return orgchart


def epfl_orgchart():
    print('[ORGCHART]', "Fetching orgchart")

    # Initialise orgchart
    orgchart = []

    # Try to fetch fresh data from LDAP
    try:
        orgchart = fetch_from_ldap()
        fresh = True
        print('[ORGCHART]', "Fetched fresh orgchart from LDAP")
    except (ldap.SERVER_DOWN, ldap.TIMEOUT) as e:
        print('[ORGCHART]', f"Error fetching orgchart from LDAP: {e}")
        fresh = False

    # If no fetch fresh data from LDAP, fetch it from file
    if not fresh:
        filename = config.get('ldap', {}).get('orgchart_file')
        with open(filename, encoding='utf-8') as f:
            orgchart = json.load(f)

        print('[ORGCHART]', f"Fetched orgchart from local stored copy at {filename}")

    return orgchart


def get_orgchart_system_prompt():
    orgchart = epfl_orgchart()

    today = datetime.now().strftime("%Y-%m-%d")

    return f"""
For reference, below is the current organizational chart of EPFL as fetched today ({today}). This includes EPFL staff from certain upper-management units, but it is not an exhaustive list of EPFL members.
Note that this is more up-to-date than the output of `search_nodes`, so make sure to prioritise this organizational chart over that or your beliefs in case they disagree.
```
{orgchart}
```
    """


if __name__ == '__main__':
    print(get_orgchart_system_prompt())
