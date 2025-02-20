"""
This module contains the tool to retrieve the organizational chart from EPFL
"""

import ldap

from app.config import config


def get_ldap_attribute(entry, attribute, index=0):
    binary_str_list = entry.get(attribute, [b''])

    if index < len(binary_str_list):
        binary_str = binary_str_list[index]
    else:
        binary_str = b''

    return binary_str.decode('utf-8')


def epfl_orgchart():
    print("[ORGCHART]", "Fetching orgchart from LDAP")

    # Initialize LDAP connection
    host = config.get('ldap', {}).get('host')
    port = config.get('ldap', {}).get('port')
    ldap_connection = ldap.initialize(f'ldap://{host}:{port}')

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

    # Perform the search
    base_dn = 'o=epfl, c=ch'
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


def get_orgchart_system_prompt():
    orgchart = epfl_orgchart()

    return f"""
For reference, below is the organizational chart of EPFL. This includes EPFL staff from certain upper-management units, but it is not an exhaustive list of EPFL members.
```
{orgchart}
```
    """


if __name__ == '__main__':
    print(epfl_orgchart())
