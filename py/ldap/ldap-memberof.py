import sys
import os
import datetime
import ldap
import ldap.modlist

os.environ['LDAPNOINIT']='0'

# Set debugging level
#ldap.set_option(ldap.OPT_DEBUG_LEVEL,255)
ldapmodule_trace_level = 0
ldapmodule_trace_file = sys.stderr

ldap._trace_level = ldapmodule_trace_level
ldapserver = 'ldap://192.168.0.1:389'

def readuserinfo():
    l = ldap.initialize(ldapserver, trace_level=ldapmodule_trace_level, trace_file=ldapmodule_trace_file)
    l.protocol_version=ldap.VERSION3

     #Try an explicit anon bind to provoke failure
    l.simple_bind("cn=admin,dc=example,dc=cn", "123456")
    res = l.search_s("ou=dev,dc=example,dc=cn", ldap.SCOPE_SUBTREE, "objectclass=*", ["cn", "mail", "pwdChangedTime"])

    for k,v in res:
        if len(v) > 0:
            dn = k
            groupname = dn.split(',')[1].split('=')[1]

            print(dn, groupname)
            try:
                res = l.search_s("cn={},ou=groups,dc=example,dc=cn".format(groupname), ldap.SCOPE_SUBTREE, "objectclass=*")
                groupdn = 'cn={},ou=groups,dc=example,dc=cn'.format(groupname)
                mod_attrs = [(
                    ldap.MOD_ADD,
                    'uniqueMember',
                    dn.encode()
                    )]
                l.modify_s(groupdn, mod_attrs)
            except ldap.NO_SUCH_OBJECT:
                groupdn = 'cn={},ou=groups,dc=example,dc=cn'.format(groupname)
                attrs = {}
                attrs['objectclass'] = [
                    b'groupOfUniqueNames',
                    b'top'
                ]
                attrs['cn'] = groupname.encode()
                attrs['uniqueMember'] = dn.encode()
                ldif = ldap.modlist.addModlist(attrs)
                l.add_s(groupdn,ldif)
    l.unbind_s()

if __name__ == "__main__":
    readuserinfo()
