import os
# Alles Installieren, was gebraucht wird
try:
    import OpenSSL
except ImportError:
    os.system('pip install pyOpenSSL')
try:
    import requests
except ImportError:
    os.system('pip install requests')
from OpenSSL.crypto import load_pkcs12, dump_privatekey, dump_certificate, FILETYPE_PEM


# Userabfrage
ovpnfilename = input("Name der .ovpn Datei (ohne Endung):")
name = input("Name der .p12 Datei (ohne Endung):")
passwd = input("Password:")

# Datei in binär einlesen
with open(os.path.dirname(os.path.abspath(__file__)) + '/' + name + '.p12', 'rb') as pkcs12_file:
    pkcs12_data = pkcs12_file.read()

# Passwort richtig codieren
pkcs12_password_bytes = passwd.encode('utf8')

# Datei entschlüsseln und einlesen
PyoP12 = load_pkcs12(pkcs12_data, pkcs12_password_bytes)
cert = dump_certificate(FILETYPE_PEM, PyoP12.get_certificate()).decode('ascii')
pk = dump_privatekey(FILETYPE_PEM, PyoP12.get_privatekey(), "aes256", pkcs12_password_bytes).decode('ascii')

# Finale Datei erstellen
ovpnfile = open(ovpnfilename + '.ovpn')
# Root Zertifikat einlesen
rootkey = open('root.key')
# Dateien zusammenfüren und in neue Datei Schreiben
txt = ovpnfile.read() + 'persist-key\npersist-tun\n<ca>\n' + rootkey.read() + '\n</ca>\n<cert>\n' + cert + '</cert>\n<key>\n' + pk + '</key>'
with open(name + '_neu.ovpn', 'w') as ovpn_file:
    ovpn_file.write(txt)
